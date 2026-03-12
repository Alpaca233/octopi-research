from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Tuple, Sequence, Dict, Any, List

from pymmcore_plus import CMMCorePlus

# -----------------------------------------------------------------------------
# Optional integration with your Stage ABC
# -----------------------------------------------------------------------------
try:
    # Most likely location in your codebase.
    from squid.abc import AbstractStage, Pos, StageStage  # type: ignore
except Exception:
    try:
        # If you keep the ABC elsewhere, adjust this import to match.
        from abc import AbstractStage, Pos, StageStage  # type: ignore
    except Exception:
        # Minimal fallbacks so this module remains usable standalone.
        class AbstractStage:  # type: ignore
            def __init__(self, stage_config: Any = None):
                self._config = stage_config

        @dataclass
        class Pos:  # type: ignore
            x_mm: float
            y_mm: float
            z_mm: float
            theta_rad: Optional[float] = None

        @dataclass
        class StageStage:  # type: ignore
            busy: bool


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------
class NikonTi2Exception(RuntimeError):
    pass


class PFSException(NikonTi2Exception):
    pass


class StageException(NikonTi2Exception):
    pass


class NikonFilterWheelException(NikonTi2Exception):
    pass


class NikonDIAException(NikonTi2Exception):
    pass


# -----------------------------------------------------------------------------
# Components container
# -----------------------------------------------------------------------------
@dataclass
class NikonTi2Components:
    """Container for all Nikon Ti2 components returned by adapter initialization."""

    stage: Optional["NikonTi2Stage"] = None
    pfs: Optional["NikonTi2PFS"] = None
    filter_wheel: Optional["NikonTi2FilterWheel"] = None
    dia: Optional["NikonTi2DIA"] = None


# -----------------------------------------------------------------------------
# Unit helpers (Micro-Manager stage coordinates are generally in µm)
# -----------------------------------------------------------------------------
def _mm_to_um(mm: float) -> float:
    return float(mm) * 1000.0


def _um_to_mm(um: float) -> float:
    return float(um) / 1000.0


