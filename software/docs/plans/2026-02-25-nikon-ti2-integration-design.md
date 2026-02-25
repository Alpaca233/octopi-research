# Nikon Ti2 Extended Integration Design

**Date:** 2026-02-25
**Status:** Approved

## Overview

Extend the existing Nikon Ti2 integration to support filter wheel and transillumination (DIA) control, with a unified configuration section in `.ini` files.

## Requirements

- Add Nikon filter wheel control (single emission filter wheel)
- Add Nikon DIA (transillumination) control with on/off and intensity (0-100%)
- Create `[Nikon]` configuration section with body type and per-component flags
- Integrate as MicroscopeAddons (consistent with existing nikon_pfs/nikon_stage pattern)
- Design for future expansion to other Nikon bodies (Ti, Ti-U)

## Design

### Configuration

**New `[Nikon]` section in `.ini` files:**

```ini
[Nikon]
nikon_body = Ti2
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

**Corresponding variables in `_def.py`:**

```python
# Nikon Ti2 Integration
NIKON_BODY = None  # "Ti2" or None
USE_NIKON_PFS = False
USE_NIKON_STAGE = False
USE_NIKON_FILTER_WHEEL = False
USE_NIKON_TRANSILLUMINATION = False
```

**Behavior:**
- `NIKON_BODY = None` disables all Nikon integration (other flags ignored)
- `NIKON_BODY = "Ti2"` enables Nikon support; individual flags control which components initialize

### New Classes in `nikon_ti2.py`

**NikonTi2FilterWheel** - Implements `AbstractFilterWheelController`:

```python
class NikonTi2FilterWheel(AbstractFilterWheelController):
    """Single emission filter wheel via Micro-Manager NikonTi2 adapter."""

    def __init__(self, core: CMMCorePlus, filter_wheel_label: str = "FilterWheel"):
        ...

    # Implements: initialize(), set_filter_wheel_position(),
    # get_filter_wheel_position(), home(), close(), etc.
    # Ti2 filter wheel positions are typically 1-6
    # Delay methods return None (hardware-controlled timing)
```

**NikonTi2DIA** - On/off + intensity control:

```python
class NikonTi2DIA:
    """Nikon Ti2 transmitted light (DIA) controller."""

    def __init__(self, core: CMMCorePlus, dia_label: str = "DIA"):
        ...

    def set_state(self, on: bool) -> None: ...
    def get_state(self) -> bool: ...
    def set_intensity(self, intensity_percent: float) -> None: ...
    def get_intensity(self) -> float: ...
```

**Simulation variants:**
- `NikonTi2FilterWheel_Simulation` - stores position in memory
- `NikonTi2DIA_Simulation` - stores state/intensity in memory

### Updated NikonTi2Adapter

```python
@dataclass
class NikonTi2Components:
    stage: Optional[NikonTi2Stage]
    pfs: Optional[NikonTi2PFS]
    filter_wheel: Optional[NikonTi2FilterWheel]
    dia: Optional[NikonTi2DIA]


class NikonTi2Adapter:
    def __init__(
        self,
        core: Optional[CMMCorePlus] = None,
        *,
        unload_before_init: bool = True,
        scope_label: str = "Ti2Scope",
        xy_label: str = "XYStage",
        z_label: str = "ZDrive",
        pfs_label: str = "PFS",
        pfs_offset_label: str = "PFSOffset",
        filter_wheel_label: str = "FilterWheel",
        dia_label: str = "DIA",
    ):
        ...

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
        # 1. Load scope device first (required for all)
        # 2. Load requested sub-devices
        # 3. Call core.initializeAllDevices()
        # 4. Create and return component objects
        ...
```

### Integration with MicroscopeAddons

```python
class MicroscopeAddons:
    @staticmethod
    def build_from_global_config(stage, micro, simulated=False, skip_init=False):
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
            # ... existing params ...
            nikon_pfs=nikon_components.pfs if nikon_components else None,
            nikon_stage=nikon_components.stage if nikon_components else None,
            nikon_filter_wheel=nikon_components.filter_wheel if nikon_components else None,
            nikon_dia=nikon_components.dia if nikon_components else None,
        )
```

### Error Handling

```python
class NikonTi2Exception(RuntimeError):
    """Base exception for all Nikon Ti2 errors."""
    pass

class NikonFilterWheelException(NikonTi2Exception):
    pass

class NikonDIAException(NikonTi2Exception):
    pass
```

- If a requested component fails to load, raise exception with clear message
- If `NIKON_BODY` is set but no components enabled, log warning but don't fail

## Files to Modify

1. **`control/_def.py`** - Add Nikon config variables in new section, remove standalone `USE_NIKON_PFS` at line 754

2. **`control/nikon_ti2.py`** - Add:
   - `NikonTi2Components` dataclass
   - `NikonTi2FilterWheel` and `NikonTi2FilterWheel_Simulation`
   - `NikonTi2DIA` and `NikonTi2DIA_Simulation`
   - `NikonFilterWheelException` and `NikonDIAException`
   - Update `NikonTi2Adapter` and `NikonTi2Adapter_Simulation`

3. **`control/microscope.py:138`** - Update initialization to use `NIKON_BODY` check and new adapter interface

4. **`control/gui_hcs.py`** - Update 3 usages (lines 276, 560, 834):
   ```python
   # Before:
   if USE_NIKON_PFS:

   # After:
   if control._def.NIKON_BODY and control._def.USE_NIKON_PFS:
   ```

5. **`configurations/*.ini`** - Add `[Nikon]` section template to example file

6. **`CLAUDE.md`** - Update Nikon Ti2 documentation section

## Testing

- Simulation classes allow full testing without hardware
- Tests in `tests/control/test_nikon_ti2.py`:
  - Test each component class in isolation (simulation mode)
  - Test adapter initialization with various flag combinations
  - Test that unrequested components return `None`
