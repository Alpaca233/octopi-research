# Microscope Control Hypha Service

This directory contains a Hypha-RPC service wrapper for remote microscope control, designed for integration with AI agents and distributed computing workflows.

## Overview

The Microscope Control Service exposes the microscope hardware functionality through Hypha-RPC, enabling:
- Remote control from anywhere via the internet
- Integration with AI agents (GPT-4, Claude, etc.)
- Distributed workflows and automation
- Multi-user collaboration

## Files

- `start_hypha_service.py` - Main service implementation with schema annotations
- `test_client.py` - Test client to verify service functionality  
- `agent_config_example.py` - Example AI agent configuration
- `README_SERVICE.md` - This documentation

## Installation

```bash
# Install required dependencies
pip install hypha-rpc pydantic
```

## Quick Start

### 1. Start the Service

```bash
# Run with real hardware
python start_hypha_service.py

# Run in simulation mode (no hardware required)
python start_hypha_service.py --simulation

# Connect to a custom server
python start_hypha_service.py --server-url https://your-hypha-server.com
```

When the service starts, you'll see output like:
```
✅ Microscope Control Service registered successfully!
Service ID: ws-user-capable-raccoon-57051682/ABC123:microscope-control
Workspace: ws-user-capable-raccoon-57051682
```

**Important:** Copy the Service ID - you'll need it to connect clients.

### 2. Test the Service

```bash
# Replace with your actual service ID
python test_client.py "ws-user-capable-raccoon-57051682/ABC123:microscope-control"
```

### 3. Use with AI Agents

In Hypha Agent Lab (https://agents.aicell.io/#/lab):

1. Create a new chat session
2. Add a system configuration cell with the code from `agent_config_example.py`
3. Replace `YOUR_WORKSPACE/YOUR_SERVICE_ID:microscope-control` with your actual service ID
4. Set the cell to "System" role and hide it
5. Start chatting with your microscope control agent!

Example prompts for the agent:
- "Initialize the microscope and home all axes"
- "Set up a scan for wells A1 through B4 in a 24-well plate"
- "Configure fluorescence imaging with 488nm and 561nm channels"
- "Move to position X=10mm, Y=5mm, Z=3mm"

## Available Methods

### System Control
- `initialize_system(home_xyz)` - Initialize and optionally home the microscope
- `get_system_status()` - Get current system state
- `shutdown()` - Safely shutdown the system

### Stage Movement
- `move_to_position(x_mm, y_mm, z_mm)` - Move to absolute coordinates
- `move_to_loading_position()` - Move to sample loading position
- `move_to_scanning_position()` - Move to scanning position
- `get_current_position()` - Get current XYZ position

### Optical Configuration
- `set_objective(objective)` - Change objective lens (4x, 10x, 20x, 40x, 60x, 100x)
- `set_illumination_intensity(channel, intensity)` - Set light source intensity
- `set_exposure_time(channel, exposure_time_ms)` - Set camera exposure

### Image Acquisition
- `acquire_single_image()` - Capture a single image
- `start_live_preview()` - Start live camera view
- `stop_live_preview()` - Stop live view

### Automated Scanning
- `set_scan_coordinates(wellplate_format, well_selection, scan_size_mm, overlap_percent)` - Configure scan area
- `perform_scan(output_path, experiment_id, z_position_um, channels, ...)` - Execute automated scan

## Service Architecture

```
┌─────────────────────────┐
│   AI Agent / Client     │
└───────────┬─────────────┘
            │ Hypha-RPC
            ▼
┌─────────────────────────┐
│   Hypha Server          │
│  (hypha.aicell.io)      │
└───────────┬─────────────┘
            │ WebSocket
            ▼
┌─────────────────────────┐
│  Microscope Service     │
│  (start_hypha_service)  │
└───────────┬─────────────┘
            │ Local Control
            ▼
┌─────────────────────────┐
│  Microscope Hardware    │
│  (control.microscope)   │
└─────────────────────────┘
```

## Method Documentation

All methods include:
- Comprehensive docstrings explaining functionality
- Type annotations with Pydantic Field descriptions
- Value ranges and constraints
- Usage examples
- Return value documentation

This enables AI agents to understand:
- What each method does
- Required and optional parameters
- Valid parameter ranges
- Expected return values
- Error conditions

## Example Workflows

### Basic Imaging Workflow

```python
# Initialize system
await microscope.initialize_system(home_xyz=True)

# Configure optics
await microscope.set_objective(objective="20x")
await microscope.set_illumination_intensity(channel="BF LED matrix full", intensity=10)

# Move to loading position and load sample
await microscope.move_to_loading_position()
# ... load sample ...

# Move to scanning position
await microscope.move_to_scanning_position()

# Configure and run scan
await microscope.set_scan_coordinates(
    wellplate_format="24 well plate",
    well_selection="A1:B4",
    scan_size_mm=10,
    overlap_percent=10
)

await microscope.perform_scan(
    output_path="/data/",
    experiment_id="exp001",
    z_position_um=3000,
    channels=["Fluorescence 488 nm Ex", "Fluorescence 561 nm Ex"]
)

# Shutdown
await microscope.shutdown()
```

### Multi-Channel Fluorescence with Z-Stack

```python
# Configure multi-channel acquisition with Z-stack
await microscope.perform_scan(
    output_path="/data/fluorescence/",
    experiment_id="3d_fluorescence",
    z_position_um=3000,
    channels=[
        "Fluorescence 405 nm Ex",  # DAPI
        "Fluorescence 488 nm Ex",  # GFP
        "Fluorescence 561 nm Ex",  # RFP
        "Fluorescence 638 nm Ex"   # Cy5
    ],
    use_laser_autofocus=True,
    z_stack_range_um=20,  # 20 micron range
    z_stack_steps=11      # 11 planes, 2 micron spacing
)
```

## Security and Access Control

- Services can be public or private (configured via `visibility` parameter)
- Authentication via Hypha tokens for private services
- Workspace isolation for multi-user environments
- Service IDs include workspace prefix for access control

## Troubleshooting

### Service won't start
- Check Python version (3.8+ required)
- Verify hypha-rpc is installed: `pip install hypha-rpc`
- Check network connectivity to Hypha server
- Try simulation mode: `--simulation`

### Can't connect from client
- Verify service ID is correct (copy from service startup output)
- Check service is still running
- Ensure client has network access to Hypha server
- Try the test client first before AI agents

### Hardware errors (non-simulation)
- Ensure microscope hardware is powered on
- Check serial/USB connections
- Verify hardware initialization sequence
- Review control module configuration

## Advanced Configuration

### Custom Server Deployment

Deploy your own Hypha server:
```bash
python -m hypha.server --host=0.0.0.0 --port=9527
```

Then connect the service:
```bash
python start_hypha_service.py --server-url http://your-server:9527
```

### Multiple Service Instances

Run multiple microscopes as separate services:
```bash
# Microscope 1
python start_hypha_service.py --service-id "microscope-1"

# Microscope 2  
python start_hypha_service.py --service-id "microscope-2"
```

## Contributing

To extend the service:

1. Add new methods to `MicroscopeService` class
2. Use `@schema_method` decorator for all public methods
3. Include comprehensive docstrings and type hints
4. Add Field descriptions for all parameters
5. Update the service registration in `start_hypha_service()`
6. Test with the test client
7. Update agent configuration examples

## License

This service wrapper is part of the microscope control software suite.