# -----------------------------------------------------------------------------
# Ti2 PFS
# -----------------------------------------------------------------------------
class NikonTi2PFS:
    """
    Nikon Ti2 PFS controller (pymmcore-plus) using the Micro-Manager NikonTi2 adapter.

    This class is written to be *robust across Ti2 adapter variations*:
    - It can auto-select the relevant properties if they differ.
    - It falls back gracefully if lock-status is not exposed by the adapter build.

    Public API (mirrors your Ti class):
      1) set_pfs_state(on: bool)
      2) get_pfs_state() -> bool
      3) set_offset(offset_um: float)
      4) get_offset() -> float
      5) wait_until_locked(timeout_s=2.0, settle_ms=50, poll_ms=5)

    Notes:
      - Many Ti2 setups expose a "FocusMaintenance" property on the PFS device
        to engage/disengage PFS. Some builds may use different names; this class
        probes property names at runtime.
      - Some Ti2 setups do NOT expose a detailed "Status" property. In that case,
        wait_until_locked() becomes best-effort (it can only wait a short settle).
    """

    # Property-name candidates (best-effort). The adapter may expose different ones.
    _PFS_ENABLE_CANDIDATES = ("FocusMaintenance", "State", "Enabled", "OnOff", "On/Off")
    _PFS_STATUS_CANDIDATES = ("Status", "PFSStatus", "FocusStatus", "LockStatus")
    _PFS_OFFSET_PROP_CANDIDATES = ("Position", "Offset", "PFSOffset", "Value")

    def __init__(
        self,
        core: Optional[CMMCorePlus] = None,
        *,
        pfs_label: str = "PFS",
        pfs_offset_label: str = "PFSOffset",
        unload_before_init: bool = False,
    ):
        self.core = core or CMMCorePlus.instance()
        self.pfs_label = pfs_label
        self.pfs_offset_label = pfs_offset_label
        self.unload_before_init = unload_before_init

        self._initialized = False
        self._prop_enable: Optional[str] = None
        self._prop_status: Optional[str] = None
        self._prop_offset: Optional[str] = None

    def initialize_device(self) -> None:
        """
        If you are using NikonTi2Adapter.initialize(), you typically do NOT need see this.
        This method is provided so NikonTi2PFS can also be used standalone (assuming
        your devices are already loaded).
        """
        if self.unload_before_init:
            try:
                self.core.unloadAllDevices()
            except Exception:
                pass

        # Resolve properties.
        self._prop_enable = self._pick_property(self.pfs_label, self._PFS_ENABLE_CANDIDATES, must=True)
        self._prop_status = self._pick_property(self.pfs_label, self._PFS_STATUS_CANDIDATES, must=False)
        # self._prop_offset = self._pick_property(self.pfs_offset_label, self._PFS_OFFSET_PROP_CANDIDATES, must=True)

        self._initialized = True

    def set_pfs_state(self, on: bool) -> None:
        self._require_initialized()
        assert self._prop_enable is not None
        self._set_bool_property(self.pfs_label, self._prop_enable, on)

    def get_pfs_state(self) -> bool:
        self._require_initialized()
        assert self._prop_enable is not None
        val = self.core.getProperty(self.pfs_label, self._prop_enable)
        return self._to_bool(val)

    def set_offset(self, offset_um: float) -> None:
        self._require_initialized()
        # assert self._prop_offset is not None
        try:
            # self.core.setProperty(self.pfs_offset_label, self._prop_offset, float(offset_um))
            self.core.setPosition(self.pfs_offset_label, float(offset_um))
        except Exception as e:
            print(e)
            raise PFSException(
                f"Failed to set Ti2 PFS offset via {self.pfs_offset_label}.{self._prop_offset} to {offset_um} µm: {e}"
            ) from e

    def get_offset(self) -> float:
        self._require_initialized()
        # assert self._prop_offset is not None
        try:
            # val = self.core.getProperty(self.pfs_offset_label, self._prop_offset)
            val = self.core.getPosition(self.pfs_offset_label)
            return float(val)
        except Exception as e:
            raise PFSException(
                f"Failed to read Ti2 PFS offset via {self.pfs_offset_label}.{self._prop_offset}: {e}"
            ) from e

    def wait_until_locked(
        self,
        timeout_s: float = 2.0,
        *,
        settle_ms: int = 50,
        poll_ms: int = 5,
        allow_when_off: bool = False,
    ) -> None:
        """
        Wait until PFS reports 'locked', if that information is exposed.
        If lock-status isn't exposed (common on some Ti2 adapter builds), this falls back to:
          - returning immediately if allow_when_off and PFS is off
          - otherwise waiting `settle_ms` and returning (best effort)
        """
        self._require_initialized()

        if allow_when_off and not self.get_pfs_state():
            return

        if not self._prop_status:
            # Best-effort fallback: we cannot observe "locked", so we can only settle briefly.
            self.core.sleep(int(settle_ms))
            return

        t0 = time.time()
        last = None
        while True:
            try:
                status = self.core.getProperty(self.pfs_label, self._prop_status)
                last = status
            except Exception as e:
                raise PFSException(f"Failed to read Ti2 PFS status: {e}") from e

            if self._is_locked(status):
                self.core.sleep(int(settle_ms))
                return

            if (time.time() - t0) > float(timeout_s):
                raise TimeoutError(f"Ti2 PFS did not lock in {timeout_s:.3f}s (last status: {last!r})")

            self.core.sleep(int(poll_ms))

    # ----- helpers -----
    def _require_initialized(self) -> None:
        if not self._initialized:
            raise PFSException("Call initialize_device() first, or use NikonTi2Adapter.initialize().")

    def _pick_property(self, dev: str, candidates: Sequence[str], *, must: bool) -> Optional[str]:
        try:
            props = set(self.core.getDevicePropertyNames(dev))
        except Exception as e:
            raise PFSException(f"Cannot read properties for device '{dev}'. Is it loaded? ({e})") from e

        for p in candidates:
            if p in props:
                return p

        # helpful heuristic fallback
        lowered = {p.lower(): p for p in props}
        for cand in candidates:
            if cand.lower() in lowered:
                return lowered[cand.lower()]

        if must:
            raise PFSException(
                f"Could not find required property on '{dev}'. "
                f"Tried: {list(candidates)}. Available: {sorted(props)}"
            )
        return None

    def _set_bool_property(self, dev: str, prop: str, on: bool) -> None:
        """
        Set a boolean-ish Micro-Manager property robustly by consulting allowed values first.
        """
        target_bool = bool(on)

        allowed: List[str] = []
        try:
            allowed = list(self.core.getAllowedPropertyValues(dev, prop))
        except Exception:
            allowed = []

        def pick_value() -> str:
            if not allowed:
                # common safe defaults
                return "On" if target_bool else "Off"

            # Prefer explicit On/Off if present
            allowed_lower = [a.strip().lower() for a in allowed]
            if "on" in allowed_lower and "off" in allowed_lower:
                return allowed[allowed_lower.index("on")] if target_bool else allowed[allowed_lower.index("off")]

            # Numeric toggles
            if "1" in allowed_lower and "0" in allowed_lower:
                return "1" if target_bool else "0"

            # True/False toggles
            if "true" in allowed_lower and "false" in allowed_lower:
                return allowed[allowed_lower.index("true")] if target_bool else allowed[allowed_lower.index("false")]

            # Fallback: pick first that matches target as interpreted boolean
            for a in allowed:
                if self._to_bool(a) == target_bool:
                    return a

            # Last resort: just use the first allowed value for True, last for False
            return allowed[0] if target_bool else allowed[-1]

        val = pick_value()
        try:
            self.core.setProperty(dev, prop, val)
        except Exception as e:
            raise PFSException(f'Failed to set {dev}.{prop}="{val}" (allowed={allowed}): {e}') from e

        # optional readback check (not strict because some adapters lag / re-map values)
        try:
            readback = self.core.getProperty(dev, prop)
            if self._to_bool(readback) != target_bool:
                # do not hard-fail; this sometimes happens transiently
                pass
        except Exception:
            pass

    @staticmethod
    def _to_bool(val: Any) -> bool:
        if isinstance(val, (int, float)):
            return int(val) != 0
        s = str(val).strip().lower()
        if s in ("on", "1", "true", "enabled", "enable", "yes"):
            return True
        if s in ("off", "0", "false", "disabled", "disable", "no"):
            return False
        if s.startswith("on"):
            return True
        if s.startswith("off"):
            return False
        return False

    @staticmethod
    def _is_locked(status: Any) -> bool:
        # Numeric schemes sometimes use >= 2 for "locked"
        if isinstance(status, (int, float)):
            return int(status) >= 2
        return "locked" in str(status).lower()

    @property
    def is_initialized(self) -> bool:
        return bool(self._initialized)


