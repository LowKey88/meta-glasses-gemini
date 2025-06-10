#!/usr/bin/env python3
"""
Debug why manual memories don't appear in get_all_memories
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.memory_manager import MemoryManager
from utils.redis_utils import r

def debug_manual_memory_ordering():
    """Debug the ordering and filtering of manual memories"""
    
    print("\n=== DEBUGGING MANUAL MEMORY ORDERING ===\n")
    
    user_id = "60122873632"
    
    # 1. Get all memories with detailed analysis
    print("1. Analyzing get_all_memories:")
    all_memories = MemoryManager.get_all_memories(user_id)
    
    manual_in_all = [m for m in all_memories if m.get('extracted_from') == 'manual']
    limitless_in_all = [m for m in all_memories if m.get('extracted_from') == 'limitless']
    none_in_all = [m for m in all_memories if not m.get('extracted_from')]
    
    print(f"   Total memories: {len(all_memories)}")
    print(f"   Manual: {len(manual_in_all)}")
    print(f"   Limitless: {len(limitless_in_all)}")
    print(f"   None/empty: {len(none_in_all)}")
    
    # 2. Check creation dates of manual memories
    print("\n2. Manual memories in get_all_memories:")
    if manual_in_all:
        for i, memory in enumerate(manual_in_all):
            print(f"   {i+1}. {memory.get('content', '')[:50]}...")
            print(f"      Created: {memory.get('created_at')}")
            print(f"      Type: {memory.get('type')}")
    else:
        print("   ❌ NO manual memories found in get_all_memories!")
    
    # 3. Check the first 20 memories to see what's at the top
    print("\n3. First 20 memories from get_all_memories (by creation date):")
    for i, memory in enumerate(all_memories[:20]):
        source = memory.get('extracted_from', 'none')
        created = memory.get('created_at', 'unknown')[:19]  # Just date/time part
        content = memory.get('content', '')[:40]
        print(f"   {i+1:2d}. [{source:8s}] {created} | {content}...")
    
    # 4. Check personal_info memories specifically
    print("\n4. Personal info memories from get_memories_by_type:")
    personal_info = MemoryManager.get_memories_by_type(user_id, 'personal_info')
    for i, memory in enumerate(personal_info):
        print(f"   {i+1}. {memory.get('content', '')[:50]}...")
        print(f"      Created: {memory.get('created_at')}")
        print(f"      Source: {memory.get('extracted_from')}")
    
    # 5. Check if manual memories are being filtered out somehow
    print("\n5. Checking raw Redis data for manual memories:")
    
    # Get memory IDs from index
    index_key = MemoryManager.get_index_key(user_id)
    memory_ids = r.smembers(index_key)
    
    manual_raw_count = 0
    for memory_id in memory_ids:
        memory_id_str = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
        memory_key = MemoryManager.get_memory_key(user_id, memory_id_str)
        raw_data = r.get(memory_key)
        
        if raw_data:
            try:
                memory_data = json.loads(raw_data)
                if (memory_data.get('extracted_from') == 'manual' and 
                    memory_data.get('status') == 'active'):
                    manual_raw_count += 1
                    if manual_raw_count <= 5:  # Show first 5
                        print(f"   Raw manual memory {manual_raw_count}:")
                        print(f"     ID: {memory_id_str}")
                        print(f"     Content: {memory_data.get('content', '')[:50]}...")
                        print(f"     Created: {memory_data.get('created_at')}")
                        print(f"     Status: {memory_data.get('status')}")
                        print(f"     Source: {memory_data.get('extracted_from')}")
            except:
                pass
    
    print(f"\n   Total raw manual memories found: {manual_raw_count}")
    
    # 6. Test the limit behavior
    print("\n6. Testing limit behavior:")
    limited_memories = MemoryManager.get_all_memories(user_id)[:50]
    manual_in_limited = [m for m in limited_memories if m.get('extracted_from') == 'manual']
    print(f"   First 50 memories contain {len(manual_in_limited)} manual memories")

if __name__ == "__main__":
    debug_manual_memory_ordering()