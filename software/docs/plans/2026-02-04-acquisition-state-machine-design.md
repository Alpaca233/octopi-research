# Acquisition State Machine Design

## Overview

This document describes a state machine design for the Squid microscope acquisition system that enables:

1. **Pause/Resume**: Gracefully pause acquisition mid-timepoint or after completion
2. **Selective Retake**: Review recent FOVs and retake specific ones
3. **QC Integration**: Hook points for quality control checks that can trigger pauses or suggest retakes

## Design Goals

- Minimal changes to existing `MultiPointWorker` acquisition loop
- Clear separation between state management and acquisition logic
- Support manual pause/retake as primary use case
- Extensible for future automated QC workflows
- Per-timepoint scope (previous timepoints are immutable)

## Architecture

### Acquisition Level (No State Machine)

Simple tracking variables - no formal state machine needed:

```python
@dataclass
class AcquisitionContext:
    current_timepoint: int = 0
    total_timepoints: int = 1
    aborted: bool = False
    proceed_policy: ProceedPolicy = ProceedPolicy.AUTO

class ProceedPolicy(Enum):
    AUTO = auto()       # Proceed immediately when CAPTURED
    MANUAL = auto()     # Wait for explicit proceed()
    QC_GATED = auto()   # Wait for QC approval (future)
```

**Logic:**
- Acquisition is "running" while `current_timepoint < total_timepoints` and not `aborted`
- Proceed to next timepoint when current timepoint reaches `CAPTURED` state
- Proceed behavior controlled by `proceed_policy`

### Timepoint Level (State Machine)

Manages pause/resume/retake within a single timepoint.

```
              ┌───────────┐   pause()    ┌────────┐
              │ ACQUIRING │─────────────▶│ PAUSED │
              └─────┬─────┘              └───┬────┘
                │   │                        │
                │   │                        ├─── resume() ──▶ ACQUIRING
        abort() │   │                        │   (FOVs remaining)
                │   │                        │
                │   │ all FOVs done          ├─── resume() ──▶ CAPTURED
                │   │                        │   (no FOVs remaining)
                │   ▼                        │
                │ ┌──────────┐   pause()     │ retake([fovs])
                │ │ CAPTURED │──────────────▶│
                │ └────┬─────┘               ▼
                │      │               ┌──────────┐
                │      │ abort()       │ RETAKING │
                │      │               └────┬─────┘
                │      │                    │   │
                │      │        ┌───────────┘   │ abort()
                │      │        │ done          │ (retaking only)
                │      │        ▼               ▼
                │      │   ┌────────┐      ┌────────┐
                ▼      ▼   │ PAUSED │      │ PAUSED │
           Abort entire    └────────┘      └────────┘
           acquisition
```

## States

| State | Description |
|-------|-------------|
| `ACQUIRING` | Initial capture of FOVs in sequence |
| `PAUSED` | Decision point - operator reviews, selects retakes, or proceeds |
| `RETAKING` | Re-capturing specific FOVs from the retake list |
| `CAPTURED` | All FOVs captured, ready for next timepoint |

## Transitions

| From | To | Trigger | Notes |
|------|----|---------|-------|
| `ACQUIRING` | `PAUSED` | `pause()` | Graceful - completes current FOV first |
| `ACQUIRING` | `CAPTURED` | All FOVs done | Automatic transition |
| `CAPTURED` | `PAUSED` | `pause()` | For review before next timepoint |
| `PAUSED` | `ACQUIRING` | `resume()` | Only if FOVs remaining |
| `PAUSED` | `CAPTURED` | `resume()` | Only if no FOVs remaining |
| `PAUSED` | `RETAKING` | `retake(fov_list)` | Receives list of (region_id, fov_index) |
| `RETAKING` | `PAUSED` | Retake list complete | Returns to PAUSED for review |

## Abort Behavior

| Abort From | Effect |
|------------|--------|
| `ACQUIRING` | Abort entire acquisition |
| `PAUSED` | Abort entire acquisition |
| `CAPTURED` | Abort entire acquisition |
| `RETAKING` | Abort retaking only, return to `PAUSED` |