# -----------------------------------------------------------------------------
# Ti2 Stage (XY + Z) implementing your AbstractStage interface
# -----------------------------------------------------------------------------
class NikonTi2Stage(AbstractStage):
    """
    Nikon Ti2 stage wrapper (XYStage + ZDrive) using the Micro-Manager NikonTi2 adapter.

    Units:
      - Your AbstractStage uses mm; Micro-Manager uses µm internally.
      - This class converts mm <-> µm at the boundary.
    """

    def __init__(
        self,
        core: Optional[CMMCorePlus] = None,
        stage_config: Any = None,
        *,
        xy_label: str = "XYStage",
        z_label: str = "ZDrive",
    ):
        try:
            super().__init__(stage_config)
        except Exception:
            # If AbstractStage is a stub or has different init in your environment.
            self._config = stage_config
        self.core = core or CMMCorePlus.instance()
        self.xy_label = xy_label
        self.z_label = z_label

        # Optional software limits (in mm). None means "no limit".
        self._limits: Dict[str, Tuple[Optional[float], Optional[float]]] = {
            "x": (None, None),
            "y": (None, None),
            "z": (None, None),
        }

    # --- relative moves ---
    def move_x(self, rel_mm: float, blocking: bool = True):
        dx_um = _mm_to_um(rel_mm)
        self._move_xy_um(dx_um, 0.0, blocking=blocking)

    def move_y(self, rel_mm: float, blocking: bool = True):
        dy_um = _mm_to_um(rel_mm)
        self._move_xy_um(0.0, dy_um, blocking=blocking)

    def move_z(self, rel_mm: float, blocking: bool = True):
        dz_um = _mm_to_um(rel_mm)
        self._move_z_um_relative(dz_um, blocking=blocking)

    # --- absolute moves ---
    def move_x_to(self, abs_mm: float, blocking: bool = True):
        x_um, y_um = self._get_xy_um()
        target_x_um = _mm_to_um(abs_mm)
        # self._enforce_limits("x", abs_mm)
        self._set_xy_um(target_x_um, y_um, blocking=blocking)

    def move_y_to(self, abs_mm: float, blocking: bool = True):
        x_um, y_um = self._get_xy_um()
        target_y_um = _mm_to_um(abs_mm)
        # self._enforce_limits("y", abs_mm)
        self._set_xy_um(x_um, target_y_um, blocking=blocking)

    def move_z_to(self, abs_mm: float, blocking: bool = True):
        # self._enforce_limits("z", abs_mm)
        target_z_um = _mm_to_um(abs_mm)
        self._set_z_um(target_z_um, blocking=blocking)

    # --- status/position ---
    def get_pos(self) -> Pos:
        x_um, y_um = self._get_xy_um()
        z_um = self._get_z_um()
        return Pos(x_mm=_um_to_mm(x_um), y_mm=_um_to_mm(y_um), z_mm=_um_to_mm(z_um), theta_rad=None)

    def get_state(self) -> StageStage:
        busy = False
        try:
            busy = bool(self.core.deviceBusy(self.xy_label) or self.core.deviceBusy(self.z_label))
        except Exception:
            # Conservative
            busy = True
        return StageStage(busy=busy)

    # --- homing / zeroing ---
    def home(self, x: bool, y: bool, z: bool, theta: bool, blocking: bool = True):
        pass
        """
        if theta:
            raise NotImplementedError("Ti2 theta stage control not implemented in this wrapper.")

        # In Micro-Manager, XY is one device, so home x/y together.
        if x or y:
            self._call_home(self.xy_label, blocking=blocking)
        if z:
            self._call_home(self.z_label, blocking=blocking)
        """

    def zero(self, x: bool, y: bool, z: bool, theta: bool, blocking: bool = True):
        if theta:
            raise NotImplementedError("Ti2 theta stage control not implemented in this wrapper.")

        # Micro-Manager provides setOriginXY / setOrigin where available.
        if x or y:
            try:
                self.core.setOriginXY(self.xy_label)
            except Exception as e:
                raise StageException(f"Failed to set XY origin: {e}") from e

        if z:
            try:
                self.core.setOrigin(self.z_label)
            except Exception as e:
                raise StageException(f"Failed to set Z origin: {e}") from e

        if blocking:
            self._wait_for_devices([self.xy_label, self.z_label], timeout_s=5.0)

    def set_limits(
        self,
        x_pos_mm: Optional[float] = None,
        x_neg_mm: Optional[float] = None,
        y_pos_mm: Optional[float] = None,
        y_neg_mm: Optional[float] = None,
        z_pos_mm: Optional[float] = None,
        z_neg_mm: Optional[float] = None,
        theta_pos_rad: Optional[float] = None,
        theta_neg_rad: Optional[float] = None,
    ):
        # Only software limits here. (Micro-Manager generally doesn't offer a universal way
        # to set hardware limits.)
        if theta_pos_rad is not None or theta_neg_rad is not None:
            raise NotImplementedError("Theta limits not supported in this wrapper.")

        self._limits["x"] = (x_neg_mm, x_pos_mm)
        self._limits["y"] = (y_neg_mm, y_pos_mm)
        self._limits["z"] = (z_neg_mm, z_pos_mm)

    # ----- internal helpers -----
    def _enforce_limits(self, axis: str, value_mm: float) -> None:
        neg, pos = self._limits[axis]
        if neg is not None and value_mm < neg:
            raise StageException(f"{axis}-axis target {value_mm} mm is below limit {neg} mm")
        if pos is not None and value_mm > pos:
            raise StageException(f"{axis}-axis target {value_mm} mm is above limit {pos} mm")

    def _get_xy_um(self) -> Tuple[float, float]:
        try:
            x_um, y_um = self.core.getXYPosition(self.xy_label)
            return float(x_um), float(y_um)
        except Exception as e:
            raise StageException(f"Failed to read XY position from '{self.xy_label}': {e}") from e

    def _get_z_um(self) -> float:
        try:
            z_um = self.core.getPosition(self.z_label)
            return float(z_um)
        except Exception as e:
            raise StageException(f"Failed to read Z position from '{self.z_label}': {e}") from e

    def _move_xy_um(self, dx_um: float, dy_um: float, *, blocking: bool) -> None:
        # Convert software limits (absolute) if present by computing target.
        if any(v is not None for lims in (self._limits["x"], self._limits["y"]) for v in lims):
            x_um, y_um = self._get_xy_um()
            # self._enforce_limits("x", _um_to_mm(x_um + dx_um))
            # self._enforce_limits("y", _um_to_mm(y_um + dy_um))

        try:
            self.core.setRelativeXYPosition(self.xy_label, float(dx_um), float(dy_um))
        except Exception as e:
            raise StageException(f"Failed relative XY move ({dx_um} µm, {dy_um} µm) on '{self.xy_label}': {e}") from e

        if blocking:
            self._wait_for_devices([self.xy_label], timeout_s=30.0)

    def _set_xy_um(self, x_um: float, y_um: float, *, blocking: bool) -> None:
        try:
            self.core.setXYPosition(self.xy_label, float(x_um), float(y_um))
        except Exception as e:
            raise StageException(f"Failed absolute XY move to ({x_um} µm, {y_um} µm) on '{self.xy_label}': {e}") from e

        if blocking:
            self._wait_for_devices([self.xy_label], timeout_s=30.0)

    def _move_z_um_relative(self, dz_um: float, *, blocking: bool) -> None:
        if any(v is not None for v in self._limits["z"]):
            z_um = self._get_z_um()
            self._enforce_limits("z", _um_to_mm(z_um + dz_um))

        try:
            self.core.setRelativePosition(self.z_label, float(dz_um))
        except Exception as e:
            raise StageException(f"Failed relative Z move ({dz_um} µm) on '{self.z_label}': {e}") from e

        if blocking:
            self._wait_for_devices([self.z_label], timeout_s=30.0)

    def _set_z_um(self, z_um: float, *, blocking: bool) -> None:
        try:
            self.core.setPosition(self.z_label, float(z_um))
        except Exception as e:
            raise StageException(f"Failed absolute Z move to ({z_um} µm) on '{self.z_label}': {e}") from e

        if blocking:
            self._wait_for_devices([self.z_label], timeout_s=30.0)

    def _call_home(self, dev_label: str, *, blocking: bool) -> None:
        try:
            self.core.home(dev_label)
        except Exception as e:
            raise StageException(f"Failed to home device '{dev_label}': {e}") from e

        if blocking:
            self._wait_for_devices([dev_label], timeout_s=60.0)

    def _wait_for_devices(self, devs: Sequence[str], *, timeout_s: float) -> None:
        # MMCore has waitForDevice(label), but we also handle a generic busy loop as a fallback.
        t0 = time.time()
        for dev in devs:
            try:
                self.core.waitForDevice(dev)
            except Exception:
                # fallback busy loop
                while True:
                    if (time.time() - t0) > timeout_s:
                        raise StageException(f"Timed out waiting for devices {list(devs)}")
                    try:
                        if not self.core.deviceBusy(dev):
                            break
                    except Exception:
                        # If busy state can't be read, just sleep and keep trying.
                        pass
                    time.sleep(0.002)


