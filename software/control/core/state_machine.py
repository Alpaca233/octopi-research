"""Acquisition state machine for timepoint-level pause/resume/retake functionality.

This module provides a thread-safe state machine for controlling acquisition flow,
enabling users to pause mid-acquisition, review images, and retake specific FOVs.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Tuple, Optional, Callable
import threading


class TimepointState(Enum):
    """States for timepoint acquisition."""

    ACQUIRING = auto()  # Actively acquiring FOVs
    PAUSED = auto()  # Acquisition paused, waiting for user action
    RETAKING = auto()  # Re-acquiring specific FOVs
    CAPTURED = auto()  # All FOVs captured, waiting for next timepoint or review


@dataclass(frozen=True)
class FOVIdentifier:
    """Unique identifier for a field of view within an acquisition."""

    region_id: str
    fov_index: int


class TimepointStateMachine:
    """Thread-safe state machine for timepoint acquisition.

    This state machine manages the acquisition flow within a single timepoint,
    enabling pause/resume and retake functionality. It is designed to be used
    from both the UI thread (for control operations) and the worker thread
    (for state queries and transitions).

    State transitions:
        ACQUIRING -> PAUSED (via request_pause + complete_pause)
        ACQUIRING -> CAPTURED (via mark_all_captured)
        PAUSED -> ACQUIRING (via resume, if FOVs remaining)
        PAUSED -> CAPTURED (via resume, if no FOVs remaining)
        PAUSED -> RETAKING (via retake)
        RETAKING -> PAUSED (via complete_retakes or abort)
        CAPTURED -> PAUSED (via request_pause + complete_pause)
    """

    def __init__(self):
        self._state = TimepointState.ACQUIRING
        self._lock = threading.Lock()
        self._pause_requested = threading.Event()
        self._resume_event = threading.Event()
        self._retake_list: List[FOVIdentifier] = []
        self._fovs_remaining = 0

        # Callbacks (set by controller)
        self.on_state_changed: Optional[Callable[[TimepointState], None]] = None

    @property
    def state(self) -> TimepointState:
        """Get current state (thread-safe)."""
        with self._lock:
            return self._state

    def reset(self, total_fovs: int) -> None:
        """Reset state machine for a new timepoint.

        Args:
            total_fovs: Total number of FOVs to acquire in this timepoint.
        """
        with self._lock:
            self._state = TimepointState.ACQUIRING
            self._fovs_remaining = total_fovs
            self._retake_list.clear()
            self._pause_requested.clear()
            self._resume_event.clear()

    # --- Pause/Resume ---

    def request_pause(self) -> bool:
        """Request pause of acquisition (called from UI thread).

        The actual transition to PAUSED happens when the worker calls
        complete_pause() after finishing the current FOV.

        Returns:
            True if pause request was accepted, False if not in a pausable state.
        """
        with self._lock:
            if self._state in (TimepointState.ACQUIRING, TimepointState.CAPTURED):
                self._pause_requested.set()
                return True
            return False

    def is_pause_requested(self) -> bool:
        """Check if pause has been requested (called from worker thread)."""
        return self._pause_requested.is_set()

    def complete_pause(self) -> bool:
        """Complete transition to PAUSED state (called from worker thread).

        This should be called after ensuring all in-flight images are processed.

        Returns:
            True if successfully transitioned to PAUSED, False otherwise.
        """
        with self._lock:
            if self._pause_requested.is_set():
                self._pause_requested.clear()
                old_state = self._state
                self._state = TimepointState.PAUSED
                self._notify_state_changed(old_state)
                return True
            return False

    def resume(self) -> bool:
        """Resume acquisition from PAUSED state (called from UI thread).

        Transitions to ACQUIRING if FOVs remain, otherwise to CAPTURED.

        Returns:
            True if successfully initiated resume, False if not paused.
        """
        with self._lock:
            if self._state != TimepointState.PAUSED:
                return False

            old_state = self._state
            if self._fovs_remaining > 0:
                self._state = TimepointState.ACQUIRING
            else:
                self._state = TimepointState.CAPTURED

            self._notify_state_changed(old_state)
            self._resume_event.set()
            return True

    def wait_for_resume(self, timeout: Optional[float] = None) -> bool:
        """Block until resumed or timeout (called from worker thread).

        Args:
            timeout: Maximum seconds to wait, or None for indefinite wait.

        Returns:
            True if resumed, False if timed out.
        """
        result = self._resume_event.wait(timeout)
        self._resume_event.clear()
        return result

    # --- Retake ---

    def retake(self, fovs: List[FOVIdentifier]) -> bool:
        """Start retaking specified FOVs (called from UI thread).

        Can only be called from PAUSED state.

        Args:
            fovs: List of FOV identifiers to retake.

        Returns:
            True if retake started successfully, False otherwise.
        """
        with self._lock:
            if self._state != TimepointState.PAUSED:
                return False
            if not fovs:
                return False

            self._retake_list = list(fovs)
            old_state = self._state
            self._state = TimepointState.RETAKING
            self._notify_state_changed(old_state)
            self._resume_event.set()
            return True

    def get_retake_list(self) -> List[FOVIdentifier]:
        """Get list of FOVs to retake (called from worker thread).

        Returns:
            Copy of the retake list.
        """
        with self._lock:
            return list(self._retake_list)

    def complete_retakes(self) -> bool:
        """Finish retaking, return to PAUSED (called from worker thread).

        Returns:
            True if successfully transitioned back to PAUSED, False otherwise.
        """
        with self._lock:
            if self._state != TimepointState.RETAKING:
                return False

            self._retake_list.clear()
            old_state = self._state
            self._state = TimepointState.PAUSED
            self._notify_state_changed(old_state)
            return True

    # --- FOV Tracking ---

    def mark_fov_captured(self) -> None:
        """Mark one FOV as captured (called from worker thread)."""
        with self._lock:
            if self._fovs_remaining > 0:
                self._fovs_remaining -= 1

    def mark_all_captured(self) -> bool:
        """Transition to CAPTURED state after all FOVs done (called from worker thread).

        Returns:
            True if successfully transitioned to CAPTURED, False otherwise.
        """
        with self._lock:
            if self._state != TimepointState.ACQUIRING:
                return False

            old_state = self._state
            self._state = TimepointState.CAPTURED
            self._notify_state_changed(old_state)
            return True

    @property
    def fovs_remaining(self) -> int:
        """Get count of remaining FOVs to acquire (thread-safe)."""
        with self._lock:
            return self._fovs_remaining

    # --- Abort ---

    def abort(self) -> Tuple[bool, bool]:
        """Abort current operation (called from UI thread).

        When called during RETAKING, only aborts the retake operation and
        returns to PAUSED. In other states, signals to abort the entire
        acquisition.

        Returns:
            Tuple of (accepted, abort_entire_acquisition):
            - accepted: True if abort was handled
            - abort_entire_acquisition: True if full acquisition should abort,
              False if only retake was aborted
        """
        with self._lock:
            if self._state == TimepointState.RETAKING:
                # Abort retake only - return to PAUSED
                self._retake_list.clear()
                old_state = self._state
                self._state = TimepointState.PAUSED
                self._notify_state_changed(old_state)
                self._resume_event.set()  # Unblock worker
                return (True, False)
            else:
                # Abort entire acquisition
                return (True, True)

    def _notify_state_changed(self, old_state: TimepointState) -> None:
        """Call state change callback if state changed (must hold lock)."""
        if self.on_state_changed and old_state != self._state:
            new_state = self._state
            # Schedule callback outside lock to avoid deadlock
            # Using a daemon thread so it doesn't block shutdown
            threading.Thread(
                target=self.on_state_changed,
                args=(new_state,),
                daemon=True,
            ).start()
