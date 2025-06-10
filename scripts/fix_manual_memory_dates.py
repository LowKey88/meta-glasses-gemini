#!/usr/bin/env python3
"""
Fix manual memory creation dates to make them appear in recent results
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.memory_manager import MemoryManager
from utils.redis_utils import r
from datetime import datetime, timedelta

def fix_manual_memory_dates():
    """Update creation dates for manual memories to make them recent"""
    
    print("\n=== FIXING MANUAL MEMORY DATES ===\n")
    
    user_id = "60122873632"
    
    # Get all manual memories
    index_key = MemoryManager.get_index_key(user_id)
    memory_ids = r.smembers(index_key)
    
    manual_memories = []
    
    # Find all manual memories
    for memory_id in memory_ids:
        memory_id_str = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
        memory_key = MemoryManager.get_memory_key(user_id, memory_id_str)
        raw_data = r.get(memory_key)
        
        if raw_data:
            try:
                memory_data = json.loads(raw_data)
                if (memory_data.get('extracted_from') == 'manual' and 
                    memory_data.get('status') == 'active'):
                    manual_memories.append((memory_id_str, memory_key, memory_data))
            except:
                pass
    
    print(f"Found {len(manual_memories)} manual memories to update")
    
    if not manual_memories:
        print("No manual memories found!")
        return
    
    # Update their creation dates to recent dates
    # We'll spread them over the last few hours to maintain some ordering
    base_time = datetime.now()
    
    updated_count = 0
    
    for i, (memory_id, memory_key, memory_data) in enumerate(manual_memories):
        # Create a recent timestamp, spacing them 30 minutes apart
        new_time = base_time - timedelta(minutes=30 * i)
        new_timestamp = new_time.isoformat()
        
        old_timestamp = memory_data.get('created_at', 'unknown')
        
        print(f"\n🔧 Updating memory {memory_id}:")
        print(f"   Content: {memory_data.get('content', '')[:50]}...")
        print(f"   Old date: {old_timestamp}")
        print(f"   New date: {new_timestamp}")
        
        # Update the memory
        memory_data['created_at'] = new_timestamp
        memory_data['updated_at'] = datetime.now().isoformat()
        
        # Save back to Redis
        r.set(memory_key, json.dumps(memory_data))
        updated_count += 1
        
        print(f"   ✅ Updated!")
    
    print(f"\n📊 Summary:")
    print(f"   Updated {updated_count} manual memories")
    print(f"   Manual memories should now appear in 'All Types' view")
    print(f"   They will be spread across the most recent positions")
    
    # Test the result
    print(f"\n🔍 Testing result:")
    all_memories = MemoryManager.get_all_memories(user_id)
    first_50 = all_memories[:50]
    manual_in_first_50 = [m for m in first_50 if m.get('extracted_from') == 'manual']
    
    print(f"   First 50 memories now contain {len(manual_in_first_50)} manual memories")
    
    if manual_in_first_50:
        print(f"   ✅ Success! Manual memories in top 50:")
        for i, memory in enumerate(manual_in_first_50):
            position = next(j for j, m in enumerate(first_50) if m['id'] == memory['id']) + 1
            content = memory.get('content', '')[:40]
            print(f"      Position {position:2d}: {content}...")

if __name__ == "__main__":
    fix_manual_memory_dates()