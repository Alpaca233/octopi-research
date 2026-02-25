# Nikon Ti2 Extended Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Nikon Ti2 filter wheel and DIA control with unified `[Nikon]` configuration section.

**Architecture:** Extend existing `NikonTi2Adapter` to conditionally initialize filter wheel and DIA components based on config flags. Return all components via `NikonTi2Components` dataclass. Integrate via `MicroscopeAddons`.

**Tech Stack:** Python 3, pymmcore-plus, Pydantic dataclasses, pytest

---

### Task 1: Add Nikon Configuration Variables to `_def.py`

**Files:**
- Modify: `control/_def.py:754` (replace standalone USE_NIKON_PFS)

**Step 1: Add Nikon config section defaults**

Add after line 752 (after `PRIOR_STAGE_SN = ""`), replacing the existing `USE_NIKON_PFS = False`:

```python
# Nikon Ti2 Integration
NIKON_BODY = None  # "Ti2" or None - enables Nikon integration when set
USE_NIKON_PFS = False
USE_NIKON_STAGE = False
USE_NIKON_FILTER_WHEEL = False
USE_NIKON_TRANSILLUMINATION = False
```

**Step 2: Verify syntax**

Run: `python3 -c "import control._def; print(control._def.NIKON_BODY)"`
Expected: `None`

**Step 3: Commit**

```bash
git add control/_def.py
git commit -m "feat(nikon): add Nikon configuration variables to _def.py"
```

---

### Task 2: Add `[Nikon]` Section to Example INI File

**Files:**
- Modify: `configurations/configuration_Squid+.ini`

**Step 1: Add Nikon section at end of file**

Append to `configurations/configuration_Squid+.ini`:

```ini

[Nikon]
nikon_body = None
_nikon_body_options = [Ti2, None]

use_nikon_pfs = False
_use_nikon_pfs_options = [True, False]

use_nikon_stage = False
_use_nikon_stage_options = [True, False]

use_nikon_filter_wheel = False
_use_nikon_filter_wheel_options = [True, False]

use_nikon_transillumination = False
_use_nikon_transillumination_options = [True, False]
```

**Step 2: Verify INI parses correctly**

Run: `python3 -c "from configparser import ConfigParser; c = ConfigParser(); c.read('configurations/configuration_Squid+.ini'); print(c.get('Nikon', 'nikon_body'))"`
Expected: `None`

**Step 3: Commit**

```bash
git add configurations/configuration_Squid+.ini
git commit -m "feat(nikon): add [Nikon] section to example INI config"
```

---

### Task 3: Add Exception Classes to `nikon_ti2.py`

**Files:**
- Modify: `control/nikon_ti2.py:45-50`

**Step 1: Add new exception classes after existing exceptions**

Add after `class StageException(NikonTi2Exception):` (around line 50):

```python
class NikonFilterWheelException(NikonTi2Exception):
    pass


class NikonDIAException(NikonTi2Exception):
    pass
```

**Step 2: Verify import works**

Run: `python3 -c "from control.nikon_ti2 import NikonFilterWheelException, NikonDIAException; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add control/nikon_ti2.py
git commit -m "feat(nikon): add FilterWheel and DIA exception classes"
```

---

### Task 4: Add NikonTi2Components Dataclass

**Files:**
- Modify: `control/nikon_ti2.py` (add after imports, before NikonTi2PFS class)

**Step 1: Add dataclass import and NikonTi2Components**

Add near top of file with other imports (after `from dataclasses import dataclass`):

```python
from typing import Optional, Tuple, Sequence, Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from squid.abc import AbstractFilterWheelController
```

Add after the exception classes, before `class NikonTi2PFS:`:

```python
@dataclass
class NikonTi2Components:
    """Container for all Nikon Ti2 components returned by adapter initialization."""
    stage: Optional["NikonTi2Stage"] = None
    pfs: Optional["NikonTi2PFS"] = None
    filter_wheel: Optional["NikonTi2FilterWheel"] = None
    dia: Optional["NikonTi2DIA"] = None
```

**Step 2: Verify import works**

Run: `python3 -c "from control.nikon_ti2 import NikonTi2Components; print(NikonTi2Components())"`
Expected: `NikonTi2Components(stage=None, pfs=None, filter_wheel=None, dia=None)`

**Step 3: Commit**

```bash
git add control/nikon_ti2.py
git commit -m "feat(nikon): add NikonTi2Components dataclass"
```

---

### Task 5: Write Failing Test for NikonTi2FilterWheel_Simulation

**Files:**
- Create: `tests/control/test_nikon_ti2.py`

**Step 1: Create test file with filter wheel simulation tests**