## Pause Behavior

Pause is **graceful**:
1. Current FOV capture completes
2. All jobs for current FOV are dispatched (save, QC, etc.)
3. Then state transitions to `PAUSED`

No half-captured images or orphaned jobs.

## Retake Mechanism

**Input:**
- `retake(fov_list)` receives a list of `(region_id, fov_index)` tuples
- List provided by user (manual selection) or QC system (automated)
- State machine does not track per-FOV status internally

**Behavior:**
- Retaking overwrites original files (no versioning)
- After retakes complete, returns to `PAUSED` for review
- Operator can trigger additional retakes or resume

**Identification:**
- FOVs identified by index pair: `(region_id, fov_index)`
- Matches existing loop structure in `MultiPointWorker`

## Interface

```python
from enum import Enum, auto
from typing import List, Tuple, Callable, Optional
from dataclasses import dataclass
import threading

class TimepointState(Enum):
    ACQUIRING = auto()
    PAUSED = auto()
    RETAKING = auto()
    CAPTURED = auto()

@dataclass(frozen=True)
class FOVIdentifier:
    region_id: str
    fov_index: int

class TimepointStateMachine:
    """Manages state for a single timepoint."""

    def __init__(self, total_fovs: int):
        self._state = TimepointState.ACQUIRING
        self._lock = threading.Lock()
        self._pause_requested = threading.Event()
        self._resume_event = threading.Event()
        self._retake_list: List[FOVIdentifier] = []
        self._fovs_remaining = total_fovs
        self._total_fovs = total_fovs

    @property
    def state(self) -> TimepointState:
        """Current state."""
        with self._lock:
            return self._state

    @property
    def fovs_remaining(self) -> int:
        """Number of FOVs not yet captured."""
        with self._lock:
            return self._fovs_remaining

    def request_pause(self) -> bool:
        """
        Request pause. Returns True if request accepted.
        Pause is graceful - completes current FOV first.
        Valid from: ACQUIRING, CAPTURED
        """
        with self._lock:
            if self._state in (TimepointState.ACQUIRING, TimepointState.CAPTURED):
                self._pause_requested.set()
                return True
            return False

    def wait_for_pause(self, timeout: Optional[float] = None) -> bool:
        """Block until pause is requested. Used by worker thread."""
        return self._pause_requested.wait(timeout)

    def complete_pause(self) -> bool:
        """
        Called by worker after completing current FOV.
        Actually transitions to PAUSED state.
        """
        with self._lock:
            if self._pause_requested.is_set():
                self._pause_requested.clear()
                self._state = TimepointState.PAUSED
                return True
            return False

    def resume(self) -> bool:
        """
        Resume acquisition.
        Valid from: PAUSED
        Transitions to: ACQUIRING (if FOVs remaining) or CAPTURED (if done)
        """
        with self._lock:
            if self._state != TimepointState.PAUSED:
                return False

            if self._fovs_remaining > 0:
                self._state = TimepointState.ACQUIRING
            else:
                self._state = TimepointState.CAPTURED

            self._resume_event.set()
            return True

    def wait_for_resume(self, timeout: Optional[float] = None) -> bool:
        """Block until resumed. Used by worker thread."""
        result = self._resume_event.wait(timeout)
        self._resume_event.clear()
        return result

    def retake(self, fovs: List[FOVIdentifier]) -> bool:
        """
        Start retaking specified FOVs.
        Valid from: PAUSED
        Transitions to: RETAKING
        """
        with self._lock:
            if self._state != TimepointState.PAUSED:
                return False
            if not fovs:
                return False

            self._retake_list = list(fovs)
            self._state = TimepointState.RETAKING
            self._resume_event.set()
            return True

    def get_retake_list(self) -> List[FOVIdentifier]:
        """Get current retake list."""
        with self._lock:
            return list(self._retake_list)

    def complete_retakes(self) -> bool:
        """
        Called by worker when retake list is complete.
        Transitions to: PAUSED
        """
        with self._lock:
            if self._state != TimepointState.RETAKING:
                return False

            self._retake_list.clear()
            self._state = TimepointState.PAUSED
            return True

    def mark_fov_captured(self) -> None:
        """Called by worker when an FOV is captured."""
        with self._lock:
            if self._fovs_remaining > 0:
                self._fovs_remaining -= 1

    def mark_all_captured(self) -> bool:
        """
        Called by worker when all FOVs are done.
        Transitions to: CAPTURED
        """
        with self._lock:
            if self._state != TimepointState.ACQUIRING:
                return False

            self._state = TimepointState.CAPTURED
            return True

    def abort(self) -> Tuple[bool, bool]:
        """
        Abort current operation.
        Returns: (abort_accepted, abort_entire_acquisition)

        From RETAKING: aborts retake only, returns to PAUSED
        From other states: aborts entire acquisition
        """
        with self._lock:
            if self._state == TimepointState.RETAKING:
                self._retake_list.clear()
                self._state = TimepointState.PAUSED
                return (True, False)  # Abort retake only
            else:
                return (True, True)   # Abort entire acquisition
```

