# Microscope Control System - Complete Usage Guide

## System Overview

This is an advanced research-grade automated microscope system designed for high-throughput imaging of biological samples. The system combines precision motorized stages, multiple illumination sources, automated objective switching, and sophisticated image acquisition capabilities to enable complex imaging workflows.

### Key Capabilities

- **Automated Multi-Well Plate Scanning**: Image entire wellplates with programmable patterns
- **Multi-Channel Fluorescence Imaging**: Acquire images with multiple excitation wavelengths
- **Z-Stack Acquisition**: Capture 3D volumes through optical sectioning
- **Laser Autofocus**: Maintain precise focal plane during long acquisitions
- **Live Preview Mode**: Real-time imaging for sample navigation and focusing
- **High-Precision Positioning**: Sub-micrometer stage positioning accuracy

## Hardware Components

### Stage System
- **XY Stage**: Motorized positioning with ±50mm travel range, resolution <1μm
- **Z Stage**: Focus control with 10mm travel range, resolution <0.1μm
- **Piezo Z**: Optional fine focus control for rapid Z-stack acquisition

### Optical System
- **Objectives**: 4x, 10x, 20x, 40x, 60x, 100x magnification options
- **Automatic Objective Changer**: Motorized switching between objectives
- **Parfocal Correction**: Automatic focus adjustment when changing objectives

### Illumination Sources
- **Brightfield LED Matrix**: Uniform white light illumination for transmitted light
- **Fluorescence Excitation**: 
  - 405nm (DAPI, Hoechst)
  - 488nm (GFP, FITC, Alexa 488)
  - 561nm (RFP, mCherry, Cy3)
  - 638nm (Cy5, Alexa 647)
  - 730nm (Near-IR dyes)

### Camera System
- High-sensitivity scientific camera
- Configurable exposure times (1-10000ms)
- Hardware triggering for synchronized acquisition
- Support for various pixel formats

## API Usage Guide

### 1. System Initialization

**Always start by initializing the system:**

```python
# Initialize and home all axes
result = await microscope.initialize_system(home_xyz=True)
```

**Purpose**: Establishes reference positions for all motorized components
**When to use**: At the beginning of every session
**Parameters**:
- `home_xyz`: Set to `True` to perform homing (recommended for first use)

### 2. Objective Selection

**Set the magnification:**

```python
# Select 20x objective for overview imaging
result = await microscope.set_objective(objective="20x")
```

**Purpose**: Changes the objective lens and adjusts system parameters accordingly
**When to use**: Before imaging when specific magnification is needed
**Available options**: "4x", "10x", "20x", "40x", "60x", "100x"
**Tips**: 
- Lower magnification (4x-10x) for sample navigation
- Medium magnification (20x-40x) for most imaging
- High magnification (60x-100x) for subcellular details

### 3. Sample Loading Workflow

**Move to loading position:**

```python
# Safely position stage for sample loading
result = await microscope.move_to_loading_position()
```

**Purpose**: Retracts objective and positions stage for safe sample access
**When to use**: Before loading or removing samples
**What happens**:
- Z-axis retracts to prevent collision
- XY stage moves to accessible position
- Live preview stops if active

**After loading sample, move to scanning position:**

```python
# Position for imaging
result = await microscope.move_to_scanning_position()
```

**Purpose**: Returns stage to imaging position
**What happens**:
- Z-axis returns to previous focus position
- XY stage moves to scan start position

### 4. Stage Positioning

**Move to specific coordinates:**

```python
# Move to center of wellplate
result = await microscope.move_to_position(
    x_mm=0.0,    # X position in millimeters
    y_mm=0.0,    # Y position in millimeters  
    z_mm=3.0     # Z focus position in millimeters
)
```

**Purpose**: Precise positioning for specific regions of interest
**Coordinate system**:
- Origin (0,0,0) is at stage center and nominal focus
- X range: -50 to +50 mm
- Y range: -50 to +50 mm
- Z range: 0 to 10 mm