```python
"""Tests for Nikon Ti2 integration components."""

import pytest
from control.nikon_ti2 import (
    NikonTi2FilterWheel_Simulation,
    NikonFilterWheelException,
)


class TestNikonTi2FilterWheelSimulation:
    """Tests for NikonTi2FilterWheel_Simulation."""

    def test_initialize(self):
        """Test filter wheel initialization."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        assert fw.is_initialized

    def test_available_filter_wheels(self):
        """Test available filter wheels returns single wheel."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        assert fw.available_filter_wheels == [1]

    def test_set_and_get_position(self):
        """Test setting and getting filter wheel position."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        fw.set_filter_wheel_position({1: 3})
        assert fw.get_filter_wheel_position() == {1: 3}

    def test_position_range(self):
        """Test filter wheel positions 1-6."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        for pos in range(1, 7):
            fw.set_filter_wheel_position({1: pos})
            assert fw.get_filter_wheel_position() == {1: pos}

    def test_get_filter_wheel_info(self):
        """Test getting filter wheel info."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        info = fw.get_filter_wheel_info(1)
        assert info.index == 1
        assert info.number_of_slots == 6

    def test_home(self):
        """Test homing resets position to 1."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        fw.set_filter_wheel_position({1: 5})
        fw.home(1)
        assert fw.get_filter_wheel_position() == {1: 1}

    def test_delay_methods_return_none(self):
        """Test delay methods return None (hardware-controlled)."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        assert fw.get_delay_ms() is None
        assert fw.get_delay_offset_ms() is None
        fw.set_delay_ms(100)  # Should not raise
        fw.set_delay_offset_ms(50)  # Should not raise

    def test_close(self):
        """Test close method."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        fw.close()
        assert not fw.is_initialized
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/control/test_nikon_ti2.py -v`
Expected: FAIL with `ImportError: cannot import name 'NikonTi2FilterWheel_Simulation'`

**Step 3: Commit failing test**

```bash
git add tests/control/test_nikon_ti2.py
git commit -m "test(nikon): add failing tests for NikonTi2FilterWheel_Simulation"
```

---

### Task 6: Implement NikonTi2FilterWheel_Simulation

**Files:**
- Modify: `control/nikon_ti2.py` (add after NikonTi2Stage_Simulation class)

**Step 1: Add simulation class**

Add after `class NikonTi2Stage_Simulation(AbstractStage):` (around line 970):

```python
# -----------------------------------------------------------------------------
# Simulated Ti2 Filter Wheel
# -----------------------------------------------------------------------------
class NikonTi2FilterWheel_Simulation:
    """
    Simulated Nikon Ti2 filter wheel for testing without hardware.

    Implements AbstractFilterWheelController interface.
    Ti2 typically has a single 6-position emission filter wheel.
    """

    def __init__(self, *, filter_wheel_label: str = "FilterWheel", num_positions: int = 6):
        self.filter_wheel_label = filter_wheel_label
        self._num_positions = num_positions
        self._initialized = False
        self._position = 1  # 1-indexed positions

    def initialize(self, filter_wheel_indices: List[int]):
        """Initialize the filter wheel."""
        self._initialized = True
        self._position = 1

    @property
    def available_filter_wheels(self) -> List[int]:
        """Single filter wheel at index 1."""
        return [1]

    def get_filter_wheel_info(self, index: int):
        """Get information about the filter wheel."""
        from squid.abc import FilterWheelInfo
        return FilterWheelInfo(
            index=index,
            number_of_slots=self._num_positions,
            slot_names=[f"Position {i}" for i in range(1, self._num_positions + 1)],
        )

    def home(self, index: int = None):
        """Home the filter wheel (moves to position 1)."""
        self._position = 1

    def set_filter_wheel_position(self, positions: Dict[int, int]):
        """Set filter wheel position."""
        if 1 in positions:
            pos = positions[1]
            if not (1 <= pos <= self._num_positions):
                raise NikonFilterWheelException(
                    f"Position {pos} out of range [1, {self._num_positions}]"
                )
            self._position = pos

    def get_filter_wheel_position(self) -> Dict[int, int]:
        """Get current filter wheel position."""
        return {1: self._position}

    def set_delay_offset_ms(self, delay_offset_ms: float):
        """No-op: Ti2 filter wheel timing is hardware-controlled."""
        pass

    def get_delay_offset_ms(self) -> Optional[float]:
        """Returns None: Ti2 filter wheel timing is hardware-controlled."""
        return None

    def set_delay_ms(self, delay_ms: float):
        """No-op: Ti2 filter wheel timing is hardware-controlled."""
        pass

    def get_delay_ms(self) -> Optional[float]:
        """Returns None: Ti2 filter wheel timing is hardware-controlled."""
        return None

    def close(self):
        """Close the filter wheel connection."""
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/control/test_nikon_ti2.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add control/nikon_ti2.py
git commit -m "feat(nikon): implement NikonTi2FilterWheel_Simulation"
```

---

### Task 7: Write Failing Test for NikonTi2DIA_Simulation

**Files:**
- Modify: `tests/control/test_nikon_ti2.py`

**Step 1: Add DIA simulation tests**

Append to test file:

