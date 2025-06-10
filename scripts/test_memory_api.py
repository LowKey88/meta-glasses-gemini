#!/usr/bin/env python3
"""Test memory API endpoint directly"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from datetime import datetime, timedelta
import jwt

# API configuration
# Use 'app' as hostname when running inside container
# Inside container, the app runs on port 8080
API_URL = "http://app:8080" if os.getenv('INSIDE_DOCKER') else "http://localhost:8111"
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "meta-admin-2024")
JWT_SECRET = "meta-glasses-development-jwt-secret-key-12345678"

def create_test_token():
    """Create a test JWT token"""
    payload = {
        "user": "admin",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def test_memory_api():
    """Test the memory API endpoints"""
    
    print("=== TESTING MEMORY API ===\n")
    
    # 1. Login to get token
    print("1. Testing login:")
    login_response = requests.post(
        f"{API_URL}/api/dashboard/login",
        json={"password": DASHBOARD_PASSWORD}
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["token"]
        print("   Login successful!")
    else:
        print(f"   Login failed: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        # Try with generated token
        token = create_test_token()
        print("   Using generated token instead")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Test get memories endpoint
    print("\n2. Testing GET /api/dashboard/memories:")
    memories_response = requests.get(
        f"{API_URL}/api/dashboard/memories",
        headers=headers
    )
    
    print(f"   Status code: {memories_response.status_code}")
    
    if memories_response.status_code == 200:
        data = memories_response.json()
        print(f"   Total memories returned: {data.get('total', 0)}")
        memories = data.get('memories', [])
        print(f"   Memories array length: {len(memories)}")
        
        if memories:
            # Check first few memories
            print("\n   First 3 memories:")
            for i, memory in enumerate(memories[:3]):
                print(f"\n   Memory {i+1}:")
                print(f"     ID: {memory.get('id')}")
                print(f"     Type: {memory.get('type')}")
                print(f"     Content: {memory.get('content', '')[:100]}...")
                print(f"     Created: {memory.get('created_at')}")
                print(f"     Status: {memory.get('status')}")
                print(f"     User ID: {memory.get('user_id')}")
    else:
        print(f"   Error: {memories_response.text}")
    
    # 3. Test create memory
    print("\n3. Testing POST /api/dashboard/memories:")
    test_memory = {
        "user_id": "60122873632",
        "type": "note",
        "content": f"Test memory created at {datetime.now().isoformat()}",
        "tags": []
    }
    
    create_response = requests.post(
        f"{API_URL}/api/dashboard/memories",
        headers=headers,
        json=test_memory
    )
    
    print(f"   Status code: {create_response.status_code}")
    if create_response.status_code == 200:
        result = create_response.json()
        print(f"   Success: {result.get('success')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Memory ID: {result.get('id')}")
        
        # Get memories again to see if it appears
        print("\n4. Verifying new memory appears in list:")
        verify_response = requests.get(
            f"{API_URL}/api/dashboard/memories?limit=5",
            headers=headers
        )
        
        if verify_response.status_code == 200:
            data = verify_response.json()
            memories = data.get('memories', [])
            
            # Check if our test memory is in the list
            found = False
            for memory in memories:
                if "Test memory created at" in memory.get('content', ''):
                    found = True
                    print(f"   ✓ Found test memory: {memory.get('content')[:50]}...")
                    break
            
            if not found:
                print("   ✗ Test memory NOT found in list!")
                print(f"   First memory in list: {memories[0].get('content', '')[:50] if memories else 'No memories'}...")
    else:
        print(f"   Error: {create_response.text}")
    
    # 5. Check response data structure
    print("\n5. Checking data structure:")
    if memories_response.status_code == 200:
        print("   Raw response keys:", list(memories_response.json().keys()))
        if memories:
            print("   Memory object keys:", list(memories[0].keys()))

if __name__ == "__main__":
    test_memory_api()