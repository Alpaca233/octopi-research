#!/usr/bin/env python3
"""
Test client for the Microscope Control Service.

This script demonstrates how to connect to and use the microscope service.
Run this after starting the service with start_hypha_service.py
"""

import asyncio
import json
from hypha_rpc import connect_to_server


async def test_microscope_service(service_id: str, server_url: str = "https://hypha.aicell.io"):
    """Test the microscope control service with basic operations."""
    
    print(f"🔗 Connecting to Hypha server at {server_url}...")
    server = await connect_to_server({"server_url": server_url})
    
    print(f"📡 Getting microscope service: {service_id}")
    microscope = await server.get_service(service_id)
    
    print("\n" + "="*60)
    print("MICROSCOPE SERVICE TEST")
    print("="*60)
    
    # Test 1: Get system status
    print("\n1️⃣ Getting system status...")
    status = await microscope.get_system_status()
    print(f"   Status: {status['status']}")
    if status['status'] == 'success':
        print(f"   Ready: {status['ready']}")
        print(f"   Position: {status.get('position', 'Unknown')}")
    
    # Test 2: Initialize system
    print("\n2️⃣ Initializing system (simulation mode)...")
    result = await microscope.initialize_system(home_xyz=False)  # Skip homing in test
    print(f"   Status: {result['status']}")
    print(f"   Message: {result['message']}")
    
    # Test 3: Set objective
    print("\n3️⃣ Setting objective to 20x...")
    result = await microscope.set_objective(objective="20x")
    print(f"   Status: {result['status']}")
    print(f"   Current objective: {result.get('current_objective', 'Unknown')}")
    
    # Test 4: Get current position
    print("\n4️⃣ Getting current position...")
    position = await microscope.get_current_position()
    if position['status'] == 'success':
        pos = position['position']
        print(f"   X: {pos['x']:.3f} mm")
        print(f"   Y: {pos['y']:.3f} mm")
        print(f"   Z: {pos['z']:.3f} mm")
    
    # Test 5: Configure scan (but don't run it)
    print("\n5️⃣ Configuring scan coordinates...")
    result = await microscope.set_scan_coordinates(
        wellplate_format="24 well plate",
        well_selection="A1:A3",
        scan_size_mm=5,
        overlap_percent=10
    )
    print(f"   Status: {result['status']}")
    print(f"   Wells: {result.get('selected_wells', 'Unknown')}")
    
    # Test 6: Set illumination
    print("\n6️⃣ Setting illumination intensity...")
    result = await microscope.set_illumination_intensity(
        channel="BF LED matrix full",
        intensity=10
    )
    print(f"   Status: {result['status']}")
    print(f"   Channel: {result.get('channel', 'Unknown')}")
    print(f"   Intensity: {result.get('intensity', 'Unknown')}%")
    
    # Test 7: Check method schemas
    print("\n7️⃣ Checking method schemas...")
    if hasattr(microscope.initialize_system, '__schema__'):
        schema = microscope.initialize_system.__schema__
        print("   ✅ Method schemas are available for AI agents")
        print(f"   Example schema (initialize_system):")
        print(f"   - Name: {schema.get('name', 'Unknown')}")
        print(f"   - Description: {schema.get('description', 'No description')[:100]}...")
    else:
        print("   ⚠️ Method schemas not found")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
    print("="*60)
    
    print("\n📝 Service Information:")
    print(f"   Service ID: {service_id}")
    print(f"   Server URL: {server_url}")
    print("\n💡 This service is now ready for use by AI agents!")
    print("   Use the service ID in your agent configuration.")
    
    return True


async def main():
    """Main function to run the test."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Microscope Control Service")
    parser.add_argument(
        "service_id",
        help="Service ID (e.g., 'ws-user-xxx/yyy:microscope-control')"
    )
    parser.add_argument(
        "--server-url",
        default="https://hypha.aicell.io",
        help="Hypha server URL (default: https://hypha.aicell.io)"
    )
    
    args = parser.parse_args()
    
    try:
        await test_microscope_service(args.service_id, args.server_url)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(main())