```python
from control.nikon_ti2 import (
    NikonTi2DIA_Simulation,
    NikonDIAException,
)


class TestNikonTi2DIASimulation:
    """Tests for NikonTi2DIA_Simulation."""

    def test_initialize(self):
        """Test DIA initialization."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()
        assert dia.is_initialized

    def test_initial_state_is_off(self):
        """Test DIA starts in off state."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()
        assert dia.get_state() is False

    def test_set_and_get_state(self):
        """Test turning DIA on and off."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()

        dia.set_state(True)
        assert dia.get_state() is True

        dia.set_state(False)
        assert dia.get_state() is False

    def test_initial_intensity(self):
        """Test DIA starts at 0% intensity."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()
        assert dia.get_intensity() == 0.0

    def test_set_and_get_intensity(self):
        """Test setting intensity."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()

        dia.set_intensity(50.0)
        assert dia.get_intensity() == 50.0

        dia.set_intensity(100.0)
        assert dia.get_intensity() == 100.0

    def test_intensity_clamped_to_range(self):
        """Test intensity is clamped to 0-100%."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()

        dia.set_intensity(-10.0)
        assert dia.get_intensity() == 0.0

        dia.set_intensity(150.0)
        assert dia.get_intensity() == 100.0

    def test_requires_initialization(self):
        """Test methods require initialization."""
        dia = NikonTi2DIA_Simulation()
        with pytest.raises(NikonDIAException):
            dia.get_state()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/control/test_nikon_ti2.py::TestNikonTi2DIASimulation -v`
Expected: FAIL with `ImportError: cannot import name 'NikonTi2DIA_Simulation'`

**Step 3: Commit failing test**

```bash
git add tests/control/test_nikon_ti2.py
git commit -m "test(nikon): add failing tests for NikonTi2DIA_Simulation"
```

---

### Task 8: Implement NikonTi2DIA_Simulation

**Files:**
- Modify: `control/nikon_ti2.py` (add after NikonTi2FilterWheel_Simulation)

**Step 1: Add DIA simulation class**

```python
# -----------------------------------------------------------------------------
# Simulated Ti2 DIA (Transmitted Light)
# -----------------------------------------------------------------------------
class NikonTi2DIA_Simulation:
    """
    Simulated Nikon Ti2 DIA (transmitted light) controller for testing.

    Provides on/off control and intensity adjustment (0-100%).
    """

    def __init__(self, *, dia_label: str = "DIA", simulate_delays: bool = False):
        self.dia_label = dia_label
        self.simulate_delays = simulate_delays
        self._initialized = False
        self._state = False
        self._intensity = 0.0

    def initialize_device(self) -> None:
        """Initialize the DIA device."""
        self._initialized = True
        self._state = False
        self._intensity = 0.0

    def set_state(self, on: bool) -> None:
        """Turn DIA on or off."""
        self._require_initialized()
        self._state = bool(on)

    def get_state(self) -> bool:
        """Get current DIA state."""
        self._require_initialized()
        return self._state

    def set_intensity(self, intensity_percent: float) -> None:
        """Set DIA intensity (0-100%)."""
        self._require_initialized()
        self._intensity = max(0.0, min(100.0, float(intensity_percent)))

    def get_intensity(self) -> float:
        """Get current DIA intensity (0-100%)."""
        self._require_initialized()
        return self._intensity

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise NikonDIAException("Call initialize_device() first.")

    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/control/test_nikon_ti2.py::TestNikonTi2DIASimulation -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add control/nikon_ti2.py
git commit -m "feat(nikon): implement NikonTi2DIA_Simulation"
```

---

### Task 9: Implement NikonTi2FilterWheel (Real Hardware)

**Files:**
- Modify: `control/nikon_ti2.py` (add after NikonTi2Stage class, before simulations)

**Step 1: Add real hardware filter wheel class**

Add after `class NikonTi2Stage(AbstractStage):` (around line 545):