# -----------------------------------------------------------------------------
# Ti2 Filter Wheel
# -----------------------------------------------------------------------------
class NikonTi2FilterWheel:
    """
    Nikon Ti2 emission filter wheel via Micro-Manager NikonTi2 adapter.

    Implements AbstractFilterWheelController interface for single emission wheel.
    Ti2 typically has 6 positions (1-6).
    """

    _POSITION_PROP_CANDIDATES = ("Position", "State")

    def __init__(
        self,
        core: Optional[CMMCorePlus] = None,
        *,
        filter_wheel_label: str = "FilterWheel1",
        num_positions: int = 6,
    ):
        self.core = core or CMMCorePlus.instance()
        self.filter_wheel_label = filter_wheel_label
        self._num_positions = num_positions
        self._initialized = False
        self._prop_position: Optional[str] = None

    def initialize(self, filter_wheel_indices: List[int]):
        """Initialize the filter wheel and resolve properties."""
        self._prop_position = self._pick_property(self.filter_wheel_label, self._POSITION_PROP_CANDIDATES, must=False)
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
            raise NikonFilterWheelException(f"Position {pos} out of range [1, {self._num_positions}]")

        try:
            # Try setPosition first (common for state devices)
            self.core.setPosition(self.filter_wheel_label, float(pos - 1))  # 0-indexed in MM
        except Exception:
            # Fall back to property-based control
            if self._prop_position:
                self.core.setProperty(self.filter_wheel_label, self._prop_position, str(pos))
            else:
                raise NikonFilterWheelException("Cannot set filter wheel position: no position property found")

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
            raise NikonFilterWheelException(f"Could not find required property on '{dev}'. Tried: {list(candidates)}")
        return None


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
        dia_label: str = "DiaLamp",
    ):
        self.core = core or CMMCorePlus.instance()
        self.dia_label = dia_label
        self._initialized = False
        self._prop_state: Optional[str] = None
        self._prop_intensity: Optional[str] = None

    def initialize_device(self) -> None:
        """Initialize the DIA device and resolve properties."""
        self._prop_state = self._pick_property(self.dia_label, self._STATE_PROP_CANDIDATES, must=False)
        self._prop_intensity = self._pick_property(self.dia_label, self._INTENSITY_PROP_CANDIDATES, must=False)
        self._initialized = True

    def set_state(self, on: bool) -> None:
        """Turn DIA on or off."""
        self._require_initialized()

        if self._prop_state:
            val = "1" if on else "0"
            try:
                allowed = list(self.core.getAllowedPropertyValues(self.dia_label, self._prop_state))
                if allowed:
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
        magic_number = 21
        intensity = intensity_percent * magic_number

        if self._prop_intensity:
            try:
                self.core.setProperty(self.dia_label, self._prop_intensity, str(intensity))
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
            raise NikonDIAException(f"Could not find required property on '{dev}'. Tried: {list(candidates)}")
        return None


