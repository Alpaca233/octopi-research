# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Squid is a Python-based microscope control software for high-content screening. It provides a PyQt5 GUI for instrument control, multi-camera support, automated well plate scanning, and programmatic control via MCP (Model Context Protocol).

## Common Commands

### Running the Application
```bash
python3 main_hcs.py                    # Normal operation
python3 main_hcs.py --simulation       # Simulated hardware mode
python3 main_hcs.py --start-server     # Auto-start MCP control server
python3 main_hcs.py --verbose          # Enable DEBUG logging
python3 main_hcs.py --skip-init        # Skip hardware init/homing
```

### Running Tests
```bash
pytest tests/                          # Run all tests
pytest tests/control/                  # Control module tests only
pytest tests/control/test_microscope.py  # Single test file
pytest tests/control/test_microscope.py::test_name -v  # Single test
pytest -x tests/                       # Stop on first failure
```

### Code Formatting
```bash
black --line-length 120 control/       # Format control module
```
The project uses Black with 120 character line length. Excludes: `drivers and libraries/`, `gxipy/`, `ndviewer_light/`, `fluidics_v2/`, and vendor API files.

## Architecture

### Entry Points
- **`main_hcs.py`** - Primary GUI application entry point
- **`mcp_microscope_server.py`** - MCP server for Claude Code integration (stdio-based, connects to TCP control server on port 5050)

### Core Module Structure

**`control/`** - Main application logic:
- `gui_hcs.py` - Main GUI class (`HighContentScreeningGui`)
- `microscope.py` - Factory pattern: `Microscope.build_from_global_config()` creates fully configured microscope instance
- `microcontroller.py` - Serial protocol with firmware, background thread for packet reading
- `_def.py` - Global constants, feature flags, hardware settings loaded from `.ini` files
- `core/` - Image processing pipeline:
  - `job_processing.py` - Multiprocessing job queue for disk I/O
  - `zarr_writer.py` - OME-NGFF/Zarr v3 output
  - `backpressure.py` - Queue throttling to prevent RAM exhaustion
  - `multi_point_worker.py` - High-speed acquisition worker
- `models/` - Pydantic configuration schemas (channel, camera, illumination, filter wheel)

**`squid/`** - Hardware abstractions:
- `abc.py` - Abstract base classes: `AbstractCamera`, `AbstractStage`, `AbstractFilterWheelController`, `LightSource`
- `camera/`, `stage/`, `filter_wheel_controller/` - Driver implementations
- `config.py` - Configuration loading and validation
- `logging.py` - Fork-safe logging with thread ID injection

### Configuration System

**Machine configs** (`machine_configs/`) - Hardware definitions (rarely change):
- `illumination_channel_config.yaml` - Light sources, controller port mappings
- `cameras.yaml` - Multi-camera registry (optional for single camera)
- `filter_wheels.yaml` - Filter wheel definitions
- `hardware_bindings.yaml` - Camera-to-filter-wheel mappings
- `confocal_config.yaml` - Confocal unit settings (presence enables confocal features)

**User profiles** (`user_profiles/{profile}/`) - User preferences:
- `channel_configs/general.yaml` - Channel identity and shared settings
- `channel_configs/{objective}.yaml` - Per-objective overrides (intensity, exposure, gain)
- `laser_af_configs/{objective}.yaml` - Laser autofocus calibration per objective

**Merge logic**: `general.yaml` defines channel identity; objective files override intensity, exposure, gain, and confocal settings.

**Machine initialization** (`configurations/`) - `.ini` files for microscope variants (copied to software folder to activate).

### Simulation Support

Global `--simulation` flag simulates all hardware. Per-component overrides in `_def.py` (e.g., `SIMULATE_CAMERA`, `SIMULATE_STAGE`) allow selective simulation when not using `--simulation`.

### MCP Integration

The MCP server enables Claude Code to control the microscope programmatically:
1. GUI starts `MicroscopeControlServer` on TCP port 5050
2. `mcp_microscope_server.py` (stdio) bridges MCP protocol to TCP
3. Commands prefixed with `microscope_` (e.g., `microscope_move_to`, `microscope_acquire_image`)

Launch via GUI: **Settings → Launch Claude Code** (auto-starts server and configures connection).

### Camera Drivers

Each camera SDK has a dedicated module in `control/`:
- `camera_flir.py` (Teledyne Spinnaker)
- `camera_hamamatsu.py` (DCAM API)
- `camera_tucsen.py`, `camera_toupcam.py`, `camera_ids.py`, `camera_photometrics.py`, `camera_andor.py`

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

### Test Fixtures

Key fixtures in `tests/control/conftest.py`:
- `cleanup_microcontrollers` (autouse) - Auto-cleanup of MCU instances and background threads
- `firmware_sim` - Strict firmware simulator for unit tests
- `firmware_sim_nonstrict` - Non-strict mode for negative testing

## Key Patterns

### Component Factory
```python
microscope = control.microscope.Microscope.build_from_global_config(
    simulated=args.simulation,
    skip_init=args.skip_init
)
```

### Configuration Loading
Pydantic models in `control/models/` validate all YAML configs. Invalid configs fail fast with clear errors.

### Hardware Abstraction
All hardware uses abstract base classes from `squid/abc.py`. Simulated implementations follow the same interface.

### Backpressure System
`control/core/backpressure.py` throttles acquisition when disk I/O or processing can't keep up, preventing RAM exhaustion.

## Important Files

- `control/_def.py` - Feature flags, hardware constants, loaded from `.ini` config
- `control/gui_hcs.py` - Main GUI (17k+ lines)
- `control/microscope.py` - Microscope factory and composition
- `control/microcontroller.py` - Firmware protocol implementation
- `control/nikon_ti2.py` - Nikon Ti2 stage and PFS control via pymmcore-plus
- `docs/configuration-system.md` - Full YAML config documentation
- `docs/mcp_integration.md` - Claude Code integration guide