```python
# -----------------------------------------------------------------------------
# Ti2 Filter Wheel
# -----------------------------------------------------------------------------
class NikonTi2FilterWheel:
    """
    Nikon Ti2 emission filter wheel via Micro-Manager NikonTi2 adapter.

    Implements AbstractFilterWheelController interface for single emission wheel.
    Ti2 typically has 6 positions (1-6).
    """

    _POSITION_PROP_CANDIDATES = ("Position", "State", "Label")

    def __init__(
        self,
        core: Optional[CMMCorePlus] = None,
        *,
        filter_wheel_label: str = "FilterWheel",
        num_positions: int = 6,
    ):
        self.core = core or CMMCorePlus.instance()
        self.filter_wheel_label = filter_wheel_label
        self._num_positions = num_positions
        self._initialized = False
        self._prop_position: Optional[str] = None

    def initialize(self, filter_wheel_indices: List[int]):
        """Initialize the filter wheel and resolve properties."""
        # Resolve position property
        self._prop_position = self._pick_property(
            self.filter_wheel_label, self._POSITION_PROP_CANDIDATES, must=False
        )
        self._initialized = True

    @property
    def available_filter_wheels(self) -> List[int]:
        """Single filter wheel at index 1."""
        return [1]

    def get_filter_wheel_info(self, index: int):
        """Get information about the filter wheel."""
        from squid.abc import FilterWheelInfo
        return FilterWheelInfo(
            index=index,
            number_of_slots=self._num_positions,
            slot_names=[f"Position {i}" for i in range(1, self._num_positions + 1)],
        )

    def home(self, index: int = None):
        """Home the filter wheel (move to position 1)."""
        self._require_initialized()
        self.set_filter_wheel_position({1: 1})

    def set_filter_wheel_position(self, positions: Dict[int, int]):
        """Set filter wheel position."""
        self._require_initialized()
        if 1 not in positions:
            return

        pos = positions[1]
        if not (1 <= pos <= self._num_positions):
            raise NikonFilterWheelException(
                f"Position {pos} out of range [1, {self._num_positions}]"
            )

        try:
            # Try setPosition first (common for state devices)
            self.core.setPosition(self.filter_wheel_label, float(pos - 1))  # 0-indexed in MM
        except Exception:
            # Fall back to property-based control
            if self._prop_position:
                self.core.setProperty(self.filter_wheel_label, self._prop_position, str(pos))
            else:
                raise NikonFilterWheelException(
                    f"Cannot set filter wheel position: no position property found"
                )

        # Wait for movement to complete
        try:
            self.core.waitForDevice(self.filter_wheel_label)
        except Exception:
            pass

    def get_filter_wheel_position(self) -> Dict[int, int]:
        """Get current filter wheel position."""
        self._require_initialized()
        try:
            pos = int(self.core.getPosition(self.filter_wheel_label)) + 1  # Convert to 1-indexed
            return {1: pos}
        except Exception:
            if self._prop_position:
                val = self.core.getProperty(self.filter_wheel_label, self._prop_position)
                return {1: int(val)}
            raise NikonFilterWheelException("Cannot read filter wheel position")

    def set_delay_offset_ms(self, delay_offset_ms: float):
        """No-op: Ti2 filter wheel timing is hardware-controlled."""
        pass

    def get_delay_offset_ms(self) -> Optional[float]:
        """Returns None: Ti2 filter wheel timing is hardware-controlled."""
        return None

    def set_delay_ms(self, delay_ms: float):
        """No-op: Ti2 filter wheel timing is hardware-controlled."""
        pass

    def get_delay_ms(self) -> Optional[float]:
        """Returns None: Ti2 filter wheel timing is hardware-controlled."""
        return None

    def close(self):
        """Close the filter wheel connection."""
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise NikonFilterWheelException("Call initialize() first.")

    def _pick_property(self, dev: str, candidates: Sequence[str], *, must: bool) -> Optional[str]:
        """Find a property from candidates list."""
        try:
            props = set(self.core.getDevicePropertyNames(dev))
        except Exception:
            if must:
                raise NikonFilterWheelException(f"Cannot read properties for device '{dev}'")
            return None

        for p in candidates:
            if p in props:
                return p

        if must:
            raise NikonFilterWheelException(
                f"Could not find required property on '{dev}'. Tried: {list(candidates)}"
            )
        return None
```

**Step 2: Verify import works**

Run: `python3 -c "from control.nikon_ti2 import NikonTi2FilterWheel; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add control/nikon_ti2.py
git commit -m "feat(nikon): implement NikonTi2FilterWheel for real hardware"
```

---

### Task 10: Implement NikonTi2DIA (Real Hardware)

**Files:**
- Modify: `control/nikon_ti2.py` (add after NikonTi2FilterWheel)

**Step 1: Add real hardware DIA class**