# -----------------------------------------------------------------------------
# Adapter: initializes NikonTi2 devices, returns NikonTi2Components
# -----------------------------------------------------------------------------
class NikonTi2Adapter:
    """
    Single-entry-point initializer for Nikon Ti2 with:
      - Stage control (XYStage + ZDrive)
      - PFS control (PFS + PFSOffset)
      - Filter wheel control
      - DIA (transillumination) control

    On initialize(), this returns a NikonTi2Components object with requested components.

    The scope device name on Ti2 often includes a hardware identifier, e.g.
    '*Ti2-E__0'. If you don't pass scope_device_name, we will auto-select the first
    non-simulator option exposed by the NikonTi2 module.

    Reference: Micro-Manager NikonTi2 adapter notes mention Ti2 Control and that the
    microscope may appear as '*Ti2-E__0: Nikon Ti2 microscope' in the config wizard.
    """

    _MODULE = "NikonTi2"

    # Device-name candidates for sub-devices. These are selected by trying in order.
    _ZDEV_CANDIDATES = ("ZDrive Device", "ZDrive", "Ti2ZDrive", "Ti2 ZDrive")
    _XY_CANDIDATES = ("XYStage Device", "XYStage", "Ti2XYStage", "Ti2 XYStage")
    _PFS_CANDIDATES = ("PFS Device", "PFS", "Ti2PFS")
    _PFS_OFFSET_CANDIDATES = ("PFSOffset Device", "PFSOffset", "Ti2PFSOffset", "PFS Offset")
    _FILTERWHEEL_CANDIDATES = ("FilterWheel Device", "FilterWheel", "Ti2FilterWheel", "Filter Wheel", "FilterWheel1")
    _DIA_CANDIDATES = ("DIA Device", "DIA", "Ti2DIA", "DIA Lamp", "Transmitted Light", "DiaLamp")

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
        filter_wheel_label: str = "FilterWheel1",
        dia_label: str = "DiaLamp",
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

    # ----- helpers -----
    def _auto_select_scope_device_name(self) -> str:
        """
        Choose the first non-simulator scope device from NikonTi2's available devices.
        """
        try:
            devs = list(self.core.getAvailableDevices(self._MODULE))
        except Exception as e:
            raise NikonTi2Exception(
                f"Failed to enumerate available devices for module '{self._MODULE}'. Is the adapter installed? ({e})"
            ) from e

        # The wiki notes that you may see '*Ti2-Simulator' and one or more real microscopes.
        # We'll pick the first device that looks like real hardware.
        for d in devs:
            ds = str(d)
            if "simulator" in ds.lower():
                continue
            # Child devices are typically "... Device"; scope device usually isn't.
            if ds.strip().lower().endswith("device"):
                continue
            # Often begins with "*Ti2"
            return ds

        raise NikonTi2Exception(
            f"Could not auto-select a Ti2 scope device. Available devices from '{self._MODULE}': {devs}"
        )

    def _load(self, label: str, module: str, devname: str) -> None:
        if label in self.core.getLoadedDevices():
            return
        try:
            self.core.loadDevice(label, module, devname)
        except Exception as e:
            raise NikonTi2Exception(f"loadDevice('{label}','{module}','{devname}') failed: {e}") from e

    def _try_load(self, label: str, module: str, candidates: Sequence[str]) -> None:
        if label in self.core.getLoadedDevices():
            return

        errors = []
        for devname in candidates:
            try:
                self.core.loadDevice(label, module, devname)
                return
            except Exception as e:
                errors.append(f"{devname!r}: {e}")

        raise NikonTi2Exception(
            f"Failed to load '{label}' from module '{module}'. Tried device names: {list(candidates)}.\n"
            f"Errors: {errors}"
        )

    @property
    def is_initialized(self) -> bool:
        return bool(self._initialized)
    

