"""
Redis Key Builder Utility

Centralized Redis key generation following the naming convention:
meta-glasses:{category}:{subcategory}:{identifier}

This utility ensures consistent key naming across the entire application
and makes it easy to update key patterns in the future.
"""

import base64
import hashlib
from datetime import datetime
from typing import Optional


class RedisKeyBuilder:
    """Centralized Redis key builder for consistent naming conventions."""
    
    # Base prefix for all keys
    BASE_PREFIX = "meta-glasses"
    
    # Category constants
    CACHE = "cache"
    USER = "user"
    REMINDER = "reminder"
    STATE = "state"
    METRICS = "metrics"
    MONITOR = "monitor"
    
    @classmethod
    def _build_key(cls, *parts: str) -> str:
        """Build a Redis key from parts, filtering out None/empty values."""
        filtered_parts = [cls.BASE_PREFIX] + [str(part) for part in parts if part]
        return ":".join(filtered_parts)
    
    @classmethod
    def _encode_path(cls, path: str) -> str:
        """Encode a path using base64 for safe Redis key usage."""
        return base64.b64encode(path.encode('utf-8')).decode('utf-8')
    
    @classmethod
    def _hash_content(cls, content: str) -> str:
        """Create a hash of content for cache keys."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
    
    # ====================
    # CACHE KEYS
    # ====================
    
    @classmethod
    def get_generic_cache_key(cls, path: str) -> str:
        """Generate key for generic application cache."""
        encoded_path = cls._encode_path(path)
        return cls._build_key(cls.CACHE, "generic", encoded_path)
    
    @classmethod
    def get_search_cache_key(cls, query: str) -> str:
        """Generate key for search result cache."""
        query_hash = cls._hash_content(query)
        return cls._build_key(cls.CACHE, "search", query_hash)
    
    @classmethod
    def get_api_cache_key(cls, endpoint: str, params: str = "") -> str:
        """Generate key for API response cache."""
        cache_content = f"{endpoint}:{params}"
        endpoint_hash = cls._hash_content(cache_content)
        return cls._build_key(cls.CACHE, "api", endpoint_hash)
    
    # ====================
    # USER DATA KEYS
    # ====================
    
    @classmethod
    def get_user_history_key(cls, user_id: str) -> str:
        """Generate key for user conversation history."""
        return cls._build_key(cls.USER, "history", user_id)
    
    @classmethod
    def get_user_profile_key(cls, user_id: str) -> str:
        """Generate key for user profile data."""
        return cls._build_key(cls.USER, "profile", user_id)
    
    @classmethod
    def get_user_context_key(cls, user_id: str) -> str:
        """Generate key for user conversation context."""
        return cls._build_key(cls.USER, "context", user_id)
    
    @classmethod
    def get_user_memory_key(cls, user_id: str, memory_id: str) -> str:
        """Generate key for individual user memory."""
        return cls._build_key(cls.USER, "memory", user_id, memory_id)
    
    @classmethod
    def get_user_memory_index_key(cls, user_id: str) -> str:
        """Generate key for user memory index."""
        return cls._build_key(cls.USER, "memory_index", user_id)
    
    # ====================
    # REMINDER & CALENDAR KEYS
    # ====================
    
    @classmethod
    def get_reminder_event_key(cls, event_id: str) -> str:
        """Generate key for calendar event reminder."""
        return cls._build_key(cls.REMINDER, "event", event_id)
    
    @classmethod
    def get_reminder_schedule_key(cls, user_id: str) -> str:
        """Generate key for user reminder schedule."""
        return cls._build_key(cls.REMINDER, "schedule", user_id)
    
    @classmethod
    def get_calendar_sync_key(cls, user_id: str) -> str:
        """Generate key for calendar sync status."""
        return cls._build_key("calendar", "sync", user_id)
    
    # ====================
    # STATE & OPERATION KEYS
    # ====================
    
    @classmethod
    def get_cancellation_state_key(cls, user_id: str, platform: str = "wa") -> str:
        """Generate key for cancellation state (WhatsApp, etc.)."""
        return cls._build_key(cls.STATE, "cancellation", platform, user_id)
    
    @classmethod
    def get_processing_state_key(cls, user_id: str) -> str:
        """Generate key for message processing state."""
        return cls._build_key(cls.STATE, "processing", user_id)
    
    @classmethod
    def get_session_key(cls, session_id: str) -> str:
        """Generate key for session data."""
        return cls._build_key(cls.STATE, "session", session_id)
    
    # ====================
    # METRICS & ANALYTICS KEYS
    # ====================
    
    @classmethod
    def get_ai_requests_key(cls, date: str) -> str:
        """Generate key for daily AI request metrics."""
        return cls._build_key(cls.METRICS, "ai_requests", date)
    
    @classmethod
    def get_messages_key(cls, date: str, hour: Optional[str] = None) -> str:
        """Generate key for message metrics (hourly or daily)."""
        if hour:
            return cls._build_key(cls.METRICS, "messages", f"{date}-{hour}")
        return cls._build_key(cls.METRICS, "messages", date)
    
    @classmethod
    def get_response_times_key(cls, date: str) -> str:
        """Generate key for response time tracking."""
        return cls._build_key(cls.METRICS, "response_times", date)
    
    @classmethod
    def get_user_activity_key(cls, date: str) -> str:
        """Generate key for daily user activity."""
        return cls._build_key(cls.METRICS, "user_activity", date)
    
    @classmethod
    def get_performance_latency_key(cls, date: str, operation_type: str) -> str:
        """Generate key for performance latency tracking by operation type."""
        return cls._build_key(cls.METRICS, "performance", "latency", date, operation_type.replace(" ", "_").lower())
    
    @classmethod
    def get_performance_count_key(cls, date: str, operation_type: str) -> str:
        """Generate key for performance count tracking by operation type."""
        return cls._build_key(cls.METRICS, "performance", "count", date, operation_type.replace(" ", "_").lower())
    
    # ====================
    # MONITORING KEYS
    # ====================
    
    @classmethod
    def get_redis_commands_key(cls) -> str:
        """Generate key for Redis command monitoring."""
        return cls._build_key(cls.MONITOR, "redis", "commands")
    
    @classmethod
    def get_redis_latency_key(cls) -> str:
        """Generate key for Redis latency monitoring."""
        return cls._build_key(cls.MONITOR, "redis", "latency")
    
    @classmethod
    def get_health_check_key(cls, component: str) -> str:
        """Generate key for component health check data."""
        return cls._build_key(cls.MONITOR, "health", component)
    
    # ====================
    # PATTERN MATCHING HELPERS
    # ====================
    
    @classmethod
    def get_all_user_keys_pattern(cls, user_id: str) -> str:
        """Get pattern to match all keys for a specific user."""
        return cls._build_key(cls.USER, "*", user_id)
    
    @classmethod
    def get_all_cache_keys_pattern(cls) -> str:
        """Get pattern to match all cache keys."""
        return cls._build_key(cls.CACHE, "*")
    
    @classmethod
    def get_all_reminder_keys_pattern(cls) -> str:
        """Get pattern to match all reminder keys."""
        return cls._build_key(cls.REMINDER, "*")
    
    @classmethod
    def get_all_metrics_keys_pattern(cls) -> str:
        """Get pattern to match all metrics keys."""
        return cls._build_key(cls.METRICS, "*")
    
    @classmethod
    def get_all_monitoring_keys_pattern(cls) -> str:
        """Get pattern to match all monitoring keys."""
        return cls._build_key(cls.MONITOR, "*")
    
    # ====================
    # LEGACY KEY SUPPORT (for migration)
    # ====================
    
    @classmethod
    def get_legacy_cache_key(cls, path: str) -> str:
        """Generate legacy cache key for migration purposes."""
        encoded_path = cls._encode_path(path)
        return f"josancamon:rayban-meta-glasses-api:{encoded_path}"
    
    @classmethod
    def get_legacy_reminder_key(cls, event_id: str) -> str:
        """Generate legacy reminder key for migration purposes."""
        return f"josancamon:rayban-meta-glasses-api:reminder:{event_id}"
    
    @classmethod
    def get_legacy_user_key(cls, user_id: str, key_type: str) -> str:
        """Generate legacy user key for migration purposes."""
        return f"josancamon:rayban-meta-glasses-api:{key_type}:{user_id}"


# Convenience instance for direct usage
redis_keys = RedisKeyBuilder()