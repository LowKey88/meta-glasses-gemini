#!/usr/bin/env python3
"""
Revert the manual memory creation dates back to their original values
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.memory_manager import MemoryManager
from utils.redis_utils import r

def revert_manual_memory_dates():
    """Revert manual memory dates to approximate original values"""
    
    print("\n=== REVERTING MANUAL MEMORY DATES ===\n")
    
    user_id = "60122873632"
    
    # Original dates (approximate, based on the content)
    original_dates = {
        '0290b426': '2025-06-04T16:45:58.944478',  # Netflix
        'a327b621': '2025-06-04T16:41:52.156372',  # Nasi Ayam  
        'cb7af95d': '2025-06-02T00:13:53.751694',  # Fafa birthday
        'f7d27174': '2025-06-04T07:46:54.095913',  # Work
        '02bc730e': '2025-06-04T16:43:21.119484',  # Born in KT
        '238d7f4b': '2025-06-02T01:50:21.760062',  # Wife is Fafa
        '262e5cd4': '2025-06-02T00:02:19.837985',  # Arissa birthday
        '92f79071': '2025-06-02T01:51:25.311883',  # Name is Hisyam
        'b498fa1b': '2025-06-01T23:42:48.314640',  # Daughter Arissa
        'bff4b783': '2025-06-02T01:55:59.619902',  # Anniversary
    }
    
    # Get all manual memories
    index_key = MemoryManager.get_index_key(user_id)
    memory_ids = r.smembers(index_key)
    
    reverted_count = 0
    
    for memory_id in memory_ids:
        memory_id_str = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
        
        if memory_id_str in original_dates:
            memory_key = MemoryManager.get_memory_key(user_id, memory_id_str)
            raw_data = r.get(memory_key)
            
            if raw_data:
                try:
                    memory_data = json.loads(raw_data)
                    
                    if memory_data.get('extracted_from') == 'manual':
                        old_date = memory_data.get('created_at')
                        new_date = original_dates[memory_id_str]
                        
                        print(f"🔄 Reverting memory {memory_id_str}:")
                        print(f"   Content: {memory_data.get('content', '')[:50]}...")
                        print(f"   Current date: {old_date}")
                        print(f"   Original date: {new_date}")
                        
                        # Revert the date
                        memory_data['created_at'] = new_date
                        
                        # Save back to Redis
                        r.set(memory_key, json.dumps(memory_data))
                        reverted_count += 1
                        
                        print(f"   ✅ Reverted!")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Failed to parse memory {memory_id_str}")
    
    print(f"\n📊 Summary:")
    print(f"   Reverted {reverted_count} manual memory dates")
    print(f"   Now the API limit fix should show all memories properly")

if __name__ == "__main__":
    revert_manual_memory_dates()