## Integration with MultiPointWorker

```python
# Pseudocode for modified acquisition loop

class MultiPointWorker:
    def __init__(self, ..., state_machine: TimepointStateMachine):
        self._state_machine = state_machine
        ...

    def run_coordinate_acquisition(self):
        for region_id, coords in self.regions:
            for fov_index, coord in enumerate(coords):

                # Check for pause request before each FOV
                if self._state_machine._pause_requested.is_set():
                    self._finish_current_jobs()
                    self._state_machine.complete_pause()

                    # Wait for resume or retake
                    self._state_machine.wait_for_resume()

                    # Check what state we're in after resume
                    state = self._state_machine.state
                    if state == TimepointState.CAPTURED:
                        return  # Done with this timepoint
                    elif state == TimepointState.RETAKING:
                        self._run_retakes()
                        continue  # Check state again

                # Check for abort
                if self._abort_requested():
                    return

                # Acquire FOV
                self.acquire_at_position(region_id, fov_index, coord)
                self._state_machine.mark_fov_captured()

        # All FOVs done
        self._state_machine.mark_all_captured()

    def _run_retakes(self):
        """Execute retakes for FOVs in retake list."""
        retake_list = self._state_machine.get_retake_list()

        for fov_id in retake_list:
            # Check for retake abort
            if self._retake_abort_requested():
                break

            coord = self._get_fov_coordinates(fov_id)
            self.acquire_at_position(fov_id.region_id, fov_id.fov_index, coord)

        self._state_machine.complete_retakes()
```

## Signals (PyQt Integration)

```python
@dataclass
class StateMachineSignals:
    # State changes
    signal_state_changed: Callable[[TimepointState], None]

    # Pause/resume
    signal_pause_requested: Callable[[], None]
    signal_paused: Callable[[], None]
    signal_resumed: Callable[[], None]

    # Retake
    signal_retake_started: Callable[[List[FOVIdentifier]], None]
    signal_retake_fov_complete: Callable[[FOVIdentifier], None]
    signal_retakes_complete: Callable[[], None]

    # Progress
    signal_fov_captured: Callable[[FOVIdentifier], None]
    signal_timepoint_captured: Callable[[], None]
```

## Thread Safety

State transitions are thread-safe:
- `threading.Lock` protects all state mutations
- `threading.Event` for pause/resume signaling
- Worker thread waits on events; UI thread signals them

## QC Integration Points

The state machine provides hooks for QC system (detailed in separate document):

1. **After FOV captured**: QC job dispatched, result can call `request_pause()`
2. **In PAUSED state**: QC can provide suggested retake list via UI
3. **Before proceed**: QC gate can block advancement to next timepoint

## Summary

| Component | Responsibility |
|-----------|----------------|
| `AcquisitionContext` | Tracks timepoint index, abort flag, proceed policy |
| `TimepointStateMachine` | Pause/resume/retake within a timepoint |
| `MultiPointWorker` | Actual image acquisition, responds to state machine |
| `ProceedPolicy` | Configures auto vs manual timepoint progression |