# -----------------------------------------------------------------------------
# Simulated Ti2 PFS
# -----------------------------------------------------------------------------
class NikonTi2PFS_Simulation:
    """
    Simulated Nikon Ti2 PFS controller for testing without hardware.

    Provides the same API as NikonTi2PFS but stores state internally
    without requiring actual hardware or Micro-Manager.
    """

    def __init__(
        self,
        *,
        pfs_label: str = "PFS",
        pfs_offset_label: str = "PFSOffset",
        simulate_delays: bool = True,
    ):
        self.pfs_label = pfs_label
        self.pfs_offset_label = pfs_offset_label
        self.simulate_delays = simulate_delays

        self._initialized = False
        self._pfs_on = False
        self._offset_um = 0.0
        self._locked = False

    def initialize_device(self) -> None:
        """Initialize the simulated PFS device."""
        self._initialized = True
        self._pfs_on = False
        self._offset_um = 0.0
        self._locked = False

    def set_pfs_state(self, on: bool) -> None:
        self._require_initialized()
        self._pfs_on = bool(on)
        if on:
            # When turning on, simulate acquiring lock after a brief delay
            if self.simulate_delays:
                time.sleep(0.1)
            self._locked = True
        else:
            self._locked = False

    def get_pfs_state(self) -> bool:
        self._require_initialized()
        return self._pfs_on

    def set_offset(self, offset_um: float) -> None:
        self._require_initialized()
        self._offset_um = float(offset_um)
        if self.simulate_delays:
            time.sleep(0.01)

    def get_offset(self) -> float:
        self._require_initialized()
        return self._offset_um

    def wait_until_locked(
        self,
        timeout_s: float = 2.0,
        *,
        settle_ms: int = 50,
        poll_ms: int = 5,
        allow_when_off: bool = False,
    ) -> None:
        """
        Wait until PFS is locked.
        In simulation, this immediately succeeds if PFS is on.
        """
        self._require_initialized()

        if allow_when_off and not self._pfs_on:
            return

        if not self._pfs_on:
            raise TimeoutError("Simulated PFS is not on, cannot lock")

        # Simulate settling time
        if self.simulate_delays:
            time.sleep(settle_ms / 1000.0)

        self._locked = True

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise PFSException("Call initialize_device() first.")

    @property
    def is_initialized(self) -> bool:
        return bool(self._initialized)

    @property
    def is_locked(self) -> bool:
        """Additional property for simulation: check if PFS is locked."""
        return self._locked