```python
# -----------------------------------------------------------------------------
# Ti2 DIA (Transmitted Light)
# -----------------------------------------------------------------------------
class NikonTi2DIA:
    """
    Nikon Ti2 DIA (transmitted light) controller via Micro-Manager.

    Provides on/off control and intensity adjustment (0-100%).
    """

    _STATE_PROP_CANDIDATES = ("State", "OnOff", "Shutter")
    _INTENSITY_PROP_CANDIDATES = ("Intensity", "Voltage", "Level", "Power")

    def __init__(
        self,
        core: Optional[CMMCorePlus] = None,
        *,
        dia_label: str = "DIA",
    ):
        self.core = core or CMMCorePlus.instance()
        self.dia_label = dia_label
        self._initialized = False
        self._prop_state: Optional[str] = None
        self._prop_intensity: Optional[str] = None

    def initialize_device(self) -> None:
        """Initialize the DIA device and resolve properties."""
        self._prop_state = self._pick_property(
            self.dia_label, self._STATE_PROP_CANDIDATES, must=False
        )
        self._prop_intensity = self._pick_property(
            self.dia_label, self._INTENSITY_PROP_CANDIDATES, must=False
        )
        self._initialized = True

    def set_state(self, on: bool) -> None:
        """Turn DIA on or off."""
        self._require_initialized()

        if self._prop_state:
            val = "1" if on else "0"
            try:
                allowed = list(self.core.getAllowedPropertyValues(self.dia_label, self._prop_state))
                if allowed:
                    # Find appropriate on/off value
                    allowed_lower = [a.lower() for a in allowed]
                    if on:
                        for candidate in ["on", "1", "true", "open"]:
                            if candidate in allowed_lower:
                                val = allowed[allowed_lower.index(candidate)]
                                break
                    else:
                        for candidate in ["off", "0", "false", "closed"]:
                            if candidate in allowed_lower:
                                val = allowed[allowed_lower.index(candidate)]
                                break
            except Exception:
                pass

            try:
                self.core.setProperty(self.dia_label, self._prop_state, val)
            except Exception as e:
                raise NikonDIAException(f"Failed to set DIA state: {e}") from e
        else:
            # Try using shutter control
            try:
                if on:
                    self.core.setShutterOpen(True)
                else:
                    self.core.setShutterOpen(False)
            except Exception as e:
                raise NikonDIAException(f"Failed to set DIA state (no state property): {e}") from e

    def get_state(self) -> bool:
        """Get current DIA state."""
        self._require_initialized()

        if self._prop_state:
            try:
                val = self.core.getProperty(self.dia_label, self._prop_state)
                return val.lower() in ("on", "1", "true", "open")
            except Exception as e:
                raise NikonDIAException(f"Failed to get DIA state: {e}") from e

        raise NikonDIAException("Cannot read DIA state: no state property found")

    def set_intensity(self, intensity_percent: float) -> None:
        """Set DIA intensity (0-100%)."""
        self._require_initialized()
        intensity_percent = max(0.0, min(100.0, float(intensity_percent)))

        if self._prop_intensity:
            try:
                self.core.setProperty(self.dia_label, self._prop_intensity, str(intensity_percent))
            except Exception as e:
                raise NikonDIAException(f"Failed to set DIA intensity: {e}") from e
        else:
            raise NikonDIAException("Cannot set DIA intensity: no intensity property found")

    def get_intensity(self) -> float:
        """Get current DIA intensity (0-100%)."""
        self._require_initialized()

        if self._prop_intensity:
            try:
                val = self.core.getProperty(self.dia_label, self._prop_intensity)
                return float(val)
            except Exception as e:
                raise NikonDIAException(f"Failed to get DIA intensity: {e}") from e

        raise NikonDIAException("Cannot read DIA intensity: no intensity property found")

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise NikonDIAException("Call initialize_device() first.")

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _pick_property(self, dev: str, candidates: Sequence[str], *, must: bool) -> Optional[str]:
        """Find a property from candidates list."""
        try:
            props = set(self.core.getDevicePropertyNames(dev))
        except Exception:
            if must:
                raise NikonDIAException(f"Cannot read properties for device '{dev}'")
            return None

        for p in candidates:
            if p in props:
                return p

        if must:
            raise NikonDIAException(
                f"Could not find required property on '{dev}'. Tried: {list(candidates)}"
            )
        return None
```

**Step 2: Verify import works**

Run: `python3 -c "from control.nikon_ti2 import NikonTi2DIA; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add control/nikon_ti2.py
git commit -m "feat(nikon): implement NikonTi2DIA for real hardware"
```

---

### Task 11: Update NikonTi2Adapter to Return NikonTi2Components

**Files:**
- Modify: `control/nikon_ti2.py` (update NikonTi2Adapter class)

**Step 1: Add device candidates and new labels to __init__**

Update the `NikonTi2Adapter.__init__` to add filter wheel and DIA labels:

```python
    _FILTERWHEEL_CANDIDATES = ("FilterWheel Device", "FilterWheel", "Ti2FilterWheel", "Filter Wheel")
    _DIA_CANDIDATES = ("DIA Device", "DIA", "Ti2DIA", "DIA Lamp", "Transmitted Light")

    def __init__(
        self,
        core: Optional[CMMCorePlus] = None,
        *,
        unload_before_init: bool = True,
        scope_label: str = "Ti2Scope",
        scope_device_name: Optional[str] = None,
        xy_label: str = "XYStage",
        z_label: str = "ZDrive",
        pfs_label: str = "PFS",
        pfs_offset_label: str = "PFSOffset",
        filter_wheel_label: str = "FilterWheel",
        dia_label: str = "DIA",
        set_focus_to_z: bool = True,
        set_xy_stage_device: bool = True,
    ):
        self.core = core or CMMCorePlus.instance()
        self.unload_before_init = unload_before_init

        self.scope_label = scope_label
        self.scope_device_name = scope_device_name

        self.xy_label = xy_label
        self.z_label = z_label
        self.pfs_label = pfs_label
        self.pfs_offset_label = pfs_offset_label
        self.filter_wheel_label = filter_wheel_label
        self.dia_label = dia_label

        self.set_focus_to_z = set_focus_to_z
        self.set_xy_stage_device = set_xy_stage_device

        self._initialized = False
```

**Step 2: Update initialize method signature and implementation**

Replace the `initialize` method:

```python
    def initialize(
        self,
        *,
        stage_config: Any = None,
        use_stage: bool = True,
        use_pfs: bool = True,
        use_filter_wheel: bool = False,
        use_dia: bool = False,
    ) -> NikonTi2Components:
        """
        Load and initialize Ti2 devices based on flags.

        Returns NikonTi2Components with requested components (others are None).
        """
        if self.unload_before_init:
            try:
                self.core.unloadAllDevices()
            except Exception:
                pass

        scope_dev = self.scope_device_name or self._auto_select_scope_device_name()
        self._load(self.scope_label, self._MODULE, scope_dev)

        # Load requested sub-devices
        if use_stage:
            self._try_load(self.z_label, self._MODULE, self._ZDEV_CANDIDATES)
            self._try_load(self.xy_label, self._MODULE, self._XY_CANDIDATES)

        if use_pfs:
            self._try_load(self.pfs_label, self._MODULE, self._PFS_CANDIDATES)
            self._try_load(self.pfs_offset_label, self._MODULE, self._PFS_OFFSET_CANDIDATES)

        if use_filter_wheel:
            self._try_load(self.filter_wheel_label, self._MODULE, self._FILTERWHEEL_CANDIDATES)

        if use_dia:
            self._try_load(self.dia_label, self._MODULE, self._DIA_CANDIDATES)

        try:
            self.core.initializeAllDevices()
        except Exception as e:
            raise NikonTi2Exception(f"initializeAllDevices failed: {e}") from e

        if use_stage and self.set_focus_to_z:
            try:
                self.core.setFocusDevice(self.z_label)
            except Exception:
                pass

        if use_stage and self.set_xy_stage_device:
            try:
                self.core.setXYStageDevice(self.xy_label)
            except Exception:
                pass

        # Create component objects
        stage = None
        if use_stage:
            stage = NikonTi2Stage(self.core, stage_config, xy_label=self.xy_label, z_label=self.z_label)

        pfs = None
        if use_pfs:
            pfs = NikonTi2PFS(self.core, pfs_label=self.pfs_label, pfs_offset_label=self.pfs_offset_label)
            pfs.initialize_device()

        filter_wheel = None
        if use_filter_wheel:
            filter_wheel = NikonTi2FilterWheel(self.core, filter_wheel_label=self.filter_wheel_label)
            filter_wheel.initialize([1])

        dia = None
        if use_dia:
            dia = NikonTi2DIA(self.core, dia_label=self.dia_label)
            dia.initialize_device()

        self._initialized = True
        return NikonTi2Components(stage=stage, pfs=pfs, filter_wheel=filter_wheel, dia=dia)
```

**Step 3: Verify syntax**

Run: `python3 -c "from control.nikon_ti2 import NikonTi2Adapter; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add control/nikon_ti2.py
git commit -m "feat(nikon): update NikonTi2Adapter to return NikonTi2Components"
```

---

### Task 12: Update NikonTi2Adapter_Simulation

**Files:**
- Modify: `control/nikon_ti2.py` (update NikonTi2Adapter_Simulation class)

**Step 1: Update simulation adapter**

Replace `NikonTi2Adapter_Simulation` class:

```python
class NikonTi2Adapter_Simulation:
    """
    Simulated single-entry-point initializer for Nikon Ti2.

    On initialize(), this returns NikonTi2Components with simulated objects.
    """

    def __init__(
        self,
        *,
        xy_label: str = "XYStage",
        z_label: str = "ZDrive",
        pfs_label: str = "PFS",
        pfs_offset_label: str = "PFSOffset",
        filter_wheel_label: str = "FilterWheel",
        dia_label: str = "DIA",
        simulate_delays: bool = True,
    ):
        self.xy_label = xy_label
        self.z_label = z_label
        self.pfs_label = pfs_label
        self.pfs_offset_label = pfs_offset_label
        self.filter_wheel_label = filter_wheel_label
        self.dia_label = dia_label
        self.simulate_delays = simulate_delays

        self._initialized = False

    def initialize(
        self,
        *,
        stage_config: Any = None,
        use_stage: bool = True,
        use_pfs: bool = True,
        use_filter_wheel: bool = False,
        use_dia: bool = False,
    ) -> NikonTi2Components:
        """
        Initialize simulated Ti2 devices based on flags.

        Returns NikonTi2Components with simulated objects.
        """
        stage = None
        if use_stage:
            stage = NikonTi2Stage_Simulation(
                stage_config,
                xy_label=self.xy_label,
                z_label=self.z_label,
                simulate_delays=self.simulate_delays,
            )

        pfs = None
        if use_pfs:
            pfs = NikonTi2PFS_Simulation(
                pfs_label=self.pfs_label,
                pfs_offset_label=self.pfs_offset_label,
                simulate_delays=self.simulate_delays,
            )
            pfs.initialize_device()

        filter_wheel = None
        if use_filter_wheel:
            filter_wheel = NikonTi2FilterWheel_Simulation(
                filter_wheel_label=self.filter_wheel_label,
            )
            filter_wheel.initialize([1])

        dia = None
        if use_dia:
            dia = NikonTi2DIA_Simulation(
                dia_label=self.dia_label,
                simulate_delays=self.simulate_delays,
            )
            dia.initialize_device()

        self._initialized = True
        return NikonTi2Components(stage=stage, pfs=pfs, filter_wheel=filter_wheel, dia=dia)

    @property
    def is_initialized(self) -> bool:
        return bool(self._initialized)
```

