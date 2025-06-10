#!/usr/bin/env python3
"""
Test the dashboard API endpoint directly to see what it returns
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime, timedelta
import jwt

def test_dashboard_api():
    """Test the dashboard API endpoint directly"""
    
    print("\n=== TESTING DASHBOARD API ===\n")
    
    # Create JWT token for API access
    JWT_SECRET = "meta-glasses-development-jwt-secret-key-12345678"
    payload = {
        "user": "admin",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test different API endpoints
    base_url = "http://localhost:8111"  # Adjust if different
    
    endpoints = [
        "/api/dashboard/memories",
        "/api/dashboard/memories?memory_type=personal_info",
        "/api/dashboard/memories?memory_type=fact",
        "/api/dashboard/memories?limit=10"
    ]
    
    for endpoint in endpoints:
        print(f"🔍 Testing: {endpoint}")
        
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                memories = data.get('memories', [])
                total = data.get('total', 0)
                
                print(f"   Total: {total}")
                print(f"   Memories returned: {len(memories)}")
                
                if memories:
                    # Check sources and types
                    sources = {}
                    types = {}
                    
                    for memory in memories:
                        source = memory.get('extracted_from', 'none')
                        memory_type = memory.get('type', 'unknown')
                        
                        sources[source] = sources.get(source, 0) + 1
                        types[memory_type] = types.get(memory_type, 0) + 1
                    
                    print(f"   Sources: {sources}")
                    print(f"   Types: {types}")
                    
                    # Show first few memories
                    print("   Sample memories:")
                    for i, memory in enumerate(memories[:3]):
                        content = memory.get('content', '')[:50]
                        source = memory.get('extracted_from', 'none')
                        mem_type = memory.get('type', 'unknown')
                        print(f"     {i+1}. [{source}] {mem_type}: {content}...")
                else:
                    print("   ❌ No memories returned")
            else:
                print(f"   ❌ Error: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
        
        print()

    # Test direct memory manager call for comparison
    print("🔍 Testing direct MemoryManager call:")
    try:
        from utils.memory_manager import MemoryManager
        
        user_id = "60122873632"
        direct_memories = MemoryManager.get_all_memories(user_id)
        direct_personal = MemoryManager.get_memories_by_type(user_id, 'personal_info')
        
        print(f"   Direct get_all_memories: {len(direct_memories)}")
        print(f"   Direct get_memories_by_type('personal_info'): {len(direct_personal)}")
        
        # Check if there's a difference
        if direct_personal:
            print("   Direct personal_info memories:")
            for memory in direct_personal[:3]:
                content = memory.get('content', '')[:50]
                source = memory.get('extracted_from', 'none')
                print(f"     - [{source}] {content}...")
                
    except Exception as e:
        print(f"   ❌ Direct call failed: {e}")

if __name__ == "__main__":
    test_dashboard_api()