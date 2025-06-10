#!/usr/bin/env python3
"""
Verify that the memory fix worked and check API response
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.memory_manager import MemoryManager
from utils.redis_utils import r

def verify_memory_fix():
    """Verify the manual memory fix worked"""
    
    print("\n=== VERIFYING MEMORY FIX ===\n")
    
    user_id = "60122873632"
    
    # 1. Check manual memories directly
    print("1. Checking fixed manual memories:")
    
    index_key = MemoryManager.get_index_key(user_id)
    memory_ids = r.smembers(index_key)
    
    manual_count = 0
    personal_info_count = 0
    
    for memory_id in memory_ids:
        memory_id_str = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
        memory_key = MemoryManager.get_memory_key(user_id, memory_id_str)
        raw_data = r.get(memory_key)
        
        if raw_data:
            try:
                memory_data = json.loads(raw_data)
                
                if memory_data.get('status') == 'active':
                    extracted_from = memory_data.get('extracted_from')
                    memory_type = memory_data.get('type')
                    
                    if extracted_from == 'manual':
                        manual_count += 1
                        print(f"   Manual: {memory_data.get('content', '')[:60]}...")
                        print(f"           Type: {memory_type}, ID: {memory_id_str}")
                    
                    if memory_type == 'personal_info' and memory_data.get('status') == 'active':
                        personal_info_count += 1
                        print(f"   Personal Info: {memory_data.get('content', '')[:60]}...")
                        print(f"                  Source: {extracted_from}, ID: {memory_id_str}")
                        
            except json.JSONDecodeError:
                pass
    
    print(f"\n   Total manual memories: {manual_count}")
    print(f"   Total personal_info memories: {personal_info_count}")
    
    # 2. Test API calls
    print("\n2. Testing API calls:")
    
    # Test get_all_memories
    all_memories = MemoryManager.get_all_memories(user_id)
    manual_api = [m for m in all_memories if m.get('extracted_from') == 'manual']
    personal_info_api = [m for m in all_memories if m.get('type') == 'personal_info']
    
    print(f"   get_all_memories returned: {len(all_memories)} total")
    print(f"   Manual memories via API: {len(manual_api)}")
    print(f"   Personal Info memories via API: {len(personal_info_api)}")
    
    # Test get_memories_by_type specifically
    personal_info_direct = MemoryManager.get_memories_by_type(user_id, 'personal_info')
    print(f"   get_memories_by_type('personal_info'): {len(personal_info_direct)}")
    
    if personal_info_direct:
        print("\n   Personal Info memories from get_memories_by_type:")
        for memory in personal_info_direct[:5]:
            print(f"   - {memory.get('content', '')[:50]}...")
            print(f"     Type: {memory.get('type')}, Source: {memory.get('extracted_from')}")
    
    # 3. Check specific sample memories
    print("\n3. Checking specific fixed memories:")
    
    sample_ids = ['0290b426', 'f7d27174', 'a327b621', '02bc730e']  # From the fix output
    
    for sample_id in sample_ids:
        memory_key = MemoryManager.get_memory_key(user_id, sample_id)
        raw_data = r.get(memory_key)
        
        if raw_data:
            try:
                memory_data = json.loads(raw_data)
                print(f"   Memory {sample_id}:")
                print(f"     Content: {memory_data.get('content', '')}")
                print(f"     Type: {memory_data.get('type')}")
                print(f"     Source: {memory_data.get('extracted_from')}")
                print(f"     Status: {memory_data.get('status')}")
            except:
                print(f"   Memory {sample_id}: Failed to parse")
        else:
            print(f"   Memory {sample_id}: Not found")

if __name__ == "__main__":
    verify_memory_fix()