**Step 2: Verify syntax**

Run: `python3 -c "from control.nikon_ti2 import NikonTi2Adapter_Simulation; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add control/nikon_ti2.py
git commit -m "feat(nikon): update NikonTi2Adapter_Simulation for new components"
```

---

### Task 13: Write and Run Adapter Integration Tests

**Files:**
- Modify: `tests/control/test_nikon_ti2.py`

**Step 1: Add adapter tests**

Append to test file:

```python
from control.nikon_ti2 import (
    NikonTi2Adapter_Simulation,
    NikonTi2Components,
    NikonTi2Stage_Simulation,
    NikonTi2PFS_Simulation,
)


class TestNikonTi2AdapterSimulation:
    """Tests for NikonTi2Adapter_Simulation."""

    def test_initialize_all_components(self):
        """Test initializing all components."""
        adapter = NikonTi2Adapter_Simulation()
        components = adapter.initialize(
            use_stage=True,
            use_pfs=True,
            use_filter_wheel=True,
            use_dia=True,
        )

        assert isinstance(components, NikonTi2Components)
        assert components.stage is not None
        assert components.pfs is not None
        assert components.filter_wheel is not None
        assert components.dia is not None

    def test_initialize_stage_only(self):
        """Test initializing only stage."""
        adapter = NikonTi2Adapter_Simulation()
        components = adapter.initialize(
            use_stage=True,
            use_pfs=False,
            use_filter_wheel=False,
            use_dia=False,
        )

        assert components.stage is not None
        assert components.pfs is None
        assert components.filter_wheel is None
        assert components.dia is None

    def test_initialize_nothing(self):
        """Test initializing no components."""
        adapter = NikonTi2Adapter_Simulation()
        components = adapter.initialize(
            use_stage=False,
            use_pfs=False,
            use_filter_wheel=False,
            use_dia=False,
        )

        assert components.stage is None
        assert components.pfs is None
        assert components.filter_wheel is None
        assert components.dia is None

    def test_components_are_initialized(self):
        """Test that returned components are already initialized."""
        adapter = NikonTi2Adapter_Simulation()
        components = adapter.initialize(
            use_stage=True,
            use_pfs=True,
            use_filter_wheel=True,
            use_dia=True,
        )

        # PFS, filter wheel, and DIA should be initialized
        assert components.pfs.is_initialized
        assert components.filter_wheel.is_initialized
        assert components.dia.is_initialized
```

**Step 2: Run all tests**

Run: `pytest tests/control/test_nikon_ti2.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/control/test_nikon_ti2.py
git commit -m "test(nikon): add adapter integration tests"
```

---

### Task 14: Update MicroscopeAddons in microscope.py

**Files:**
- Modify: `control/microscope.py:136-157` and `control/microscope.py:159-185`

**Step 1: Update build_from_global_config method**

Replace the Nikon initialization block (lines 136-156):

```python
        nikon_components = None
        if control._def.NIKON_BODY == "Ti2":
            from control.nikon_ti2 import NikonTi2Adapter, NikonTi2Adapter_Simulation

            adapter = (
                NikonTi2Adapter(unload_before_init=True)
                if not simulated
                else NikonTi2Adapter_Simulation()
            )
            nikon_components = adapter.initialize(
                stage_config=squid.config.get_stage_config(),
                use_stage=control._def.USE_NIKON_STAGE,
                use_pfs=control._def.USE_NIKON_PFS,
                use_filter_wheel=control._def.USE_NIKON_FILTER_WHEEL,
                use_dia=control._def.USE_NIKON_TRANSILLUMINATION,
            )

        return MicroscopeAddons(
            xlight,
            dragonfly,
            nl5,
            cellx,
            emission_filter_wheel,
            objective_changer,
            camera_focus,
            fluidics,
            piezo_stage,
            sci_microscopy_led_array,
            nikon_components.pfs if nikon_components else None,
            nikon_components.stage if nikon_components else None,
            nikon_components.filter_wheel if nikon_components else None,
            nikon_components.dia if nikon_components else None,
        )
```

**Step 2: Update __init__ method signature**

Update `MicroscopeAddons.__init__` to accept new parameters:

