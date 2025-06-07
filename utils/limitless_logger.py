"""
Centralized logging configuration for Limitless integration.
Provides clean, structured logging with reduced noise.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from utils.limitless_config import limitless_config


class LimitlessLogger:
    """Custom logger for Limitless integration with smart batching and filtering."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._processing_batch = False
        self._batch_stats = {
            'total': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'memories': 0,
            'tasks': 0
        }
        self._processed_recordings = set()
        
    def start_batch(self, total_items: int):
        """Start batch processing mode."""
        self._processing_batch = True
        self._batch_stats = {
            'total': total_items,
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'memories': 0,
            'tasks': 0
        }
        self._processed_recordings.clear()
        self.logger.info(f"🚀 Starting batch processing of {total_items} recordings")
        
    def end_batch(self):
        """End batch processing and log summary."""
        if self._processing_batch:
            self.logger.info(
                f"✅ Batch complete: {self._batch_stats['processed']} processed, "
                f"{self._batch_stats['skipped']} skipped, {self._batch_stats['errors']} errors | "
                f"Created: {self._batch_stats['memories']} memories, {self._batch_stats['tasks']} tasks"
            )
            self._processing_batch = False
            
    def recording_skipped(self, recording_id: str):
        """Log a skipped recording (only once per batch)."""
        if self._processing_batch:
            self._batch_stats['skipped'] += 1
            # Only log if configured or first few skips
            if limitless_config.LOG_DUPLICATE_SKIPS or self._batch_stats['skipped'] <= 3:
                self.logger.debug(f"Recording {recording_id[:8]}... already processed")
        else:
            self.logger.info(f"Recording {recording_id} already processed, skipping")
            
    def recording_processed(self, recording_id: str, memories: int = 0, tasks: int = 0):
        """Log successful recording processing."""
        if self._processing_batch:
            self._batch_stats['processed'] += 1
            self._batch_stats['memories'] += memories
            self._batch_stats['tasks'] += tasks
            # Only log based on configuration or if items were created
            if (limitless_config.should_log_progress(self._batch_stats['processed']) or 
                memories > 0 or tasks > 0):
                self.logger.info(
                    f"📝 Progress: {self._batch_stats['processed']}/{self._batch_stats['total']} "
                    f"(+{memories} memories, +{tasks} tasks)"
                )
        else:
            self.logger.info(
                f"Recording {recording_id} processed: "
                f"{memories} memories, {tasks} tasks created"
            )
            
    def recording_error(self, recording_id: str, error: str):
        """Log recording processing error."""
        if self._processing_batch:
            self._batch_stats['errors'] += 1
        self.logger.error(f"Error processing {recording_id[:8]}...: {error}")
        
    def api_pagination(self, page: int, items: int, cursor: Optional[str] = None):
        """Log API pagination concisely."""
        if cursor:
            # Only show first 20 chars of cursor
            cursor_preview = cursor[:20] + "..." if len(cursor) > 20 else cursor
            self.logger.debug(f"Page {page}: {items} items (cursor: {cursor_preview})")
        else:
            self.logger.debug(f"Page {page}: {items} items")
            
    def sync_summary(self, start_time: datetime, end_time: datetime, total_fetched: int):
        """Log sync operation summary."""
        duration = (end_time - start_time).total_seconds()
        self.logger.info(
            f"📊 Sync summary: Fetched {total_fetched} recordings in {duration:.1f}s "
            f"({total_fetched/duration:.1f} recordings/s)"
        )
        
    def cache_update(self, cache_type: str, value: Any):
        """Log cache updates concisely."""
        self.logger.debug(f"Cache updated: {cache_type}={value}")
        
    def dashboard_request(self, endpoint: str, params: Optional[Dict] = None):
        """Log dashboard API requests concisely."""
        if params:
            self.logger.debug(f"Dashboard: {endpoint} {params}")
        else:
            self.logger.debug(f"Dashboard: {endpoint}")


# Singleton instances for each module
limitless_logger = LimitlessLogger("functionality.limitless")
limitless_api_logger = LimitlessLogger("utils.limitless_api")
limitless_routes_logger = LimitlessLogger("api.dashboard.limitless_routes")