**Get current position:**

```python
position = await microscope.get_current_position()
print(f"Current: X={position['position']['x']}, Y={position['position']['y']}, Z={position['position']['z']}")
```

### 5. Illumination Control

**Set light intensity:**

```python
# Set brightfield LED to 10% for gentle illumination
result = await microscope.set_illumination_intensity(
    channel="BF LED matrix full",
    intensity=10  # Percentage (0-100)
)

# Set fluorescence excitation laser
result = await microscope.set_illumination_intensity(
    channel="Fluorescence 488 nm Ex",
    intensity=5  # Keep low to prevent photobleaching
)
```

**Purpose**: Controls illumination power for each channel
**Guidelines**:
- Brightfield: 5-20% for most samples
- Fluorescence: 1-10% to minimize photobleaching
- Start low and increase as needed

### 6. Exposure Time Configuration

**Set camera exposure:**

```python
# Fast exposure for brightfield
result = await microscope.set_exposure_time(
    channel="BF LED matrix full",
    exposure_time_ms=10  # 10 milliseconds
)

# Longer exposure for weak fluorescence
result = await microscope.set_exposure_time(
    channel="Fluorescence 561 nm Ex",
    exposure_time_ms=100  # 100 milliseconds
)
```

**Purpose**: Controls how long camera sensor collects light
**Guidelines**:
- Brightfield: 5-50ms typical
- Fluorescence: 50-500ms depending on signal
- Longer exposure = more signal but risk of motion blur

### 7. Live Preview Mode

**Start real-time imaging:**

```python
# Enable live view for focusing
result = await microscope.start_live_preview()

# ... adjust focus and position ...

# Stop when done
result = await microscope.stop_live_preview()
```

**Purpose**: Continuous imaging for sample navigation and focusing
**When to use**:
- Finding regions of interest
- Manual focus adjustment
- Checking sample quality
**Note**: Must stop before automated scanning

### 8. Wellplate Scanning Setup

**Configure scan pattern:**

```python
# Scan wells A1 through B4 in a 24-well plate
result = await microscope.set_scan_coordinates(
    wellplate_format="24 well plate",
    well_selection="A1:B4",  # Range notation
    scan_size_mm=10,          # Area to image per well
    overlap_percent=10        # Tile overlap for stitching
)

# Or scan specific wells
result = await microscope.set_scan_coordinates(
    wellplate_format="96 well plate",
    well_selection="A1,C3,E5,G7",  # Comma-separated list
    scan_size_mm=5,
    overlap_percent=15
)
```

**Purpose**: Defines which wells to image and how
**Wellplate formats**: "6 well plate", "12 well plate", "24 well plate", "48 well plate", "96 well plate", "384 well plate", "1536 well plate"
**Well selection syntax**:
- Single well: "A1"
- Range: "A1:C4" (rectangle from A1 to C4)
- List: "A1,B3,D5" (specific wells)
**Scan parameters**:
- `scan_size_mm`: Size of square region to image per well
- `overlap_percent`: Tile overlap (10-20% typical for stitching)

### 9. Automated Multi-Channel Scanning

**Execute complete scan:**

```python
# Multi-channel fluorescence with Z-stack
result = await microscope.perform_scan(
    output_path="/data/experiment_001/",
    experiment_id="drug_treatment_24h",
    z_position_um=3000,  # Starting focus at 3mm
    channels=[
        "Fluorescence 405 nm Ex",  # Nuclei (DAPI)
        "Fluorescence 488 nm Ex",  # GFP
        "Fluorescence 561 nm Ex",  # mCherry
    ],
    use_laser_autofocus=True,  # Maintain focus
    z_stack_range_um=20,        # 20 micron Z range
    z_stack_steps=11            # 11 planes (2μm spacing)
)
```