# -----------------------------------------------------------------------------
# Simulated Ti2 Stage (XY + Z)
# -----------------------------------------------------------------------------
class NikonTi2Stage_Simulation(AbstractStage):
    """
    Simulated Nikon Ti2 stage wrapper (XY + Z) for testing without hardware.

    Units: mm (consistent with AbstractStage interface)
    """

    def __init__(
        self,
        stage_config: Any = None,
        *,
        xy_label: str = "XYStage",
        z_label: str = "ZDrive",
        simulate_delays: bool = True,
    ):
        try:
            super().__init__(stage_config)
        except Exception:
            self._config = stage_config
        self.xy_label = xy_label
        self.z_label = z_label
        self.simulate_delays = simulate_delays

        # Simulated position state (in mm)
        self._x_mm = 0.0
        self._y_mm = 0.0
        self._z_mm = 0.0

        # Movement simulation parameters
        self._xy_speed_mm_per_s = 10.0  # mm/s for XY movement
        self._z_speed_mm_per_s = 2.0  # mm/s for Z movement
        self._busy = False

        # Software limits (in mm). None means "no limit".
        self._limits: Dict[str, Tuple[Optional[float], Optional[float]]] = {
            "x": (None, None),
            "y": (None, None),
            "z": (None, None),
        }

    # --- relative moves ---
    def move_x(self, rel_mm: float, blocking: bool = True):
        target = self._x_mm + rel_mm
        # self._enforce_limits("x", target)
        self._simulate_move("xy", abs(rel_mm), blocking)
        self._x_mm = target

    def move_y(self, rel_mm: float, blocking: bool = True):
        target = self._y_mm + rel_mm
        # self._enforce_limits("y", target)
        self._simulate_move("xy", abs(rel_mm), blocking)
        self._y_mm = target

    def move_z(self, rel_mm: float, blocking: bool = True):
        target = self._z_mm + rel_mm
        # self._enforce_limits("z", target)
        self._simulate_move("z", abs(rel_mm), blocking)
        self._z_mm = target

    # --- absolute moves ---
    def move_x_to(self, abs_mm: float, blocking: bool = True):
        # self._enforce_limits("x", abs_mm)
        distance = abs(abs_mm - self._x_mm)
        self._simulate_move("xy", distance, blocking)
        self._x_mm = abs_mm

    def move_y_to(self, abs_mm: float, blocking: bool = True):
        # self._enforce_limits("y", abs_mm)
        distance = abs(abs_mm - self._y_mm)
        self._simulate_move("xy", distance, blocking)
        self._y_mm = abs_mm

    def move_z_to(self, abs_mm: float, blocking: bool = True):
        # self._enforce_limits("z", abs_mm)
        distance = abs(abs_mm - self._z_mm)
        self._simulate_move("z", distance, blocking)
        self._z_mm = abs_mm

    # --- status/position ---
    def get_pos(self) -> Pos:
        return Pos(x_mm=self._x_mm, y_mm=self._y_mm, z_mm=self._z_mm, theta_rad=None)

    def get_state(self) -> StageStage:
        return StageStage(busy=self._busy)

    # --- homing / zeroing ---
    def home(self, x: bool, y: bool, z: bool, theta: bool, blocking: bool = True):
        if theta:
            raise NotImplementedError("Ti2 theta stage control not implemented in this wrapper.")

        if x or y:
            if self.simulate_delays and blocking:
                time.sleep(0.5)  # Simulate homing delay
            if x:
                self._x_mm = 0.0
            if y:
                self._y_mm = 0.0

        if z:
            if self.simulate_delays and blocking:
                time.sleep(0.3)  # Simulate homing delay
            self._z_mm = 0.0

    def zero(self, x: bool, y: bool, z: bool, theta: bool, blocking: bool = True):
        if theta:
            raise NotImplementedError("Ti2 theta stage control not implemented in this wrapper.")

        # Zeroing sets current position as origin
        if x:
            self._x_mm = 0.0
        if y:
            self._y_mm = 0.0
        if z:
            self._z_mm = 0.0

    def set_limits(
        self,
        x_pos_mm: Optional[float] = None,
        x_neg_mm: Optional[float] = None,
        y_pos_mm: Optional[float] = None,
        y_neg_mm: Optional[float] = None,
        z_pos_mm: Optional[float] = None,
        z_neg_mm: Optional[float] = None,
        theta_pos_rad: Optional[float] = None,
        theta_neg_rad: Optional[float] = None,
    ):
        if theta_pos_rad is not None or theta_neg_rad is not None:
            raise NotImplementedError("Theta limits not supported in this wrapper.")

        self._limits["x"] = (x_neg_mm, x_pos_mm)
        self._limits["y"] = (y_neg_mm, y_pos_mm)
        self._limits["z"] = (z_neg_mm, z_pos_mm)

    # ----- internal helpers -----
    def _enforce_limits(self, axis: str, value_mm: float) -> None:
        neg, pos = self._limits[axis]
        if neg is not None and value_mm < neg:
            raise StageException(f"{axis}-axis target {value_mm} mm is below limit {neg} mm")
        if pos is not None and value_mm > pos:
            raise StageException(f"{axis}-axis target {value_mm} mm is above limit {pos} mm")

    def _simulate_move(self, axis_type: str, distance_mm: float, blocking: bool) -> None:
        """Simulate movement delay based on distance and speed."""
        if not self.simulate_delays:
            return

        if axis_type == "xy":
            speed = self._xy_speed_mm_per_s
        else:
            speed = self._z_speed_mm_per_s

        move_time = distance_mm / speed if speed > 0 else 0

        if blocking:
            self._busy = True
            time.sleep(min(move_time, 1.0))  # Cap at 1 second for simulation
            self._busy = False


