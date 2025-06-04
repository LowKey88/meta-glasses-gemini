"""
Unit tests for Redis Key Builder utility.
"""

import pytest
import base64
from utils.redis_key_builder import RedisKeyBuilder, redis_keys


class TestRedisKeyBuilder:
    """Test cases for RedisKeyBuilder class."""
    
    def test_base_prefix(self):
        """Test that all keys start with the correct base prefix."""
        key = RedisKeyBuilder.get_user_profile_key("test_user")
        assert key.startswith("meta-glasses:")
    
    def test_build_key_basic(self):
        """Test basic key building functionality."""
        key = RedisKeyBuilder._build_key("cache", "generic", "test")
        expected = "meta-glasses:cache:generic:test"
        assert key == expected
    
    def test_build_key_filters_empty(self):
        """Test that empty values are filtered out."""
        key = RedisKeyBuilder._build_key("cache", "", None, "test")
        expected = "meta-glasses:cache:test"
        assert key == expected
    
    def test_encode_path(self):
        """Test path encoding functionality."""
        path = "test/path/with/slashes"
        encoded = RedisKeyBuilder._encode_path(path)
        # Verify it's base64 encoded
        decoded = base64.b64decode(encoded).decode('utf-8')
        assert decoded == path
    
    def test_hash_content(self):
        """Test content hashing functionality."""
        content = "test content for hashing"
        hash1 = RedisKeyBuilder._hash_content(content)
        hash2 = RedisKeyBuilder._hash_content(content)
        
        # Same content should produce same hash
        assert hash1 == hash2
        # Hash should be 12 characters
        assert len(hash1) == 12
        # Different content should produce different hash
        hash3 = RedisKeyBuilder._hash_content("different content")
        assert hash1 != hash3


class TestCacheKeys:
    """Test cache key generation."""
    
    def test_generic_cache_key(self):
        """Test generic cache key generation."""
        path = "search/results"
        key = RedisKeyBuilder.get_generic_cache_key(path)
        
        # Should contain encoded path
        encoded_path = base64.b64encode(path.encode('utf-8')).decode('utf-8')
        expected = f"meta-glasses:cache:generic:{encoded_path}"
        assert key == expected
    
    def test_search_cache_key(self):
        """Test search cache key generation."""
        query = "test search query"
        key = RedisKeyBuilder.get_search_cache_key(query)
        
        assert key.startswith("meta-glasses:cache:search:")
        assert len(key.split(":")) == 4  # prefix:cache:search:hash
    
    def test_api_cache_key(self):
        """Test API cache key generation."""
        endpoint = "/api/test"
        params = "param1=value1"
        key = RedisKeyBuilder.get_api_cache_key(endpoint, params)
        
        assert key.startswith("meta-glasses:cache:api:")
        assert len(key.split(":")) == 4  # prefix:cache:api:hash


class TestUserKeys:
    """Test user-related key generation."""
    
    def test_user_history_key(self):
        """Test user history key generation."""
        user_id = "12345"
        key = RedisKeyBuilder.get_user_history_key(user_id)
        expected = f"meta-glasses:user:history:{user_id}"
        assert key == expected
    
    def test_user_profile_key(self):
        """Test user profile key generation."""
        user_id = "12345"
        key = RedisKeyBuilder.get_user_profile_key(user_id)
        expected = f"meta-glasses:user:profile:{user_id}"
        assert key == expected
    
    def test_user_context_key(self):
        """Test user context key generation."""
        user_id = "12345"
        key = RedisKeyBuilder.get_user_context_key(user_id)
        expected = f"meta-glasses:user:context:{user_id}"
        assert key == expected
    
    def test_user_memory_key(self):
        """Test user memory key generation."""
        user_id = "12345"
        memory_id = "mem_abc123"
        key = RedisKeyBuilder.get_user_memory_key(user_id, memory_id)
        expected = f"meta-glasses:user:memory:{user_id}:{memory_id}"
        assert key == expected
    
    def test_user_memory_index_key(self):
        """Test user memory index key generation."""
        user_id = "12345"
        key = RedisKeyBuilder.get_user_memory_index_key(user_id)
        expected = f"meta-glasses:user:memory_index:{user_id}"
        assert key == expected


class TestReminderKeys:
    """Test reminder and calendar key generation."""
    
    def test_reminder_event_key(self):
        """Test reminder event key generation."""
        event_id = "event_123"
        key = RedisKeyBuilder.get_reminder_event_key(event_id)
        expected = f"meta-glasses:reminder:event:{event_id}"
        assert key == expected
    
    def test_reminder_schedule_key(self):
        """Test reminder schedule key generation."""
        user_id = "12345"
        key = RedisKeyBuilder.get_reminder_schedule_key(user_id)
        expected = f"meta-glasses:reminder:schedule:{user_id}"
        assert key == expected
    
    def test_calendar_sync_key(self):
        """Test calendar sync key generation."""
        user_id = "12345"
        key = RedisKeyBuilder.get_calendar_sync_key(user_id)
        expected = f"meta-glasses:calendar:sync:{user_id}"
        assert key == expected


