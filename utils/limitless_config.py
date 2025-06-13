"""
Configuration settings for Limitless integration.
Centralized configuration for logging, batching, and performance tuning.
"""
import os
from typing import Optional


class LimitlessConfig:
    """Configuration for Limitless integration."""
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LIMITLESS_LOG_LEVEL", "INFO")  # INFO, DEBUG, WARNING, ERROR
    LOG_BATCH_PROGRESS_INTERVAL = 10  # Log progress every N recordings
    LOG_PAGINATION_IN_DEBUG = True  # Only log pagination in DEBUG mode
    LOG_DUPLICATE_SKIPS = False  # Log when duplicates are skipped
    LOG_API_RESPONSES = False  # Log raw API responses
    
    # Batch Processing Configuration
    BATCH_PROCESSING_DELAY = 2.0  # Seconds between processing recordings
    BATCH_SIZE_LIMIT = None  # Max recordings per sync (None = no limit)
    SHOW_BATCH_SUMMARY = True  # Show summary after batch processing
    
    # Cache Configuration
    PENDING_SYNC_CACHE_TTL = 300  # 5 minutes
    LIFELOG_CACHE_TTL = 86400 * 7  # 7 days
    PROCESSED_MARKER_TTL = 86400 * 30  # 30 days
    
    # API Configuration
    API_PAGE_SIZE = 10  # Max items per API request
    API_MAX_PAGES = 20  # Max pages to fetch (safety limit)
    API_PAGINATION_DELAY = 0.5  # Delay between pagination requests
    
    # Dashboard Configuration
    DASHBOARD_MAX_SEARCH_RESULTS = 20
    DASHBOARD_DEFAULT_SYNC_HOURS = 24  # Legacy - kept for compatibility
    DEFAULT_SYNC_MODE = "today"  # New default sync mode
    
    # Notification Configuration
    SEND_TASK_NOTIFICATIONS = True  # Send WhatsApp notifications for new tasks
    NOTIFICATION_BATCH_THRESHOLD = 5  # Send summary if more than N items created
    
    @classmethod
    def get_log_level(cls) -> str:
        """Get the configured log level."""
        return cls.LOG_LEVEL
    
    @classmethod
    def should_log_progress(cls, current: int) -> bool:
        """Check if progress should be logged for current item."""
        return current % cls.LOG_BATCH_PROGRESS_INTERVAL == 0
    
    @classmethod
    def get_sync_time_range(cls, hours: Optional[int] = None) -> int:
        """Get the time range for syncing in hours. Legacy method."""
        return hours or cls.DASHBOARD_DEFAULT_SYNC_HOURS
    
    @classmethod
    def get_default_sync_mode(cls) -> str:
        """Get the default sync mode."""
        return cls.DEFAULT_SYNC_MODE
    
    @classmethod
    def is_valid_sync_mode(cls, mode: str) -> bool:
        """Check if sync mode is valid."""
        valid_modes = {"today", "yesterday", "all"}
        return mode in valid_modes or mode.startswith("hours_")


# Singleton instance
limitless_config = LimitlessConfig()