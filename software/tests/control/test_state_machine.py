"""Unit tests for the acquisition state machine.

Tests cover:
- State transitions
- Invalid transitions
- Thread safety
- Abort behavior
"""

import threading
import time
import pytest

from control.core.state_machine import TimepointStateMachine, TimepointState, FOVIdentifier


class TestTimepointStateMachine:
    """Tests for TimepointStateMachine."""

    def test_initial_state(self):
        """State machine starts in ACQUIRING state."""
        sm = TimepointStateMachine()
        assert sm.state == TimepointState.ACQUIRING

    def test_reset(self):
        """Reset initializes state and FOV count."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=10)
        assert sm.state == TimepointState.ACQUIRING
        assert sm.fovs_remaining == 10

    # --- Pause/Resume Tests ---

    def test_request_pause_from_acquiring(self):
        """Pause can be requested from ACQUIRING state."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        assert sm.request_pause() is True
        assert sm.is_pause_requested() is True

    def test_complete_pause_transitions_to_paused(self):
        """complete_pause transitions to PAUSED state."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        assert sm.complete_pause() is True
        assert sm.state == TimepointState.PAUSED

    def test_resume_from_paused_with_fovs_remaining(self):
        """Resume from PAUSED returns to ACQUIRING if FOVs remain."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()

        assert sm.resume() is True
        assert sm.state == TimepointState.ACQUIRING

    def test_resume_from_paused_no_fovs_remaining(self):
        """Resume from PAUSED transitions to CAPTURED if no FOVs remain."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=2)
        sm.mark_fov_captured()
        sm.mark_fov_captured()
        sm.request_pause()
        sm.complete_pause()

        assert sm.fovs_remaining == 0
        assert sm.resume() is True
        assert sm.state == TimepointState.CAPTURED

    def test_resume_not_from_paused_fails(self):
        """Resume fails if not in PAUSED state."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        assert sm.resume() is False  # Still in ACQUIRING

    def test_wait_for_resume_unblocks_on_resume(self):
        """wait_for_resume unblocks when resume is called."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()

        # Start a thread that will wait for resume
        wait_result = [None]

        def wait_thread():
            wait_result[0] = sm.wait_for_resume(timeout=2.0)

        t = threading.Thread(target=wait_thread)
        t.start()

        # Give the thread time to start waiting
        time.sleep(0.1)

        # Resume should unblock the wait
        sm.resume()
        t.join(timeout=1.0)

        assert not t.is_alive()
        assert wait_result[0] is True

    def test_wait_for_resume_times_out(self):
        """wait_for_resume returns False on timeout."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()

        result = sm.wait_for_resume(timeout=0.1)
        assert result is False

    # --- Retake Tests ---

    def test_retake_from_paused(self):
        """Retake can be started from PAUSED state."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()

        fovs = [FOVIdentifier("A1", 0), FOVIdentifier("A1", 1)]
        assert sm.retake(fovs) is True
        assert sm.state == TimepointState.RETAKING

    def test_retake_not_from_paused_fails(self):
        """Retake fails if not in PAUSED state."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)

        fovs = [FOVIdentifier("A1", 0)]
        assert sm.retake(fovs) is False

    def test_retake_empty_list_fails(self):
        """Retake with empty list fails."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()

        assert sm.retake([]) is False

    def test_get_retake_list(self):
        """get_retake_list returns copy of retake list."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()

        fovs = [FOVIdentifier("A1", 0), FOVIdentifier("A1", 1)]
        sm.retake(fovs)

        retake_list = sm.get_retake_list()
        assert len(retake_list) == 2
        assert retake_list[0] == FOVIdentifier("A1", 0)
        assert retake_list[1] == FOVIdentifier("A1", 1)

    def test_complete_retakes_returns_to_paused(self):
        """complete_retakes transitions back to PAUSED."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()
        sm.retake([FOVIdentifier("A1", 0)])

        assert sm.complete_retakes() is True
        assert sm.state == TimepointState.PAUSED
        assert sm.get_retake_list() == []

    def test_complete_retakes_not_from_retaking_fails(self):
        """complete_retakes fails if not in RETAKING state."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()

        assert sm.complete_retakes() is False

    # --- FOV Tracking Tests ---

    def test_mark_fov_captured(self):
        """mark_fov_captured decrements remaining count."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)

        sm.mark_fov_captured()
        assert sm.fovs_remaining == 4

        sm.mark_fov_captured()
        assert sm.fovs_remaining == 3

    def test_mark_fov_captured_at_zero_stays_zero(self):
        """mark_fov_captured doesn't go negative."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=1)

        sm.mark_fov_captured()
        assert sm.fovs_remaining == 0

        sm.mark_fov_captured()  # Should not go negative
        assert sm.fovs_remaining == 0

    def test_mark_all_captured(self):
        """mark_all_captured transitions to CAPTURED."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)

        assert sm.mark_all_captured() is True
        assert sm.state == TimepointState.CAPTURED

    def test_mark_all_captured_not_from_acquiring_fails(self):
        """mark_all_captured fails if not in ACQUIRING state."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()

        assert sm.mark_all_captured() is False

    # --- Abort Tests ---

    def test_abort_from_retaking_returns_to_paused(self):
        """Abort from RETAKING returns to PAUSED."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()
        sm.retake([FOVIdentifier("A1", 0)])

        accepted, abort_all = sm.abort()
        assert accepted is True
        assert abort_all is False
        assert sm.state == TimepointState.PAUSED

    def test_abort_from_acquiring_aborts_all(self):
        """Abort from ACQUIRING signals full abort."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)

        accepted, abort_all = sm.abort()
        assert accepted is True
        assert abort_all is True

    def test_abort_from_paused_aborts_all(self):
        """Abort from PAUSED signals full abort."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)
        sm.request_pause()
        sm.complete_pause()

        accepted, abort_all = sm.abort()
        assert accepted is True
        assert abort_all is True

    # --- State Change Callback Tests ---

    def test_state_change_callback_called(self):
        """State change callback is called on state transitions."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=5)

        states_received = []

        def callback(state):
            states_received.append(state)

        sm.on_state_changed = callback

        sm.request_pause()
        sm.complete_pause()

        # Give callback thread time to run
        time.sleep(0.1)

        assert TimepointState.PAUSED in states_received

    # --- Thread Safety Tests ---

    def test_concurrent_pause_requests(self):
        """Multiple concurrent pause requests are handled safely."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=100)

        results = []

        def request_pause_thread():
            result = sm.request_pause()
            results.append(result)

        threads = [threading.Thread(target=request_pause_thread) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # At least one should succeed
        assert any(results)
        # All should get consistent result
        assert sm.is_pause_requested()

    def test_concurrent_fov_marking(self):
        """Multiple concurrent mark_fov_captured calls are thread-safe."""
        sm = TimepointStateMachine()
        sm.reset(total_fovs=100)

        def mark_fov_thread():
            for _ in range(10):
                sm.mark_fov_captured()

        threads = [threading.Thread(target=mark_fov_thread) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 100 FOVs should be marked
        assert sm.fovs_remaining == 0


class TestFOVIdentifier:
    """Tests for FOVIdentifier dataclass."""

    def test_fov_identifier_equality(self):
        """FOVIdentifier equality is based on region_id and fov_index."""
        fov1 = FOVIdentifier("A1", 0)
        fov2 = FOVIdentifier("A1", 0)
        fov3 = FOVIdentifier("A1", 1)
        fov4 = FOVIdentifier("A2", 0)

        assert fov1 == fov2
        assert fov1 != fov3
        assert fov1 != fov4

    def test_fov_identifier_hashable(self):
        """FOVIdentifier can be used in sets and as dict keys."""
        fov1 = FOVIdentifier("A1", 0)
        fov2 = FOVIdentifier("A1", 0)
        fov3 = FOVIdentifier("A1", 1)

        # Can use in set
        fov_set = {fov1, fov2, fov3}
        assert len(fov_set) == 2

        # Can use as dict key
        fov_dict = {fov1: "first", fov3: "second"}
        assert fov_dict[fov2] == "first"

    def test_fov_identifier_immutable(self):
        """FOVIdentifier is frozen (immutable)."""
        fov = FOVIdentifier("A1", 0)
        with pytest.raises(AttributeError):
            fov.region_id = "A2"
