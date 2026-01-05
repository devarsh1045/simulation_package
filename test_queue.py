#!/usr/bin/env python3
"""
Test script to verify queue length tracking functionality
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_api():
    """Test the API endpoints"""
    
    print("Testing SUMO Web App Queue Functionality")
    print("=" * 50)
    
    # Test status endpoint
    print("\n1. Testing /status endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code == 200:
            data = response.json()
            print("✓ Status endpoint working")
            print(f"  - Simulation running: {data.get('running', False)}")
            print(f"  - Current flow rates: {data.get('flow_rates', {})}")
            
            # Check for queue data structure
            sim_data = data.get('data', {})
            if 'queue_lengths' in sim_data:
                print("✓ Queue length tracking structure present")
            else:
                print("✗ Queue length tracking not found in data")
                
            if 'occupancy' in sim_data:
                print("✓ Occupancy tracking structure present")
            else:
                print("✗ Occupancy tracking not found in data")
        else:
            print(f"✗ Status endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error accessing status: {e}")
    
    # Test flow update
    print("\n2. Testing /update_flow endpoint...")
    try:
        test_flow = {"booth": "booth_0", "rate": 1500}
        response = requests.post(f"{BASE_URL}/update_flow", 
                                json=test_flow,
                                headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            print("✓ Flow update endpoint working")
            data = response.json()
            if data['flow_rates']['booth_0'] == 1500:
                print("✓ Flow rate updated correctly")
            else:
                print("✗ Flow rate not updated as expected")
        elif response.status_code == 400:
            data = response.json()
            print(f"  Note: {data.get('message', 'Flow update blocked')}")
        else:
            print(f"✗ Flow update failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error updating flow: {e}")
    
    # Reset flows
    print("\n3. Testing /reset_flows endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/reset_flows")
        if response.status_code == 200:
            print("✓ Reset flows endpoint working")
        else:
            print(f"✗ Reset flows failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error resetting flows: {e}")
    
    print("\n" + "=" * 50)
    print("Queue tracking features added:")
    print("- Real-time queue length display for each booth")
    print("- Color-coded queue indicators:")
    print("  • Green: No queue")
    print("  • Yellow: 1-2 vehicles waiting")
    print("  • Red: 3+ vehicles waiting")
    print("- Visual queue bar showing relative queue size")
    print("- Occupancy percentage for each detector")
    print("- Total queue count across all booths")
    
    print("\nTo test with simulation:")
    print("1. Start the web app: python3 run_webapp.py")
    print("2. Open browser to: http://localhost:5000")
    print("3. Click 'Start Simulation'")
    print("4. Watch queue lengths update in real-time")

if __name__ == "__main__":
    test_api()