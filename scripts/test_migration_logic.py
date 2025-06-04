#!/usr/bin/env python3
"""
Test Migration Logic

Tests the key migration logic without connecting to Redis.
This validates our key identification and generation logic.
"""

import sys
import os
import base64

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_key_builder import RedisKeyBuilder

class MigrationLogicTester:
    """Tests migration logic without Redis connection."""
    
    def __init__(self):
        self.old_prefix = "josancamon:rayban-meta-glasses-api"
        self.test_cases = [
            # Cache keys (base64 encoded paths)
            "josancamon:rayban-meta-glasses-api:dGVzdC9wYXRo",  # test/path
            "josancamon:rayban-meta-glasses-api:c2VhcmNoL3Jlc3VsdHM=",  # search/results
            
            # Reminder keys
            "josancamon:rayban-meta-glasses-api:reminder:event_123",
            "josancamon:rayban-meta-glasses-api:reminder:cal_456",
            
            # User data keys
            "josancamon:rayban-meta-glasses-api:conversation_history:60122873632",
            "josancamon:rayban-meta-glasses-api:user_profile:60122873632",
            
            # Cancellation state keys
            "josancamon:rayban-meta-glasses-api:cancellation:wa:60122873632",
            
            # Unknown/edge cases
            "josancamon:rayban-meta-glasses-api:unknown_type:some_id",
            "josancamon:rayban-meta-glasses-api:malformed",
            "different:prefix:key"
        ]
    
    def identify_key_type(self, key: str):
        """Copy of migration logic for testing."""
        if not key.startswith(self.old_prefix):
            return "unknown", {}
            
        suffix = key[len(self.old_prefix):].lstrip(":")
        parts = suffix.split(":")
        
        if not parts:
            return "unknown", {}
            
        # Generic cache keys (base64 encoded paths)
        if len(parts) == 1:
            try:
                decoded = base64.b64decode(parts[0]).decode('utf-8')
                return "cache", {"encoded_path": parts[0], "original_path": decoded}
            except:
                return "unknown", {"suffix": suffix}
        
        # Reminder keys: reminder:{event_id}
        elif len(parts) == 2 and parts[0] == "reminder":
            return "reminder", {"event_id": parts[1]}
        
        # User data keys: {type}:{user_id}
        elif len(parts) == 2:
            key_type = parts[0]
            user_id = parts[1]
            
            if key_type == "conversation_history":
                return "user_history", {"user_id": user_id}
            elif key_type == "user_profile":
                return "user_profile", {"user_id": user_id}
            else:
                return "unknown", {"type": key_type, "user_id": user_id}
        
        # Cancellation state keys: cancellation:wa:{user_id}
        elif len(parts) == 3 and parts[0] == "cancellation":
            return "cancellation", {"platform": parts[1], "user_id": parts[2]}
        
        else:
            return "unknown", {"suffix": suffix, "parts": parts}
    
    def generate_new_key(self, key_type: str, components: dict):
        """Generate new key using RedisKeyBuilder."""
        try:
            if key_type == "cache":
                return RedisKeyBuilder.get_generic_cache_key(components["original_path"])
            
            elif key_type == "reminder":
                return RedisKeyBuilder.get_reminder_event_key(components["event_id"])
            
            elif key_type == "user_history":
                return RedisKeyBuilder.get_user_history_key(components["user_id"])
            
            elif key_type == "user_profile":
                return RedisKeyBuilder.get_user_profile_key(components["user_id"])
            
            elif key_type == "cancellation":
                return RedisKeyBuilder.get_cancellation_state_key(
                    components["user_id"], 
                    components["platform"]
                )
            
            else:
                return None
                
        except Exception as e:
            print(f"Error generating new key: {e}")
            return None
    
    def test_all_cases(self):
        """Test all migration cases."""
        print("🧪 Testing Migration Logic")
        print("=" * 80)
        
        success_count = 0
        total_count = len(self.test_cases)
        
        for i, old_key in enumerate(self.test_cases, 1):
            print(f"\nTest Case {i}/{total_count}:")
            print(f"  Old Key: {old_key}")
            
            # Identify key type
            key_type, components = self.identify_key_type(old_key)
            print(f"  Key Type: {key_type}")
            print(f"  Components: {components}")
            
            # Generate new key
            new_key = self.generate_new_key(key_type, components)
            if new_key:
                print(f"  New Key: {new_key}")
                print(f"  ✅ Migration: SUCCESS")
                success_count += 1
            else:
                print(f"  ❌ Migration: FAILED (no new key generated)")
        
        print("\n" + "=" * 80)
        print(f"📊 Test Results: {success_count}/{total_count} successful")
        print(f"Success Rate: {(success_count/total_count)*100:.1f}%")
        
        # Test specific scenarios
        self.test_edge_cases()
    
    def test_edge_cases(self):
        """Test edge cases and validation."""
        print("\n🔍 Testing Edge Cases:")
        
        # Test base64 encoding/decoding
        test_paths = [
            "search/results",
            "cache/user/123",
            "api/response/data",
            "special/chars/!@#$%"
        ]
        
        print("\n  Base64 Cache Key Tests:")
        for path in test_paths:
            encoded = base64.b64encode(path.encode('utf-8')).decode('utf-8')
            old_key = f"{self.old_prefix}:{encoded}"
            
            key_type, components = self.identify_key_type(old_key)
            new_key = self.generate_new_key(key_type, components)
            
            print(f"    {path} -> {new_key}")
            
            # Verify round-trip
            if key_type == "cache" and components.get("original_path") == path:
                print(f"      ✅ Round-trip successful")
            else:
                print(f"      ❌ Round-trip failed")
        
        # Test key collision scenarios
        print("\n  Key Collision Tests:")
        user_keys = [
            f"{self.old_prefix}:conversation_history:user1",
            f"{self.old_prefix}:user_profile:user1",
        ]
        
        new_keys = []
        for old_key in user_keys:
            key_type, components = self.identify_key_type(old_key)
            new_key = self.generate_new_key(key_type, components)
            new_keys.append(new_key)
            print(f"    {old_key} -> {new_key}")
        
        # Check for duplicates
        if len(new_keys) == len(set(new_keys)):
            print(f"      ✅ No key collisions detected")
        else:
            print(f"      ❌ Key collision detected!")


def main():
    """Run migration logic tests."""
    try:
        tester = MigrationLogicTester()
        tester.test_all_cases()
        print(f"\n✅ Migration logic testing complete!")
        
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        raise


if __name__ == "__main__":
    main()