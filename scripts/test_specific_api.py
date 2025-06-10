#!/usr/bin/env python3
"""
Test the specific API endpoints that the dashboard uses
"""

import requests
import json
from datetime import datetime, timedelta
import jwt

def test_specific_api():
    """Test the exact API calls the dashboard makes"""
    
    print("\n=== TESTING SPECIFIC API ENDPOINTS ===\n")
    
    # Create JWT token (same as dashboard would)
    JWT_SECRET = "meta-glasses-development-jwt-secret-key-12345678"
    payload = {
        "user": "admin",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    
    base_url = "http://localhost:8080"
    
    # Test the exact endpoints the dashboard calls
    tests = [
        ("All memories", "/api/dashboard/memories"),
        ("Personal Info filter", "/api/dashboard/memories?memory_type=personal_info"),
        ("With limit", "/api/dashboard/memories?limit=20"),
        ("Manual source test", "/api/dashboard/memories?limit=100")  # To check for manual memories
    ]
    
    for test_name, endpoint in tests:
        print(f"🔍 {test_name}: {endpoint}")
        
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                memories = data.get('memories', [])
                total = data.get('total', 0)
                
                print(f"   ✅ Status: {response.status_code}")
                print(f"   📊 Total: {total}, Returned: {len(memories)}")
                
                # Analyze the memories
                if memories:
                    sources = {}
                    types = {}
                    manual_memories = []
                    
                    for memory in memories:
                        source = memory.get('extracted_from') or 'none'
                        mem_type = memory.get('type', 'unknown')
                        
                        sources[source] = sources.get(source, 0) + 1
                        types[mem_type] = types.get(mem_type, 0) + 1
                        
                        if source == 'manual':
                            manual_memories.append(memory)
                    
                    print(f"   📈 Sources: {sources}")
                    print(f"   📋 Types: {types}")
                    
                    if manual_memories:
                        print(f"   ✅ Found {len(manual_memories)} manual memories:")
                        for memory in manual_memories[:3]:
                            content = memory.get('content', '')[:40]
                            mem_type = memory.get('type', '')
                            print(f"      - [{mem_type}] {content}...")
                    
                    # Show first few memories regardless
                    print("   📝 Sample memories:")
                    for i, memory in enumerate(memories[:3]):
                        content = memory.get('content', '')[:40]
                        source = memory.get('extracted_from', 'none')
                        mem_type = memory.get('type', 'unknown')
                        print(f"      {i+1}. [{source}] {mem_type}: {content}...")
                else:
                    print("   ❌ No memories in response")
                    
            else:
                print(f"   ❌ Status: {response.status_code}")
                print(f"   ❌ Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
        
        print()

if __name__ == "__main__":
    test_specific_api()