#!/usr/bin/env python3
"""
Test different ports to find where the API is running
"""

import requests
import json
from datetime import datetime, timedelta
import jwt

def test_api_ports():
    """Test different ports to find the API"""
    
    print("\n=== TESTING API PORTS ===\n")
    
    # Create JWT token
    JWT_SECRET = "meta-glasses-development-jwt-secret-key-12345678"
    payload = {
        "user": "admin", 
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test different ports
    ports = [8080, 8000, 8111, 3000, 5000]
    
    for port in ports:
        print(f"🔍 Testing port {port}...")
        
        try:
            # Try basic health check first
            response = requests.get(f"http://localhost:{port}/", timeout=5)
            print(f"   Root endpoint ({port}): {response.status_code}")
            
            # Try API endpoint
            api_response = requests.get(
                f"http://localhost:{port}/api/dashboard/memories?limit=5", 
                headers=headers, 
                timeout=5
            )
            print(f"   API endpoint ({port}): {api_response.status_code}")
            
            if api_response.status_code == 200:
                data = api_response.json()
                memories = data.get('memories', [])
                print(f"   ✅ SUCCESS! Found {len(memories)} memories on port {port}")
                
                if memories:
                    print("   Sample memory:")
                    memory = memories[0]
                    print(f"     Content: {memory.get('content', '')[:50]}...")
                    print(f"     Source: {memory.get('extracted_from', 'none')}")
                    print(f"     Type: {memory.get('type', 'unknown')}")
                
                return port
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Failed: {str(e)[:50]}...")
    
    print("\n❌ No working API port found!")
    return None

if __name__ == "__main__":
    working_port = test_api_ports()
    if working_port:
        print(f"\n✅ API is running on port {working_port}")
    else:
        print("\n❌ Could not find working API port")
        print("\nTry these commands to debug:")
        print("  ps aux | grep python")
        print("  netstat -tulpn | grep LISTEN")
        print("  curl http://localhost:8080/docs")