# -----------------------------------------------------------------------------
# Simulated Ti2 Filter Wheel
# -----------------------------------------------------------------------------
class NikonTi2FilterWheel_Simulation:
    """
    Simulated Nikon Ti2 filter wheel for testing without hardware.

    Implements AbstractFilterWheelController interface.
    Ti2 typically has a single 6-position emission filter wheel.
    """

    def __init__(self, *, filter_wheel_label: str = "FilterWheel1", num_positions: int = 6):
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
        self._require_initialized()
        self._position = 1

    def set_filter_wheel_position(self, positions: Dict[int, int]):
        """Set filter wheel position."""
        self._require_initialized()
        if 1 in positions:
            pos = positions[1]
            if not (1 <= pos <= self._num_positions):
                raise NikonFilterWheelException(f"Position {pos} out of range [1, {self._num_positions}]")
            self._position = pos

    def get_filter_wheel_position(self) -> Dict[int, int]:
        """Get current filter wheel position."""
        self._require_initialized()
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

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise NikonFilterWheelException("Call initialize() first.")


# -----------------------------------------------------------------------------
# Simulated Ti2 DIA (Transmitted Light)
# -----------------------------------------------------------------------------
class NikonTi2DIA_Simulation:
    """
    Simulated Nikon Ti2 DIA (transmitted light) controller for testing.

    Provides on/off control and intensity adjustment (0-100%).
    """

    def __init__(self, *, dia_label: str = "DiaLamp", simulate_delays: bool = False):
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


# -----------------------------------------------------------------------------
# Simulated Adapter: returns simulated NikonTi2Components
# -----------------------------------------------------------------------------
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