**Purpose**: Automated acquisition of all configured wells
**Process**:
1. Visits each configured well
2. Acquires all specified channels
3. Performs Z-stack if configured
4. Saves images with metadata
5. Maintains focus with laser AF if enabled

**Parameters explained**:
- `output_path`: Directory for saving images (created if needed)
- `experiment_id`: Unique identifier for this acquisition
- `z_position_um`: Focus position in micrometers
- `channels`: List of illumination channels to acquire
- `use_laser_autofocus`: Enable drift correction
- `z_stack_range_um`: Total Z range to cover
- `z_stack_steps`: Number of Z planes (1 = single plane)

### 10. Single Image Acquisition

**Capture one frame:**

```python
# Take single snapshot with current settings
result = await microscope.acquire_single_image()
```

**Purpose**: Quick image capture for testing or documentation
**Uses**: Current channel, exposure, and illumination settings
**When to use**: Parameter optimization, single position imaging

### 11. System Status

**Check system state:**

```python
status = await microscope.get_system_status()
print(f"System ready: {status['ready']}")
print(f"Position: {status['position']}")
print(f"Objective: {status['objective']}")
print(f"Live mode: {status['live_mode']}")
```

**Purpose**: Verify system configuration and readiness
**Information provided**:
- Initialization status
- Current XYZ position
- Active objective
- Live preview state
- Performance mode

### 12. Shutdown

**Safely close system:**

```python
result = await microscope.shutdown()
```

**Purpose**: Clean shutdown of all hardware
**What happens**:
- Stops any active operations
- Parks stage in safe position
- Turns off illumination
- Closes camera and stage connections
**Important**: Always call before ending session

## Complete Workflow Examples

### Example 1: Simple Brightfield Scan

```python
# Initialize
await microscope.initialize_system(home_xyz=True)
await microscope.set_objective(objective="10x")

# Configure illumination
await microscope.set_illumination_intensity(channel="BF LED matrix full", intensity=15)
await microscope.set_exposure_time(channel="BF LED matrix full", exposure_time_ms=20)

# Load sample
await microscope.move_to_loading_position()
# ... physically load 24-well plate ...
await microscope.move_to_scanning_position()

# Configure scan
await microscope.set_scan_coordinates(
    wellplate_format="24 well plate",
    well_selection="A1:D6",
    scan_size_mm=8,
    overlap_percent=10
)

# Run scan
await microscope.perform_scan(
    output_path="/data/brightfield_scan/",
    experiment_id="cell_culture_day3",
    z_position_um=3000,
    channels=["BF LED matrix full"],
    use_laser_autofocus=False
)

# Cleanup
await microscope.shutdown()
```

### Example 2: Multi-Channel Fluorescence with Z-Stack

```python
# Initialize with 40x for high resolution
await microscope.initialize_system(home_xyz=True)
await microscope.set_objective(objective="40x")

# Configure each fluorescence channel
channels_config = [
    ("Fluorescence 405 nm Ex", 3, 50),   # DAPI - low power, short exposure
    ("Fluorescence 488 nm Ex", 5, 100),   # GFP - medium power
    ("Fluorescence 561 nm Ex", 8, 150),   # mCherry - higher power
]

for channel, intensity, exposure in channels_config:
    await microscope.set_illumination_intensity(channel=channel, intensity=intensity)
    await microscope.set_exposure_time(channel=channel, exposure_time_ms=exposure)

# Load sample
await microscope.move_to_loading_position()
# ... load sample ...
await microscope.move_to_scanning_position()

# Use live preview to find focus
await microscope.start_live_preview()
# ... adjust Z position ...
current_pos = await microscope.get_current_position()
z_focus_um = current_pos['position']['z'] * 1000  # Convert mm to μm
await microscope.stop_live_preview()

# Configure for selected wells only
await microscope.set_scan_coordinates(
    wellplate_format="96 well plate",
    well_selection="B2,B4,B6,D2,D4,D6",  # Treated wells
    scan_size_mm=3,  # Smaller area for 96-well
    overlap_percent=15
)

# Acquire with Z-stack
await microscope.perform_scan(
    output_path="/data/immunofluorescence/",
    experiment_id="antibody_staining_001",
    z_position_um=z_focus_um,
    channels=["Fluorescence 405 nm Ex", "Fluorescence 488 nm Ex", "Fluorescence 561 nm Ex"],
    use_laser_autofocus=True,
    z_stack_range_um=30,  # 30μm total range
    z_stack_steps=16      # 2μm spacing
)

await microscope.shutdown()
```