```python
    def __init__(
        self,
        xlight: Optional[serial_peripherals.XLight] = None,
        dragonfly: Optional[serial_peripherals.Dragonfly] = None,
        nl5: Optional[NL5] = None,
        cellx: Optional[serial_peripherals.CellX] = None,
        emission_filter_wheel: Optional[AbstractFilterWheelController] = None,
        objective_changer: Optional[ObjectiveChanger2PosController] = None,
        camera_focus: Optional[AbstractCamera] = None,
        fluidics: Optional[Fluidics] = None,
        piezo_stage: Optional[PiezoStage] = None,
        sci_microscopy_led_array: Optional[SciMicroscopyLEDArray] = None,
        nikon_pfs=None,
        nikon_stage: Optional[AbstractStage] = None,
        nikon_filter_wheel=None,
        nikon_dia=None,
    ):
        self.xlight: Optional[serial_peripherals.XLight] = xlight
        self.dragonfly: Optional[serial_peripherals.Dragonfly] = dragonfly
        self.nl5: Optional[NL5] = nl5
        self.cellx: Optional[serial_peripherals.CellX] = cellx
        self.emission_filter_wheel = emission_filter_wheel
        self.objective_changer = objective_changer
        self.camera_focus: Optional[AbstractCamera] = camera_focus
        self.fluidics = fluidics
        self.piezo_stage = piezo_stage
        self.sci_microscopy_led_array = sci_microscopy_led_array
        self.nikon_pfs = nikon_pfs
        self._nikon_stage: Optional[AbstractStage] = nikon_stage
        self.nikon_filter_wheel = nikon_filter_wheel
        self.nikon_dia = nikon_dia
```

**Step 3: Verify syntax**

Run: `python3 -c "import control.microscope; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add control/microscope.py
git commit -m "feat(nikon): update MicroscopeAddons for new Nikon components"
```

---

### Task 15: Update gui_hcs.py USE_NIKON_PFS References

**Files:**
- Modify: `control/gui_hcs.py:276-277`, `control/gui_hcs.py:560-561`, `control/gui_hcs.py:834-835`

**Step 1: Update line 276**

Change:
```python
        if USE_NIKON_PFS:
```
To:
```python
        if control._def.NIKON_BODY and control._def.USE_NIKON_PFS:
```

**Step 2: Update line 560**

Change:
```python
        if USE_NIKON_PFS:
```
To:
```python
        if control._def.NIKON_BODY and control._def.USE_NIKON_PFS:
```

**Step 3: Update line 834**

Change:
```python
        if USE_NIKON_PFS:
```
To:
```python
        if control._def.NIKON_BODY and control._def.USE_NIKON_PFS:
```

**Step 4: Verify syntax**

Run: `python3 -c "import control.gui_hcs; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add control/gui_hcs.py
git commit -m "refactor(nikon): update USE_NIKON_PFS checks to use NIKON_BODY gate"
```

---

### Task 16: Update CLAUDE.md Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update Nikon Ti2 Integration section**

Find the existing Nikon Ti2 section and replace it with:

```markdown
### Nikon Ti2 Integration

`control/nikon_ti2.py` provides Nikon Ti2 microscope control via **pymmcore-plus** (Micro-Manager Python binding). Enabled by setting `NIKON_BODY = Ti2` in `.ini` config.

**Configuration (`[Nikon]` section in .ini):**
- `nikon_body` - Set to `Ti2` to enable Nikon integration, `None` to disable
- `use_nikon_pfs` - Enable Perfect Focus System
- `use_nikon_stage` - Enable XY+Z stage control
- `use_nikon_filter_wheel` - Enable emission filter wheel
- `use_nikon_transillumination` - Enable DIA (transmitted light) control

**Key Classes:**
- `NikonTi2Adapter` - Single entry point that loads and initializes all Ti2 devices. Returns `NikonTi2Components` dataclass.
- `NikonTi2Stage` - XY+Z stage control implementing `AbstractStage`
- `NikonTi2PFS` - Perfect Focus System control
- `NikonTi2FilterWheel` - Emission filter wheel (6 positions)
- `NikonTi2DIA` - Transmitted light on/off and intensity control

**Simulation variants:** All classes have `*_Simulation` variants for testing without hardware.

**Usage pattern:**
```python
from control.nikon_ti2 import NikonTi2Adapter
adapter = NikonTi2Adapter(unload_before_init=True)
components = adapter.initialize(
    use_stage=True,
    use_pfs=True,
    use_filter_wheel=True,
    use_dia=True,
)

# Access components
stage = components.stage
pfs = components.pfs
filter_wheel = components.filter_wheel
dia = components.dia
```
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with expanded Nikon Ti2 integration"
```

---

### Task 17: Run Full Test Suite and Final Verification

**Files:** None (verification only)

**Step 1: Run all nikon tests**

Run: `pytest tests/control/test_nikon_ti2.py -v`
Expected: All tests PASS

**Step 2: Run control module tests**

Run: `pytest tests/control/ -v --ignore=tests/control/test_HighContentScreeningGui.py -x`
Expected: Tests PASS (GUI tests skipped as they require display)

**Step 3: Verify imports work end-to-end**

Run: `python3 -c "import control._def; import control.microscope; import control.nikon_ti2; print('All imports OK')"`
Expected: `All imports OK`

**Step 4: Create final commit if any uncommitted changes**

```bash
git status
# If clean, no action needed
```

---

Plan complete and saved to `docs/plans/2026-02-25-nikon-ti2-integration.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
