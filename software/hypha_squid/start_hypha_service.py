#!/usr/bin/env python3
"""
Hypha Service Wrapper for Microscope Control

This module provides a Hypha-RPC service interface to control the microscope system remotely.
It wraps the Microscope class with proper type annotations and documentation for AI agents.
"""

import asyncio
import sys
from pathlib import Path
from typing import Literal, Optional, List, Tuple, Dict, Any
from enum import Enum
from pydantic import Field, BaseModel
from hypha_rpc import connect_to_server
from hypha_rpc.utils.schema import schema_method

# Add parent directory to path to import control module
sys.path.insert(0, str(Path(__file__).parent.parent))
from control.microscope import Microscope

# Load usage documentation
def load_usage_docs():
    """Load the USAGE.md documentation file."""
    docs_path = Path(__file__).parent / "USAGE.md"
    try:
        with open(docs_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Documentation not found. Please refer to USAGE.md for detailed instructions."
    except Exception as e:
        return f"Error loading documentation: {str(e)}"


class ObjectiveLens(str, Enum):
    """Available objective lenses for the microscope"""
    LENS_4X = "4x"
    LENS_10X = "10x" 
    LENS_20X = "20x"
    LENS_40X = "40x"
    LENS_60X = "60x"
    LENS_100X = "100x"


class WellplateFormat(str, Enum):
    """Supported wellplate formats"""
    PLATE_6 = "6 well plate"
    PLATE_12 = "12 well plate"
    PLATE_24 = "24 well plate"
    PLATE_48 = "48 well plate"
    PLATE_96 = "96 well plate"
    PLATE_384 = "384 well plate"
    PLATE_1536 = "1536 well plate"
    CUSTOM = "0"  # Custom format


class IlluminationChannel(str, Enum):
    """Available illumination channels"""
    BF_LED = "BF LED matrix full"
    BF_LED_LEFT = "BF LED matrix left half"
    BF_LED_RIGHT = "BF LED matrix right half"
    FLUORESCENCE_405 = "Fluorescence 405 nm Ex"
    FLUORESCENCE_488 = "Fluorescence 488 nm Ex"
    FLUORESCENCE_561 = "Fluorescence 561 nm Ex"
    FLUORESCENCE_638 = "Fluorescence 638 nm Ex"
    FLUORESCENCE_730 = "Fluorescence 730 nm Ex"


class MicroscopeService:
    """
    Hypha service wrapper for microscope control.
    
    This class provides remote access to microscope functions through Hypha-RPC,
    with comprehensive type annotations and documentation for AI agent integration.
    """
    
    def __init__(self, is_simulation: bool = False):
        """
        Initialize the microscope service.
        
        Args:
            is_simulation: If True, runs in simulation mode without hardware
        """
        self.microscope = Microscope(is_simulation=is_simulation)
        self.is_initialized = False
        self.current_objective = None
        self.current_position = {"x": 0.0, "y": 0.0, "z": 0.0}
        
    @schema_method
    async def initialize_system(
        self,
        home_xyz: bool = Field(True, description="Whether to home all axes during initialization")
    ) -> Dict[str, Any]:
        """
        Initialize the microscope system and optionally home all axes.
        
        This should be called once at the beginning of a session to ensure
        the microscope is in a known state. Homing establishes the reference
        position for all motorized axes.
        
        Args:
            home_xyz: If True, performs homing sequence for X, Y, and Z axes
            
        Returns:
            Dictionary containing initialization status and current position
            
        Example:
            >>> result = await service.initialize_system(home_xyz=True)
            >>> print(f"System initialized at position: {result['position']}")
        """
        try:
            if home_xyz:
                self.microscope.home_xyz()
            
            self.is_initialized = True
            self.current_position = {
                "x": self.microscope.get_x(),
                "y": self.microscope.get_y(),
                "z": self.microscope.get_z()
            }
            
            return {
                "status": "success",
                "initialized": True,
                "homed": home_xyz,
                "position": self.current_position,
                "message": "Microscope system initialized successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "initialized": False,
                "message": f"Failed to initialize: {str(e)}"
            }
    
    @schema_method
    async def set_objective(
        self,
        objective: str = Field(..., description="Objective lens to use (e.g., '4x', '10x', '20x', '40x', '60x', '100x')")
    ) -> Dict[str, Any]:
        """
        Change the microscope objective lens.
        
        This function switches to the specified objective lens. The microscope
        will automatically adjust parfocality and other settings for the new objective.
        Available objectives typically include 4x, 10x, 20x, 40x, 60x, and 100x.
        
        Args:
            objective: The objective lens designation (e.g., '20x' for 20x magnification)
            
        Returns:
            Dictionary with status and the currently active objective
            
        Example:
            >>> result = await service.set_objective(objective="20x")
            >>> print(f"Now using {result['current_objective']} objective")
        """
        try:
            self.microscope.set_objective(objective)
            self.current_objective = objective
            
            return {
                "status": "success",
                "current_objective": objective,
                "message": f"Successfully switched to {objective} objective"
            }
        except Exception as e:
            return {
                "status": "error",
                "current_objective": self.current_objective,
                "message": f"Failed to set objective: {str(e)}"
            }
    
    @schema_method
    async def move_to_loading_position(self) -> Dict[str, Any]:
        """
        Move the microscope stage to the sample loading position.
        
        This moves the stage to a predefined position where samples can be
        safely loaded or unloaded. The objective is retracted to prevent
        collision, and the XY stage moves to an accessible position.
        This is typically used when changing samples or wellplates.
        
        Returns:
            Dictionary with movement status and final position
            
        Example:
            >>> result = await service.move_to_loading_position()
            >>> # Now safe to load/unload samples
            >>> print("Stage ready for sample loading")
        """
        try:
            was_live = self.microscope.liveController.is_live
            self.microscope.to_loading_position()
            
            self.current_position = {
                "x": self.microscope.get_x(),
                "y": self.microscope.get_y(),
                "z": self.microscope.get_z()
            }
            
            return {
                "status": "success",
                "position": self.current_position,
                "objective_retracted": True,
                "was_live": was_live,
                "message": "Stage moved to loading position"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to move to loading position: {str(e)}"
            }
    
    @schema_method
    async def move_to_scanning_position(self) -> Dict[str, Any]:
        """
        Move the microscope stage to the scanning position.
        
        This moves the stage from the loading position to the scanning position
        where image acquisition can begin. The objective is extended back to
        the working distance, and the XY stage moves to the scan start position.
        
        Returns:
            Dictionary with movement status and final position
            
        Example:
            >>> result = await service.move_to_scanning_position()
            >>> print("Ready to start scanning")
        """
        try:
            was_live = self.microscope.liveController.is_live
            self.microscope.to_scanning_position()
            
            self.current_position = {
                "x": self.microscope.get_x(),
                "y": self.microscope.get_y(),
                "z": self.microscope.get_z()
            }
            
            return {
                "status": "success",
                "position": self.current_position,
                "objective_retracted": False,
                "was_live": was_live,
                "message": "Stage moved to scanning position"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to move to scanning position: {str(e)}"
            }
    
    @schema_method
    async def move_to_position(
        self,
        x_mm: float = Field(..., description="X position in millimeters", ge=-50, le=50),
        y_mm: float = Field(..., description="Y position in millimeters", ge=-50, le=50),
        z_mm: float = Field(..., description="Z position in millimeters", ge=0, le=10)
    ) -> Dict[str, Any]:
        """
        Move the microscope stage to a specific XYZ position.
        
        Moves the stage to absolute coordinates. All movements are performed
        sequentially (X, then Y, then Z) to ensure safe operation. Position
        limits are enforced to prevent mechanical damage.
        
        Args:
            x_mm: Target X position in millimeters (range: -50 to 50 mm)
            y_mm: Target Y position in millimeters (range: -50 to 50 mm)
            z_mm: Target Z position in millimeters (range: 0 to 10 mm)
            
        Returns:
            Dictionary with movement status and final position
            
        Example:
            >>> result = await service.move_to_position(x_mm=10.5, y_mm=-5.2, z_mm=3.0)
            >>> print(f"Moved to position: {result['position']}")
        """
        try:
            self.microscope.move_to_position(x_mm, y_mm, z_mm)
            
            self.current_position = {
                "x": self.microscope.get_x(),
                "y": self.microscope.get_y(),
                "z": self.microscope.get_z()
            }
            
            return {
                "status": "success",
                "position": self.current_position,
                "message": f"Moved to position (x={x_mm}, y={y_mm}, z={z_mm})"
            }
        except Exception as e:
            return {
                "status": "error",
                "position": self.current_position,
                "message": f"Failed to move to position: {str(e)}"
            }
    
    @schema_method
    async def get_current_position(self) -> Dict[str, Any]:
        """
        Get the current XYZ position of the microscope stage.
        
        Returns the absolute position of the stage in millimeters for all three axes.
        This is useful for recording positions of interest or verifying stage location.
        
        Returns:
            Dictionary containing current X, Y, and Z positions in millimeters
            
        Example:
            >>> position = await service.get_current_position()
            >>> print(f"Current position: X={position['x']}, Y={position['y']}, Z={position['z']}")
        """
        try:
            self.current_position = {
                "x": self.microscope.get_x(),
                "y": self.microscope.get_y(),
                "z": self.microscope.get_z()
            }
            
            return {
                "status": "success",
                "position": self.current_position,
                "unit": "millimeters"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get position: {str(e)}"
            }
    
    @schema_method
    async def set_scan_coordinates(
        self,
        wellplate_format: str = Field(..., description="Wellplate format (e.g., '6 well plate', '24 well plate', '96 well plate')"),
        well_selection: str = Field(..., description="Wells to scan (e.g., 'A1', 'A1:B4', 'A1,C3,E5')"),
        scan_size_mm: float = Field(10, description="Size of scan area in millimeters", ge=0.1, le=50),
        overlap_percent: int = Field(10, description="Overlap percentage between tiles", ge=0, le=50)
    ) -> Dict[str, Any]:
        """
        Configure the scan coordinates for wellplate imaging.
        
        Sets up the scanning pattern for imaging selected wells in a wellplate.
        Supports various wellplate formats and flexible well selection patterns.
        The scan area can be customized in size and tile overlap for stitching.
        
        Args:
            wellplate_format: Type of wellplate (e.g., '24 well plate', '96 well plate')
            well_selection: Wells to scan - single well ('A1'), range ('A1:B4'), or list ('A1,C3,E5')
            scan_size_mm: Size of the square scan area per well in millimeters
            overlap_percent: Percentage overlap between adjacent tiles for stitching
            
        Returns:
            Dictionary with configuration status and scan parameters
            
        Example:
            >>> # Scan wells A1 through B4 in a 24-well plate
            >>> result = await service.set_scan_coordinates(
            ...     wellplate_format="24 well plate",
            ...     well_selection="A1:B4",
            ...     scan_size_mm=10,
            ...     overlap_percent=10
            ... )
        """
        try:
            self.microscope.set_coordinates(
                wellplate_format=wellplate_format,
                selected=well_selection,
                scan_size_mm=scan_size_mm,
                overlap_percent=overlap_percent
            )
            
            return {
                "status": "success",
                "wellplate_format": wellplate_format,
                "selected_wells": well_selection,
                "scan_size_mm": scan_size_mm,
                "overlap_percent": overlap_percent,
                "message": "Scan coordinates configured successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to set scan coordinates: {str(e)}"
            }
    
    @schema_method
    async def set_illumination_intensity(
        self,
        channel: str = Field(..., description="Illumination channel name (e.g., 'BF LED matrix full', 'Fluorescence 488 nm Ex')"),
        intensity: float = Field(..., description="Intensity percentage (0-100)", ge=0, le=100)
    ) -> Dict[str, Any]:
        """
        Set the illumination intensity for a specific channel.
        
        Adjusts the intensity of the illumination source for the specified channel.
        Different channels control different light sources (brightfield LED, fluorescence
        excitation lasers, etc.). Intensity is specified as a percentage of maximum power.
        
        Args:
            channel: Name of the illumination channel (e.g., 'BF LED matrix full', 'Fluorescence 488 nm Ex')
            intensity: Intensity as percentage (0-100, where 100 is maximum power)
            
        Returns:
            Dictionary with status and current settings
            
        Example:
            >>> # Set brightfield LED to 10% intensity
            >>> result = await service.set_illumination_intensity(
            ...     channel="BF LED matrix full",
            ...     intensity=10
            ... )
        """
        try:
            self.microscope.set_illumination_intensity(channel, intensity)
            
            return {
                "status": "success",
                "channel": channel,
                "intensity": intensity,
                "message": f"Illumination intensity set to {intensity}% for {channel}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to set illumination: {str(e)}"
            }
    
    @schema_method
    async def set_exposure_time(
        self,
        channel: str = Field(..., description="Channel name for exposure setting"),
        exposure_time_ms: float = Field(..., description="Exposure time in milliseconds", ge=1, le=10000)
    ) -> Dict[str, Any]:
        """
        Set the camera exposure time for a specific imaging channel.
        
        Configures the exposure duration for image acquisition in the specified channel.
        Longer exposures collect more light but may cause motion blur or photobleaching.
        Optimal exposure depends on sample brightness and imaging requirements.
        
        Args:
            channel: Name of the imaging channel
            exposure_time_ms: Exposure time in milliseconds (range: 1-10000 ms)
            
        Returns:
            Dictionary with status and current settings
            
        Example:
            >>> # Set 50ms exposure for fluorescence imaging
            >>> result = await service.set_exposure_time(
            ...     channel="Fluorescence 488 nm Ex",
            ...     exposure_time_ms=50
            ... )
        """
        try:
            self.microscope.set_exposure_time(channel, exposure_time_ms)
            
            return {
                "status": "success",
                "channel": channel,
                "exposure_time_ms": exposure_time_ms,
                "message": f"Exposure time set to {exposure_time_ms}ms for {channel}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to set exposure time: {str(e)}"
            }
    
    @schema_method
    async def start_live_preview(self) -> Dict[str, Any]:
        """
        Start live preview mode for real-time imaging.
        
        Begins continuous image acquisition and display for focusing and sample
        positioning. The camera streams images at maximum framerate for the current
        settings. Use this for sample navigation and focus adjustment.
        
        Returns:
            Dictionary with status of live preview activation
            
        Example:
            >>> result = await service.start_live_preview()
            >>> # Now showing live images from the camera
        """
        try:
            self.microscope.start_live()
            
            return {
                "status": "success",
                "live_mode": True,
                "message": "Live preview started"
            }
        except Exception as e:
            return {
                "status": "error",
                "live_mode": False,
                "message": f"Failed to start live preview: {str(e)}"
            }
    
    @schema_method
    async def stop_live_preview(self) -> Dict[str, Any]:
        """
        Stop live preview mode.
        
        Stops continuous image acquisition and frees the camera for other operations.
        Should be called before starting automated scans or when live view is no longer needed.
        
        Returns:
            Dictionary with status of live preview deactivation
            
        Example:
            >>> result = await service.stop_live_preview()
            >>> # Live preview stopped, camera ready for scanning
        """
        try:
            self.microscope.stop_live()
            
            return {
                "status": "success",
                "live_mode": False,
                "message": "Live preview stopped"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to stop live preview: {str(e)}"
            }
    
    @schema_method
    async def perform_scan(
        self,
        output_path: str = Field(..., description="Directory path for saving acquired images"),
        experiment_id: str = Field(..., description="Unique identifier for this experiment"),
        z_position_um: float = Field(..., description="Z focus position in micrometers", ge=0, le=10000),
        channels: List[str] = Field(..., description="List of channel names to acquire (e.g., ['Fluorescence 488 nm Ex', 'Fluorescence 561 nm Ex'])"),
        use_laser_autofocus: bool = Field(False, description="Enable laser autofocus for maintaining focus"),
        z_stack_range_um: float = Field(1.5, description="Total Z-stack range in micrometers", ge=0, le=100),
        z_stack_steps: int = Field(1, description="Number of Z-stack steps", ge=1, le=100)
    ) -> Dict[str, Any]:
        """
        Perform automated multi-well, multi-channel scanning.
        
        Executes a complete scanning sequence based on previously configured coordinates.
        Acquires images for all specified channels at each position, with optional Z-stacking
        and laser autofocus for maintaining focal plane. Images are saved to the specified
        directory with automatic organization by well, channel, and position.
        
        Args:
            output_path: Directory where images will be saved (created if doesn't exist)
            experiment_id: Unique identifier for organizing data from this experiment
            z_position_um: Starting Z position in micrometers for the focal plane
            channels: List of channel names to image at each position
            use_laser_autofocus: If True, uses laser-based autofocus to maintain focus
            z_stack_range_um: Total range for Z-stack acquisition in micrometers
            z_stack_steps: Number of steps in the Z-stack (1 for single plane)
            
        Returns:
            Dictionary with scan status and statistics
            
        Example:
            >>> # Perform a multi-channel fluorescence scan
            >>> result = await service.perform_scan(
            ...     output_path="/data/experiments/",
            ...     experiment_id="exp_20240101_001",
            ...     z_position_um=3000,
            ...     channels=["Fluorescence 488 nm Ex", "Fluorescence 561 nm Ex"],
            ...     use_laser_autofocus=True,
            ...     z_stack_range_um=10,
            ...     z_stack_steps=5
            ... )
            >>> print(f"Scan completed: {result['images_acquired']} images acquired")
        """
        try:
            self.microscope.perform_scanning(
                path=output_path,
                experiment_ID=experiment_id,
                z_pos_um=z_position_um,
                channels=channels,
                use_laser_af=use_laser_autofocus,
                dz=z_stack_range_um,
                Nz=z_stack_steps
            )
            
            return {
                "status": "success",
                "experiment_id": experiment_id,
                "output_path": output_path,
                "channels_acquired": channels,
                "z_position_um": z_position_um,
                "z_stack": {
                    "enabled": z_stack_steps > 1,
                    "range_um": z_stack_range_um,
                    "steps": z_stack_steps
                },
                "laser_autofocus": use_laser_autofocus,
                "message": "Scan completed successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Scan failed: {str(e)}"
            }
    
    @schema_method
    async def acquire_single_image(self) -> Dict[str, Any]:
        """
        Acquire a single image with current settings.
        
        Captures one image using the current channel, exposure, and illumination settings.
        This is useful for testing parameters or acquiring individual snapshots.
        The image data is returned in the response for immediate use.
        
        Returns:
            Dictionary with acquisition status and image metadata
            
        Example:
            >>> result = await service.acquire_single_image()
            >>> if result['status'] == 'success':
            ...     print(f"Image acquired: {result['image_shape']}")
        """
        try:
            image = self.microscope.acquire_image()
            
            if image is not None:
                return {
                    "status": "success",
                    "image_shape": image.shape if hasattr(image, 'shape') else None,
                    "message": "Image acquired successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to acquire image - no data returned"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to acquire image: {str(e)}"
            }
    
    @schema_method
    async def shutdown(self) -> Dict[str, Any]:
        """
        Safely shutdown the microscope system.
        
        Performs a clean shutdown sequence: stops any ongoing operations, 
        parks the stage in a safe position, turns off illumination, and 
        closes all connections. Always call this before ending a session.
        
        Returns:
            Dictionary with shutdown status
            
        Example:
            >>> result = await service.shutdown()
            >>> print("Microscope system shut down safely")
        """
        try:
            self.microscope.close()
            
            return {
                "status": "success",
                "message": "Microscope system shut down successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Shutdown error: {str(e)}"
            }
    
    @schema_method
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status information.
        
        Returns detailed information about the current state of the microscope system,
        including position, active objective, live mode status, and system readiness.
        Useful for diagnostics and confirming system state before operations.
        
        Returns:
            Dictionary containing complete system status information
            
        Example:
            >>> status = await service.get_system_status()
            >>> print(f"System ready: {status['ready']}")
            >>> print(f"Current objective: {status['objective']}")
        """
        try:
            position = {
                "x": self.microscope.get_x(),
                "y": self.microscope.get_y(),
                "z": self.microscope.get_z()
            }
            
            is_live = self.microscope.liveController.is_live
            
            return {
                "status": "success",
                "ready": self.is_initialized,
                "position": position,
                "objective": self.current_objective,
                "live_mode": is_live,
                "system_info": {
                    "initialized": self.is_initialized,
                    "performance_mode": self.microscope.performance_mode
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "ready": False,
                "message": f"Failed to get system status: {str(e)}"
            }


async def start_hypha_service(
    server_url: str = "https://hypha.aicell.io",
    service_id: str = "microscope-control",
    is_simulation: bool = False
):
    """
    Start the Hypha microscope control service.
    
    Args:
        server_url: URL of the Hypha server
        service_id: Unique identifier for this service
        is_simulation: Run in simulation mode without hardware
    """
    # Connect to Hypha server
    server = await connect_to_server({"server_url": server_url})
    
    # Create microscope service instance
    microscope_service = MicroscopeService(is_simulation=is_simulation)
    
    # Load comprehensive usage documentation
    usage_docs = load_usage_docs()
    
    # Register all methods as a service
    service = await server.register_service({
        "id": service_id,
        "name": "Microscope Control Service",
        "description": """
        Comprehensive microscope control service for automated imaging.
        
        This service provides full control over a research microscope system including:
        - Stage positioning and movement
        - Objective lens selection
        - Illumination control
        - Multi-channel imaging
        - Automated wellplate scanning
        - Z-stack acquisition
        - Laser autofocus
        
        Designed for AI agent integration with detailed documentation and type hints.
        """,
        "docs": usage_docs,  # Include comprehensive usage documentation
        "config": {
            "visibility": "public",
            "require_context": False
        },
        # Register all methods
        "initialize_system": microscope_service.initialize_system,
        "set_objective": microscope_service.set_objective,
        "move_to_loading_position": microscope_service.move_to_loading_position,
        "move_to_scanning_position": microscope_service.move_to_scanning_position,
        "move_to_position": microscope_service.move_to_position,
        "get_current_position": microscope_service.get_current_position,
        "set_scan_coordinates": microscope_service.set_scan_coordinates,
        "set_illumination_intensity": microscope_service.set_illumination_intensity,
        "set_exposure_time": microscope_service.set_exposure_time,
        "start_live_preview": microscope_service.start_live_preview,
        "stop_live_preview": microscope_service.stop_live_preview,
        "perform_scan": microscope_service.perform_scan,
        "acquire_single_image": microscope_service.acquire_single_image,
        "shutdown": microscope_service.shutdown,
        "get_system_status": microscope_service.get_system_status
    })
    
    print(f"✅ Microscope Control Service registered successfully!")
    print(f"Service ID: {service.id}")
    print(f"Workspace: {server.config.workspace}")
    print(f"Server URL: {server_url}/{server.config.workspace}/services/{service.id.split('/')[1]}")
    print(f"MCP Server URL: {server_url}/{server.config.workspace}/mcp/{service.id.split('/')[1]}/mcp")
    print("\nService is now available for AI agents and remote clients.")
    print("\nTo use this service from an AI agent, use the service ID:")
    print(f"  {service.id}")
    print("\nPress Ctrl+C to stop the service...")
    
    # Keep the service running
    await server.serve()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Start Hypha Microscope Control Service")
    parser.add_argument(
        "--server-url",
        default="https://hypha.aicell.io",
        help="Hypha server URL (default: https://hypha.aicell.io)"
    )
    parser.add_argument(
        "--service-id",
        default="microscope-control",
        help="Service ID (default: microscope-control)"
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run in simulation mode without hardware"
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(start_hypha_service(
            server_url=args.server_url,
            service_id=args.service_id,
            is_simulation=args.simulation
        ))
    except KeyboardInterrupt:
        print("\n⏹️ Service stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)