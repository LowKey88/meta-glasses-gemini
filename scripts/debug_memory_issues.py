#!/usr/bin/env python3
"""Debug memory creation and display issues"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from utils.redis_utils import r
from utils.memory_manager import MemoryManager
from utils.redis_key_builder import redis_keys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_memory_issues():
    """Debug memory creation and retrieval issues"""
    
    # Common user IDs to check
    user_ids = ["60122873632", "60122873632@s.whatsapp.net", "unknown"]
    
    print("\n=== DEBUGGING MEMORY ISSUES ===\n")
    
    # 1. Check memory indexes for all possible user IDs
    print("1. Checking memory indexes:")
    for user_id in user_ids:
        index_key = redis_keys.get_user_memory_index_key(user_id)
        memory_ids = r.smembers(index_key)
        print(f"   User ID: {user_id}")
        print(f"   Index key: {index_key}")
        print(f"   Number of memories in index: {len(memory_ids)}")
        if memory_ids:
            print(f"   Sample memory IDs: {list(memory_ids)[:3]}")
        print()
    
    # 2. Check all memory keys in Redis
    print("\n2. Checking all memory keys in Redis:")
    memory_pattern = redis_keys._build_key(redis_keys.USER, "memory", "*")
    all_memory_keys = r.keys(memory_pattern)
    print(f"   Pattern: {memory_pattern}")
    print(f"   Total memory keys found: {len(all_memory_keys)}")
    
    # Group by user ID
    user_memories = {}
    for key in all_memory_keys[:10]:  # Check first 10
        key_str = key.decode() if isinstance(key, bytes) else key
        parts = key_str.split(":")
        if len(parts) >= 5:  # meta-glasses:user:memory:user_id:memory_id
            user_id = parts[3]
            if user_id not in user_memories:
                user_memories[user_id] = []
            user_memories[user_id].append(key_str)
    
    print(f"   Unique user IDs found: {list(user_memories.keys())}")
    for user_id, keys in user_memories.items():
        print(f"   User {user_id}: {len(keys)} memories")
    
    # 3. Check a sample memory for data integrity
    print("\n3. Checking sample memories for data integrity:")
    for key in all_memory_keys[:3]:  # Check first 3 memories
        key_str = key.decode() if isinstance(key, bytes) else key
        memory_data = r.get(key_str)
        if memory_data:
            try:
                memory = json.loads(memory_data)
                print(f"\n   Key: {key_str}")
                print(f"   ID: {memory.get('id')}")
                print(f"   User ID: {memory.get('user_id')}")
                print(f"   Type: {memory.get('type')}")
                print(f"   Status: {memory.get('status')}")
                print(f"   Content: {memory.get('content', '')[:100]}...")
                print(f"   Created: {memory.get('created_at')}")
                print(f"   Extracted from: {memory.get('extracted_from')}")
            except json.JSONDecodeError as e:
                print(f"   ERROR: Failed to decode JSON for key {key_str}: {e}")
                print(f"   Raw data: {memory_data[:200]}...")
    
    # 4. Test memory retrieval using MemoryManager
    print("\n4. Testing MemoryManager.get_all_memories():")
    for user_id in user_ids:
        memories = MemoryManager.get_all_memories(user_id)
        print(f"   User ID: {user_id}")
        print(f"   Memories retrieved: {len(memories)}")
        if memories:
            sample = memories[0]
            print(f"   Sample memory: {sample.get('content', '')[:100]}...")
    
    # 5. Check for encoding issues
    print("\n5. Checking for encoding issues:")
    for key in all_memory_keys[:5]:
        key_str = key.decode() if isinstance(key, bytes) else key
        memory_data = r.get(key_str)
        if memory_data:
            # Check if it's bytes or string
            print(f"\n   Key: {key_str}")
            print(f"   Data type: {type(memory_data)}")
            if isinstance(memory_data, bytes):
                print("   Attempting decode...")
                try:
                    decoded = memory_data.decode('utf-8')
                    print("   UTF-8 decode successful")
                except UnicodeDecodeError as e:
                    print(f"   UTF-8 decode failed: {e}")
                    # Try other encodings
                    for encoding in ['latin-1', 'cp1252', 'ascii']:
                        try:
                            decoded = memory_data.decode(encoding)
                            print(f"   {encoding} decode successful")
                            break
                        except:
                            print(f"   {encoding} decode failed")
    
    # 6. Check Redis key consistency
    print("\n6. Checking Redis key consistency:")
    # Check if old key patterns exist
    old_patterns = [
        "memory:*",
        "josancamon:*memory*",
        "whatsapp:*:memory:*"
    ]
    
    for pattern in old_patterns:
        keys = r.keys(pattern)
        if keys:
            print(f"   Found {len(keys)} keys matching old pattern: {pattern}")
            print(f"   Sample keys: {[k.decode() if isinstance(k, bytes) else k for k in keys[:3]]}")

if __name__ == "__main__":
    debug_memory_issues()