class TestStateKeys:
    """Test state and operation key generation."""
    
    def test_cancellation_state_key_default(self):
        """Test cancellation state key with default platform."""
        user_id = "12345"
        key = RedisKeyBuilder.get_cancellation_state_key(user_id)
        expected = f"meta-glasses:state:cancellation:wa:{user_id}"
        assert key == expected
    
    def test_cancellation_state_key_custom_platform(self):
        """Test cancellation state key with custom platform."""
        user_id = "12345"
        platform = "telegram"
        key = RedisKeyBuilder.get_cancellation_state_key(user_id, platform)
        expected = f"meta-glasses:state:cancellation:{platform}:{user_id}"
        assert key == expected
    
    def test_processing_state_key(self):
        """Test processing state key generation."""
        user_id = "12345"
        key = RedisKeyBuilder.get_processing_state_key(user_id)
        expected = f"meta-glasses:state:processing:{user_id}"
        assert key == expected
    
    def test_session_key(self):
        """Test session key generation."""
        session_id = "sess_abc123"
        key = RedisKeyBuilder.get_session_key(session_id)
        expected = f"meta-glasses:state:session:{session_id}"
        assert key == expected


class TestMetricsKeys:
    """Test metrics and analytics key generation."""
    
    def test_ai_requests_key(self):
        """Test AI requests key generation."""
        date = "2024-01-15"
        key = RedisKeyBuilder.get_ai_requests_key(date)
        expected = f"meta-glasses:metrics:ai_requests:{date}"
        assert key == expected
    
    def test_messages_key_daily(self):
        """Test daily messages key generation."""
        date = "2024-01-15"
        key = RedisKeyBuilder.get_messages_key(date)
        expected = f"meta-glasses:metrics:messages:{date}"
        assert key == expected
    
    def test_messages_key_hourly(self):
        """Test hourly messages key generation."""
        date = "2024-01-15"
        hour = "14"
        key = RedisKeyBuilder.get_messages_key(date, hour)
        expected = f"meta-glasses:metrics:messages:{date}-{hour}"
        assert key == expected
    
    def test_response_times_key(self):
        """Test response times key generation."""
        date = "2024-01-15"
        key = RedisKeyBuilder.get_response_times_key(date)
        expected = f"meta-glasses:metrics:response_times:{date}"
        assert key == expected
    
    def test_user_activity_key(self):
        """Test user activity key generation."""
        date = "2024-01-15"
        key = RedisKeyBuilder.get_user_activity_key(date)
        expected = f"meta-glasses:metrics:user_activity:{date}"
        assert key == expected


class TestMonitoringKeys:
    """Test monitoring key generation."""
    
    def test_redis_commands_key(self):
        """Test Redis commands monitoring key."""
        key = RedisKeyBuilder.get_redis_commands_key()
        expected = "meta-glasses:monitor:redis:commands"
        assert key == expected
    
    def test_redis_latency_key(self):
        """Test Redis latency monitoring key."""
        key = RedisKeyBuilder.get_redis_latency_key()
        expected = "meta-glasses:monitor:redis:latency"
        assert key == expected
    
    def test_health_check_key(self):
        """Test health check key generation."""
        component = "whatsapp_api"
        key = RedisKeyBuilder.get_health_check_key(component)
        expected = f"meta-glasses:monitor:health:{component}"
        assert key == expected


class TestPatternMatching:
    """Test pattern matching helpers."""
    
    def test_all_user_keys_pattern(self):
        """Test user keys pattern generation."""
        user_id = "12345"
        pattern = RedisKeyBuilder.get_all_user_keys_pattern(user_id)
        expected = f"meta-glasses:user:*:{user_id}"
        assert pattern == expected
    
    def test_all_cache_keys_pattern(self):
        """Test cache keys pattern generation."""
        pattern = RedisKeyBuilder.get_all_cache_keys_pattern()
        expected = "meta-glasses:cache:*"
        assert pattern == expected
    
    def test_all_reminder_keys_pattern(self):
        """Test reminder keys pattern generation."""
        pattern = RedisKeyBuilder.get_all_reminder_keys_pattern()
        expected = "meta-glasses:reminder:*"
        assert pattern == expected
    
    def test_all_metrics_keys_pattern(self):
        """Test metrics keys pattern generation."""
        pattern = RedisKeyBuilder.get_all_metrics_keys_pattern()
        expected = "meta-glasses:metrics:*"
        assert pattern == expected
    
    def test_all_monitoring_keys_pattern(self):
        """Test monitoring keys pattern generation."""
        pattern = RedisKeyBuilder.get_all_monitoring_keys_pattern()
        expected = "meta-glasses:monitor:*"
        assert pattern == expected


class TestLegacyKeys:
    """Test legacy key generation for migration."""
    
    def test_legacy_cache_key(self):
        """Test legacy cache key generation."""
        path = "test/path"
        key = RedisKeyBuilder.get_legacy_cache_key(path)
        
        encoded_path = base64.b64encode(path.encode('utf-8')).decode('utf-8')
        expected = f"josancamon:rayban-meta-glasses-api:{encoded_path}"
        assert key == expected
    
    def test_legacy_reminder_key(self):
        """Test legacy reminder key generation."""
        event_id = "event_123"
        key = RedisKeyBuilder.get_legacy_reminder_key(event_id)
        expected = f"josancamon:rayban-meta-glasses-api:reminder:{event_id}"
        assert key == expected
    
    def test_legacy_user_key(self):
        """Test legacy user key generation."""
        user_id = "12345"
        key_type = "conversation_history"
        key = RedisKeyBuilder.get_legacy_user_key(user_id, key_type)
        expected = f"josancamon:rayban-meta-glasses-api:{key_type}:{user_id}"
        assert key == expected


class TestConvenienceInstance:
    """Test the convenience instance."""
    
    def test_redis_keys_instance(self):
        """Test that redis_keys convenience instance works."""
        user_id = "12345"
        key1 = redis_keys.get_user_profile_key(user_id)
        key2 = RedisKeyBuilder.get_user_profile_key(user_id)
        assert key1 == key2


if __name__ == "__main__":
    pytest.main([__file__])