### Example 3: Time-Lapse Acquisition

```python
import asyncio
from datetime import datetime

# Initialize for long-term imaging
await microscope.initialize_system(home_xyz=True)
await microscope.set_objective(objective="20x")

# Gentle illumination to prevent phototoxicity
await microscope.set_illumination_intensity(channel="Fluorescence 488 nm Ex", intensity=2)
await microscope.set_exposure_time(channel="Fluorescence 488 nm Ex", exposure_time_ms=50)

# Configure positions
await microscope.set_scan_coordinates(
    wellplate_format="24 well plate",
    well_selection="B2:C3",
    scan_size_mm=5,
    overlap_percent=10
)

# Time-lapse loop
for timepoint in range(48):  # 48 timepoints
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    await microscope.perform_scan(
        output_path="/data/timelapse/",
        experiment_id=f"growth_curve_t{timepoint:03d}_{timestamp}",
        z_position_um=3000,
        channels=["Fluorescence 488 nm Ex"],
        use_laser_autofocus=True  # Critical for long time-lapse
    )
    
    # Wait 30 minutes
    await asyncio.sleep(30 * 60)

await microscope.shutdown()
```

## Best Practices

### Sample Protection
- Start with lowest possible illumination intensity
- Use shorter exposure times when possible
- Enable laser autofocus for long acquisitions
- Consider photobleaching effects in multi-channel imaging

### Optimal Image Quality
- Ensure proper Köhler illumination alignment
- Clean objectives before high-resolution imaging
- Allow temperature stabilization (30 min) for precision work
- Use appropriate immersion media for high-NA objectives

### Data Management
- Use descriptive experiment IDs
- Organize output paths by date/project
- Document imaging parameters in lab notebook
- Verify storage space before large acquisitions

### Troubleshooting Guide

**Problem: Images out of focus**
- Solution: Use laser autofocus or manual refocus between wells

**Problem: Uneven illumination**
- Solution: Check LED matrix alignment, clean optical path

**Problem: Stage position errors**
- Solution: Re-home system, check for mechanical obstructions

**Problem: Weak fluorescence signal**
- Solution: Increase exposure time before increasing laser power

**Problem: System not responding**
- Solution: Call shutdown(), restart service, re-initialize

## Safety Considerations

1. **Laser Safety**: Fluorescence excitation uses laser sources - never look directly into objectives during operation
2. **Mechanical Safety**: Always move to loading position before manipulating samples
3. **Sample Safety**: Use minimum required illumination to prevent damage
4. **Data Safety**: Regularly backup acquired images

## Performance Specifications

- **Positioning Accuracy**: <1μm in XY, <0.1μm in Z
- **Positioning Repeatability**: ±0.5μm
- **Maximum Scan Speed**: 100 positions/hour (depending on settings)
- **Field of View**: Varies by objective (4x: 3.2mm, 20x: 0.64mm, 100x: 0.128mm)
- **Image Resolution**: Up to 2048x2048 pixels
- **Z-Stack Speed**: 10 planes/second with piezo
- **Autofocus Accuracy**: ±0.5μm
- **Temperature Stability**: Required for <1μm drift/hour

## Contact and Support

For technical issues or questions about specific imaging applications, consult the system manual or contact your facility manager. This API provides programmatic access to all standard microscope functions - advanced features may require direct hardware access.