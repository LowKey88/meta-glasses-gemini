"""
Limitless AI integration for syncing Pendant recordings with the assistant.
"""
import re
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import asyncio

from utils.limitless_api import LimitlessAPIClient
from utils.redis_utils import r as redis_client
from utils.memory_manager import MemoryManager
from utils.gemini import simple_prompt_request, limitless_extraction_request
from utils.whatsapp import send_whatsapp_threaded
from functionality.task import create_task, get_task_lists
from functionality.calendar import create_google_calendar_event
from utils.redis_key_builder import RedisKeyBuilder
from functionality.calendar import get_event_color
from utils.limitless_logger import limitless_logger
from utils.limitless_config import limitless_config

logger = logging.getLogger(__name__)

# Initialize clients
limitless_client = LimitlessAPIClient()
memory_manager = MemoryManager()


async def process_limitless_command(command: str, phone_number: str) -> str:
    """
    Process Limitless-related commands from WhatsApp.
    
    Commands:
    - sync limitless: Sync recent recordings
    - limitless today: Show today's recordings
    - limitless yesterday: Show yesterday's recordings
    - limitless search [query]: Search transcripts
    - limitless person [name]: Find discussions with person
    - limitless summary [date]: Get daily summary
    """
    command = command.lower().strip()
    
    # Remove 'limitless' prefix if present
    if command.startswith("limitless "):
        command = command[10:]
    elif command == "limitless":
        return await get_limitless_help()
        
    # Route to appropriate handler
    if command == "sync" or command == "sync limitless":
        return await sync_recent_lifelogs(phone_number, "today")  # Default to today
    elif command == "sync today":
        return await sync_recent_lifelogs(phone_number, "today")
    elif command == "sync yesterday":
        return await sync_recent_lifelogs(phone_number, "yesterday")
    elif command == "sync all":
        return await sync_recent_lifelogs(phone_number, "all")
    elif command.startswith("sync ") and command.split()[-1].isdigit():
        # Handle "sync 24" or "sync 48" for custom hours
        hours = command.split()[-1]
        return await sync_recent_lifelogs(phone_number, f"hours_{hours}")
    elif command == "force reprocess" or command == "reprocess":
        return await force_reprocess_recent_tasks(phone_number, "today")
    elif command == "sync pending" or command == "pending":
        return await process_pending_recordings(phone_number)
    elif command == "today":
        return await get_today_lifelogs(phone_number)
    elif command == "yesterday":
        return await get_yesterday_lifelogs(phone_number)
    elif command.startswith("search "):
        query = command[7:]
        return await search_lifelogs(query, phone_number)
    elif command.startswith("person "):
        person_name = command[7:]
        return await find_person_discussions(person_name, phone_number)
    elif command.startswith("summary"):
        # Extract date if provided
        parts = command.split()
        date_str = parts[1] if len(parts) > 1 else None
        return await get_daily_summary(date_str, phone_number)
    else:
        return await get_limitless_help()


async def get_limitless_help() -> str:
    """Return help text for Limitless commands."""
    return """🎙️ *Limitless Commands:*

*Sync Options:*
• *sync limitless* - Sync today's recordings (midnight to now)
• *limitless sync today* - Same as above
• *limitless sync yesterday* - Yesterday's full day
• *limitless sync all* - Complete historical sync
• *limitless sync 24* - Last 24 hours (legacy mode)
• *limitless sync pending* - Process missed/pending recordings

*Browse:*
• *limitless today* - Today's recordings
• *limitless yesterday* - Yesterday's recordings  
• *limitless search [query]* - Search transcripts
• *limitless person [name]* - Find discussions with person
• *limitless summary [date]* - Daily summary
• *limitless reprocess* - Force reprocess today's recordings

_Example: "limitless search project deadline"_"""


async def force_reprocess_recent_tasks(phone_number: str, sync_mode: str = "today") -> str:
    """
    Force reprocessing of recordings to fix task counting issues.
    Clears processed flags for recordings to ensure they get reprocessed.
    """
    try:
        logger.info(f"🔄 Force reprocessing tasks with mode: {sync_mode}")
        
        # Calculate time range using same logic as sync_recent_lifelogs
        start_time = None
        end_time = None
        
        if sync_mode == "today":
            end_time = datetime.now()
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        elif sync_mode == "yesterday":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = today - timedelta(days=1)
            end_time = today
        elif sync_mode.startswith("hours_"):
            try:
                hours = int(sync_mode.split("_")[1])
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
            except (ValueError, IndexError):
                end_time = datetime.now()
                start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default to today
            end_time = datetime.now()
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get recent recordings
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=start_time,
            end_time=end_time,
            timezone_str="Asia/Kuala_Lumpur",
            max_entries=None,
            include_markdown=False,
            include_headings=False
        )
        
        cleared_count = 0
        
        # Clear processed flags for recent recordings
        for log in lifelogs:
            log_id = log.get('id')
            if log_id:
                # Clear processed flag
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
                if redis_client.exists(processed_key):
                    redis_client.delete(processed_key)
                    cleared_count += 1
                
                # Clear AI task processed flag  
                ai_task_key = f"meta-glasses:limitless:ai_tasks_processed:{log_id}"
                if redis_client.exists(ai_task_key):
                    redis_client.delete(ai_task_key)
                
                # Clear natural language task flag
                task_key = RedisKeyBuilder.build_limitless_task_created_key(log_id)
                if redis_client.exists(task_key):
                    redis_client.delete(task_key)
        
        logger.info(f"🧹 Cleared processed flags for {cleared_count} recordings")
        
        # Now run normal sync to reprocess
        return await sync_recent_lifelogs(phone_number, sync_mode)
        
    except Exception as e:
        logger.error(f"Error in force reprocessing: {str(e)}")
        return f"❌ Error force reprocessing: {str(e)}"


def get_last_sync_timestamp(phone_number: str) -> Optional[datetime]:
    """Get the timestamp of the last successful sync."""
    try:
        # Get the latest processed recording timestamp
        latest_timestamp_key = f"meta-glasses:limitless:last_sync_timestamp:{phone_number}"
        timestamp_str = redis_client.get(latest_timestamp_key)
        
        if timestamp_str:
            if isinstance(timestamp_str, bytes):
                timestamp_str = timestamp_str.decode()
            return datetime.fromisoformat(timestamp_str)
        
        # Fallback: Find the latest processed recording from cache
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        latest_time = None
        
        for key in redis_client.scan_iter(match=pattern):
            data = redis_client.get(key)
            if data:
                try:
                    log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                    start_time_str = log_data.get('start_time') or log_data.get('created_at')
                    if start_time_str:
                        log_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        if not latest_time or log_time > latest_time:
                            latest_time = log_time
                except:
                    continue
        
        return latest_time
        
    except Exception as e:
        logger.error(f"Error getting last sync timestamp: {str(e)}")
        return None


def update_last_sync_timestamp(phone_number: str, timestamp: datetime):
    """Update the last successful sync timestamp."""
    try:
        latest_timestamp_key = f"meta-glasses:limitless:last_sync_timestamp:{phone_number}"
        redis_client.setex(
            latest_timestamp_key,
            86400 * 7,  # Keep for 7 days
            timestamp.isoformat()
        )
        logger.debug(f"Updated last sync timestamp: {timestamp}")
    except Exception as e:
        logger.error(f"Error updating last sync timestamp: {str(e)}")


async def sync_recent_lifelogs(phone_number: str, sync_mode: str = "today") -> str:
    """
    Efficient incremental sync that only fetches NEW recordings.
    
    Args:
        phone_number: User's phone number
        sync_mode: Sync mode - "today" (default), "yesterday", "hours_N", or "all"
    """
    try:
        logger.info(f"Starting INCREMENTAL Limitless sync for user {phone_number} with mode: {sync_mode}")
        
        # 🎯 KEY FIX: Get last successful sync timestamp for incremental sync
        last_sync_timestamp = get_last_sync_timestamp(phone_number)
        
        start_time = None
        end_time = None
        
        # Determine sync strategy based on mode and last sync timestamp
        if sync_mode == "today":
            # Today from midnight to now - use incremental if we have a recent sync
            end_time = datetime.now()
            today_start = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if last_sync_timestamp and last_sync_timestamp > today_start:
                # Incremental sync: only fetch recordings newer than last sync
                start_time = last_sync_timestamp
                logger.info(f"📈 Incremental sync for today: fetching recordings from {start_time} to {end_time}")
            else:
                # Full sync for today: from midnight to now
                start_time = today_start
                logger.info(f"🚀 Full sync for today: fetching recordings from {start_time} to {end_time}")
                
        elif sync_mode == "yesterday":
            # Yesterday full day
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = today - timedelta(days=1)
            end_time = today
            logger.info(f"📅 Yesterday sync: fetching recordings from {start_time} to {end_time}")
            
        elif sync_mode.startswith("hours_"):
            # Legacy hours-based sync - use incremental if possible
            try:
                hours = int(sync_mode.split("_")[1])
                end_time = datetime.now()
                hours_start = end_time - timedelta(hours=hours)
                
                if last_sync_timestamp and last_sync_timestamp > hours_start:
                    # Incremental sync: only fetch recordings newer than last sync
                    start_time = last_sync_timestamp
                    logger.info(f"📈 Incremental sync for last {hours}h: fetching recordings from {start_time} to {end_time}")
                else:
                    # Full sync for the hours period
                    start_time = hours_start
                    logger.info(f"🚀 Full sync for last {hours}h: fetching recordings from {start_time} to {end_time}")
            except (ValueError, IndexError):
                # Fallback to today if invalid hours format
                end_time = datetime.now()
                start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
                logger.warning(f"Invalid hours format '{sync_mode}', falling back to today")
                
        elif sync_mode == "all":
            # Force full historical sync - ignore incremental
            start_time = None
            end_time = None
            logger.info("🔥 Full historical sync: fetching ALL recordings")
            
        else:
            # Default to today for unknown modes - use incremental if possible
            end_time = datetime.now()
            today_start = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if last_sync_timestamp and last_sync_timestamp > today_start:
                start_time = last_sync_timestamp
                logger.info(f"📈 Incremental sync (default): fetching recordings from {start_time} to {end_time}")
            else:
                start_time = today_start
                logger.info(f"🚀 Full sync (default): fetching recordings from {start_time} to {end_time}")
        
        # Fetch only NEW recordings (not all recordings in time range)
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=start_time,
            end_time=end_time,
            timezone_str="Asia/Kuala_Lumpur",
            max_entries=None,
            include_markdown=True,
            include_headings=True
        )
        
        logger.info(f"📥 Fetched {len(lifelogs)} recordings from Limitless API")
        
        if not lifelogs:
            logger.info("✅ No new recordings found - sync complete")
            return "No new recordings found. All recordings are up to date."
        
        # 🎯 OPTIMIZATION: Pre-filter already processed recordings to minimize Redis checks
        unprocessed_logs = []
        processed_count_existing = 0
        
        for log in lifelogs:
            log_id = log.get('id', 'unknown')
            processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
            
            if not redis_client.exists(processed_key):
                unprocessed_logs.append(log)
            else:
                processed_count_existing += 1
        
        logger.info(f"📊 Pre-filtering: {len(unprocessed_logs)} new, {processed_count_existing} already processed")
        
        if not unprocessed_logs:
            logger.info("✅ All fetched recordings already processed")
            return "All recordings are already processed."
        
        # Process only the unprocessed recordings
        processed_count = 0
        memories_created = 0
        tasks_created = 0
        
        for i, log in enumerate(unprocessed_logs, 1):
            try:
                log_id = log.get('id', 'unknown')
                log_title = log.get('title', 'Untitled')
                
                logger.info(f"⚙️ Processing recording {i}/{len(unprocessed_logs)}: {log_title} (ID: {log_id})")
                
                # Process the recording
                results = await process_single_lifelog(log, phone_number)
                
                memories_created += results['memories_created']
                tasks_created += results['tasks_created']
                processed_count += 1
                
                # Mark as processed
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
                redis_client.setex(processed_key, 86400 * 30, "1")  # 30 days
                
                logger.info(f"✅ Processed {log_id}: {results['memories_created']} memories, {results['tasks_created']} tasks")
                
                # Rate limiting delay
                await asyncio.sleep(limitless_config.BATCH_PROCESSING_DELAY)
                
            except Exception as e:
                logger.error(f"❌ Error processing {log.get('id')}: {str(e)}")
                continue
        
        # 🎯 CRITICAL: Update last sync timestamp to latest processed recording
        if unprocessed_logs:
            latest_recording = max(unprocessed_logs, key=lambda x: x.get('start_time') or x.get('startTime') or x.get('createdAt') or '')
            latest_timestamp = latest_recording.get('start_time') or latest_recording.get('startTime') or latest_recording.get('createdAt')
            
            if latest_timestamp:
                # Convert to datetime and store
                if isinstance(latest_timestamp, str):
                    try:
                        latest_dt = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00')).replace(tzinfo=None)
                    except:
                        latest_dt = datetime.now()
                else:
                    latest_dt = latest_timestamp
                
                update_last_sync_timestamp(phone_number, latest_dt)
                logger.info(f"📌 Updated last sync timestamp to: {latest_dt}")
        
        # Update legacy sync timestamp for backward compatibility
        last_sync_key = RedisKeyBuilder.build_limitless_sync_key(phone_number)
        redis_client.set(last_sync_key, datetime.now(timezone.utc).isoformat())
        
        # Log efficiency summary
        total_fetched = len(lifelogs)
        efficiency_pct = (len(unprocessed_logs) / total_fetched * 100) if total_fetched > 0 else 0
        logger.info(f"🔄 Sync efficiency: {efficiency_pct:.1f}% ({len(unprocessed_logs)}/{total_fetched} fetched recordings needed processing)")
        
        # Store efficiency metrics for dashboard
        try:
            efficiency_key = f"meta-glasses:limitless:last_efficiency:{phone_number}"
            redis_client.setex(efficiency_key, 86400 * 7, str(efficiency_pct))  # Keep for 7 days
        except Exception as e:
            logger.error(f"Error storing efficiency metrics: {str(e)}")
        
        # Update pending sync cache
        try:
            pending_sync_key = "meta-glasses:limitless:pending_sync_cache"
            redis_client.setex(pending_sync_key, 300, "0")  # Set to 0 since we just processed everything
            logger.info(f"📊 Updated pending sync cache: 0 recordings pending")
        except Exception as e:
            logger.error(f"Error updating pending sync cache: {str(e)}")
        
        # Build response with efficiency info
        sync_type = "Incremental" if last_sync_timestamp and start_time == last_sync_timestamp else "Full"
        
        time_range_str = ""
        if start_time and end_time and hasattr(start_time, 'strftime') and hasattr(end_time, 'strftime'):
            start_str = start_time.strftime('%b %d, %I:%M %p')
            end_str = end_time.strftime('%I:%M %p')
            time_range_str = f"📅 Time Range: {start_str} - {end_str}\n"
        elif sync_mode == "all":
            time_range_str = "📅 Time Range: All recordings\n"
        
        response = f"""✅ *{sync_type} Sync Complete*

{time_range_str}📝 New recordings processed: {len(unprocessed_logs)}
🧠 Memories created: {memories_created}
✅ Tasks extracted: {tasks_created}
⏭️ Already processed: {processed_count_existing}

_Efficiency: Only fetched {len(lifelogs)} recordings instead of checking all recordings_"""
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error in incremental sync: {str(e)}")
        return f"❌ Error syncing Limitless recordings: {str(e)}"


async def force_full_sync(phone_number: str, hours: int = 24) -> str:
    """Force a full sync that ignores incremental timestamps - use sparingly."""
    
    try:
        logger.info(f"🔥 FORCE FULL SYNC requested for last {hours} hours")
        
        # Clear last sync timestamp to force full sync
        latest_timestamp_key = f"meta-glasses:limitless:last_sync_timestamp:{phone_number}"
        redis_client.delete(latest_timestamp_key)
        
        # Run full sync
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        logger.info(f"📅 Full sync: fetching ALL recordings from {start_time} to {end_time}")
        
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=start_time,
            end_time=end_time,
            timezone_str="Asia/Kuala_Lumpur",
            max_entries=None,
            include_markdown=True,
            include_headings=True
        )
        
        logger.info(f"📥 Full sync fetched {len(lifelogs)} recordings")
        
        # Process all recordings (will skip already processed ones)
        processed_count = 0
        skipped_count = 0
        memories_created = 0
        tasks_created = 0
        
        for i, log in enumerate(lifelogs, 1):
            try:
                log_id = log.get('id', 'unknown')
                log_title = log.get('title', 'Untitled')
                
                # Check if already processed
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
                if redis_client.exists(processed_key):
                    skipped_count += 1
                    continue
                    
                logger.info(f"⚙️ Force processing recording {i}/{len(lifelogs)}: {log_title} (ID: {log_id})")
                    
                # Process the Lifelog
                results = await process_single_lifelog(log, phone_number)
                
                memories_created += results['memories_created']
                tasks_created += results['tasks_created']
                processed_count += 1
                
                # Mark as processed
                redis_client.setex(processed_key, 86400 * 30, "1")  # 30 days
                
                # Rate limiting delay
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Error processing {log.get('id')}: {str(e)}")
                continue
        
        # Update timestamps for future incremental syncs
        if lifelogs:
            latest_recording = max(lifelogs, key=lambda x: x.get('start_time') or x.get('startTime') or x.get('createdAt') or '')
            latest_timestamp = latest_recording.get('start_time') or latest_recording.get('startTime') or latest_recording.get('createdAt')
            
            if latest_timestamp:
                if isinstance(latest_timestamp, str):
                    try:
                        latest_dt = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00')).replace(tzinfo=None)
                    except:
                        latest_dt = datetime.now()
                else:
                    latest_dt = latest_timestamp
                
                update_last_sync_timestamp(phone_number, latest_dt)
        
        return f"""✅ *Force Full Sync Complete*

📝 Total recordings checked: {len(lifelogs)}
⚙️ New recordings processed: {processed_count}
🧠 Memories created: {memories_created}
✅ Tasks extracted: {tasks_created}
⏭️ Already processed: {skipped_count}

_Incremental sync will now work efficiently for future syncs_"""
        
    except Exception as e:
        logger.error(f"❌ Error in force full sync: {str(e)}")
        return f"❌ Error in force full sync: {str(e)}"


async def process_pending_recordings(phone_number: str) -> str:
    """
    Detect and process recordings that were missed by incremental sync.
    This catches recordings with retroactive timestamps or out-of-order processing.
    """
    import time
    
    # ⏱️ START: Overall pending processing timing
    overall_start = time.time()
    
    try:
        logger.info(f"🔍 Checking for pending recordings that may have been missed")
        
        # ⏱️ TIMING: API fetch for all recordings
        api_fetch_start = time.time()
        
        # Use same time range as dashboard (today's window)
        end_time = datetime.now()
        start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Fetch today's recordings to detect missing ones
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=start_time,
            end_time=end_time,
            timezone_str="Asia/Kuala_Lumpur",
            max_entries=None,
            include_markdown=True,  # Include full content for processing
            include_headings=True
        )
        
        api_fetch_time = time.time() - api_fetch_start
        logger.info(f"📋 API fetch completed in {api_fetch_time:.1f}s - Retrieved {len(lifelogs)} recordings")
        
        # ⏱️ TIMING: Gap detection
        gap_detection_start = time.time()
        
        # Find unprocessed recordings
        pending_logs = []
        for log in lifelogs:
            log_id = log.get('id', 'unknown')
            processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
            if not redis_client.exists(processed_key):
                pending_logs.append(log)
        
        gap_detection_time = time.time() - gap_detection_start
        logger.info(f"🔍 Gap detection completed in {gap_detection_time:.1f}s - Found {len(pending_logs)} pending")
        
        if not pending_logs:
            total_time = time.time() - overall_start
            logger.info(f"✅ No pending recordings found in {total_time:.1f}s - all recordings are processed")
            # Update cache to reflect 0 pending
            pending_sync_key = "meta-glasses:limitless:pending_sync_cache"
            redis_client.setex(pending_sync_key, 300, "0")
            return "No pending recordings found"
        
        logger.info(f"🔄 Processing {len(pending_logs)} pending recordings (estimated time: {len(pending_logs) * 30}s)")
        
        # Process the pending recordings with detailed timing
        processed_count = 0
        memories_created = 0
        tasks_created = 0
        processing_times = []
        
        for i, log in enumerate(pending_logs, 1):
            try:
                # ⏱️ TIMING: Individual recording processing
                record_start = time.time()
                
                log_id = log.get('id', 'unknown')
                log_title = log.get('title', 'Untitled')
                
                logger.info(f"⚙️ Processing pending recording {i}/{len(pending_logs)}: {log_title[:30]}... (ID: {log_id[:8]}...)")
                
                # Process the recording
                results = await process_single_lifelog(log, phone_number)
                
                record_time = time.time() - record_start
                processing_times.append(record_time)
                
                memories_created += results['memories_created']
                tasks_created += results['tasks_created']
                processed_count += 1
                
                # Mark as processed
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
                redis_client.setex(processed_key, 86400 * 30, "1")  # 30 days
                
                # Calculate remaining time estimate
                avg_time = sum(processing_times) / len(processing_times)
                remaining_count = len(pending_logs) - i
                estimated_remaining = remaining_count * avg_time
                
                logger.info(f"✅ Completed {i}/{len(pending_logs)} in {record_time:.1f}s (avg: {avg_time:.1f}s, remaining: ~{estimated_remaining:.0f}s)")
                
                # Rate limiting delay
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Error processing pending recording {log.get('id')}: {str(e)}")
                continue
        
        # Update pending sync cache to 0 since we processed everything
        pending_sync_key = "meta-glasses:limitless:pending_sync_cache"
        redis_client.setex(pending_sync_key, 300, "0")
        
        # ⏱️ FINAL: Overall processing summary
        total_time = time.time() - overall_start
        
        if processing_times:
            avg_record_time = sum(processing_times) / len(processing_times)
            min_record_time = min(processing_times)
            max_record_time = max(processing_times)
            
            logger.info(f"📊 PENDING PROCESSING COMPLETE in {total_time:.1f}s:")
            logger.info(f"├─ 📡 API fetch: {api_fetch_time:.1f}s ({api_fetch_time/total_time*100:.1f}%)")
            logger.info(f"├─ 🔍 Gap detection: {gap_detection_time:.1f}s ({gap_detection_time/total_time*100:.1f}%)")
            logger.info(f"├─ 🔄 Records processing: {total_time - api_fetch_time - gap_detection_time:.1f}s ({(total_time - api_fetch_time - gap_detection_time)/total_time*100:.1f}%)")
            logger.info(f"├─ 📈 Records processed: {processed_count}/{len(pending_logs)}")
            logger.info(f"├─ ⏱️ Average per record: {avg_record_time:.1f}s (min: {min_record_time:.1f}s, max: {max_record_time:.1f}s)")
            logger.info(f"└─ 📝 Created: {memories_created} memories, {tasks_created} tasks")
        
        result_msg = f"✅ Processed {processed_count} pending recordings in {total_time:.1f}s: {memories_created} memories, {tasks_created} tasks created"
        logger.info(result_msg)
        return result_msg
        
    except Exception as e:
        total_time = time.time() - overall_start if 'overall_start' in locals() else 0
        logger.error(f"❌ Error in process_pending_recordings after {total_time:.1f}s: {str(e)}")
        return f"❌ Error processing pending recordings: {str(e)}"


async def process_single_lifelog(log: Dict, phone_number: str) -> Dict[str, int]:
    """
    Process a single Lifelog entry to extract memories and tasks.
    Enhanced with speaker identification and robust fallbacks.
    
    Returns:
        Dict with counts of created items
    """
    import time
    
    # ⏱️ START: Overall processing timing
    processing_start_time = time.time()
    log_id = log.get('id', 'unknown')
    title = log.get('title', 'Untitled Recording')
    
    results = {
        'memories_created': 0,
        'tasks_created': 0,
        'events_created': 0
    }
    
    # Performance tracking
    timing_data = {}
    
    try:
        logger.info(f"📊 Processing recording {log_id[:8]}... - '{title[:50]}{'...' if len(title) > 50 else ''}'")
        
        # Extract basic info
        
        # ⏱️ TIMING: Speaker identification
        speaker_start = time.time()
        
        # ✅ NEW: Extract speakers from Limitless API data with fallbacks
        # Pass phone_number in log metadata for context generation
        log['_phone_number'] = phone_number
        speakers_identified = extract_speakers_from_contents(log)
        
        timing_data['speaker_identification'] = time.time() - speaker_start
        logger.info(f"🎭 Speaker identification: {timing_data['speaker_identification']:.1f}s - Found {len(speakers_identified)} speakers")
        
        # Extract transcript from contents array with speaker attribution
        transcript = ''
        contents = log.get('contents', [])
        if contents and len(contents) > 0:
            # Get speaker mapping from previous extraction
            speaker_id_mapping = log.get('_speaker_mapping', {})
            
            # Build transcript with speaker attribution using Speaker N names
            transcript_parts = []
            for content in contents:
                speaker_name = content.get('speakerName', '').strip()
                speaker_id = content.get('speakerIdentifier', '').strip()
                content_text = content.get('content', '').strip()
                
                if content_text:  # Only add non-empty content
                    # Determine the speaker label - NEVER use "Unknown"
                    speaker_label = None
                    
                    if speaker_id == 'user':
                        speaker_label = "You"
                    elif speaker_name and speaker_name.lower() not in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker', '']:
                        # Valid speaker name from API
                        speaker_label = speaker_name
                    elif speaker_id and speaker_id in speaker_id_mapping:
                        # Use mapped Speaker N name for problematic speakers
                        speaker_label = speaker_id_mapping[speaker_id]
                    elif speaker_id:
                        # Unmapped speaker ID - assign next available Speaker N number
                        # Find the highest existing Speaker N in mapping
                        existing_numbers = []
                        for mapped_name in speaker_id_mapping.values():
                            if mapped_name.startswith('Speaker '):
                                try:
                                    num = int(mapped_name.split(' ')[1])
                                    existing_numbers.append(num)
                                except (IndexError, ValueError):
                                    pass
                        next_speaker_num = max(existing_numbers) + 1 if existing_numbers else 0
                        speaker_label = f"Speaker {next_speaker_num}"
                        speaker_id_mapping[speaker_id] = speaker_label  # Cache for consistency
                        logger.debug(f"Assigned unmapped speaker ID '{speaker_id}' to '{speaker_label}'")
                    else:
                        # No speaker info at all - assign next available Speaker N number
                        existing_numbers = []
                        for mapped_name in speaker_id_mapping.values():
                            if mapped_name.startswith('Speaker '):
                                try:
                                    num = int(mapped_name.split(' ')[1])
                                    existing_numbers.append(num)
                                except (IndexError, ValueError):
                                    pass
                        next_speaker_num = max(existing_numbers) + 1 if existing_numbers else 0
                        speaker_label = f"Speaker {next_speaker_num}"
                    
                    transcript_parts.append(f"{speaker_label}: {content_text}")
            
            transcript = '\n'.join(transcript_parts)
        
        # Fallback: try to get transcript from first content if speaker attribution fails
        if not transcript and contents and len(contents) > 0:
            transcript = contents[0].get('content', '')
            logger.debug(f"Using fallback transcript for {log_id[:8]}...")
            
        summary = log.get('summary', '')
        
        # Try different timestamp field names from API response
        start_time = (log.get('start_time') or 
                     log.get('startTime') or 
                     log.get('createdAt') or 
                     log.get('created_at'))
        end_time = (log.get('end_time') or 
                   log.get('endTime') or 
                   log.get('updatedAt') or 
                   log.get('updated_at'))
        
        # Always cache the recording, even if no transcript
        # Process transcript only if available
        has_transcript = bool(transcript and transcript.strip())
        
        # Initialize extracted data structure
        extracted = {
            'facts': [],
            'tasks': [],
            'events': [],
            'people': [],
            'speakers': speakers_identified  # ✅ NEW: Include speaker info
        }
        
        # Initialize natural tasks data
        natural_tasks_data = []
        
        # Only process transcript if available
        if has_transcript:
            # OPTIMIZATION: Skip separate natural language task extraction
            # Tasks are now extracted in the main AI call to reduce API calls from 2 to 1
            natural_tasks_created = 0
            timing_data['natural_language_tasks'] = 0.0
            
            # ⏱️ TIMING: Combined Gemini AI extraction (includes natural language tasks)
            gemini_start = time.time()
            
            # ✅ ENHANCED: Use speaker-aware Gemini prompt with fallback
            extraction_prompt = get_enhanced_extraction_prompt(title, summary, transcript)

            response = limitless_extraction_request(extraction_prompt, phone_number)
            
            timing_data['gemini_extraction'] = time.time() - gemini_start
            logger.info(f"🤖 Combined AI extraction (facts, tasks, events): {timing_data['gemini_extraction']:.1f}s - Response length: {len(response)} chars")
            
            # Parse the response
            try:
                # Clean and extract JSON from response
                cleaned_response = response.strip()
                
                # Handle markdown-wrapped JSON
                if "```json" in cleaned_response:
                    json_match = re.search(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                    if json_match:
                        cleaned_response = json_match.group(1).strip()
                elif "```" in cleaned_response:
                    json_match = re.search(r'```\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                    if json_match:
                        cleaned_response = json_match.group(1).strip()
                
                # Try to find JSON object if no code blocks
                if not cleaned_response.startswith('{'):
                    json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                    if json_match:
                        cleaned_response = json_match.group(0)
                    else:
                        raise json.JSONDecodeError("No JSON object found in response", cleaned_response, 0)
                
                # Additional cleaning for common issues
                cleaned_response = cleaned_response.replace('\n', ' ')  # Remove newlines that might break parsing
                cleaned_response = re.sub(r',\s*}', '}', cleaned_response)  # Remove trailing commas
                cleaned_response = re.sub(r',\s*]', ']', cleaned_response)  # Remove trailing commas in arrays
                        
                extracted_ai = json.loads(cleaned_response)
                
                # ✅ ENHANCED: Merge AI extraction with speaker data
                extracted['facts'] = extracted_ai.get('facts', [])
                
                # Process tasks with proper source attribution
                ai_tasks = extracted_ai.get('tasks', [])
                for task in ai_tasks:
                    if isinstance(task, dict):
                        # If task already has source from AI, keep it; otherwise mark as ai_extracted
                        if 'source' not in task:
                            task['source'] = 'ai_extracted'
                        # Count natural language tasks
                        if task.get('source') == 'natural_language':
                            natural_tasks_created += 1
                        
                extracted['tasks'] = ai_tasks
                extracted['events'] = extracted_ai.get('events', [])
                
                # Combine AI-extracted people with API speakers
                all_people = []
                
                # Get speaker mapping for standardization
                speaker_id_mapping = log.get('_speaker_mapping', {})
                
                # Add speakers identified from API first (these have correct Speaker N names)
                for speaker in speakers_identified:
                    all_people.append({
                        'name': speaker['name'],
                        'context': speaker['context'],
                        'is_speaker': True,
                        'role': speaker['role']
                    })
                
                # Add AI-extracted people, but filter out and fix any inconsistent naming
                ai_people = extracted_ai.get('people', [])
                existing_names = [p.get('name', '').lower() for p in all_people]
                
                for person in ai_people:
                    person_name = person.get('name', '')
                    
                    # Skip if we already have this person from API speakers
                    if person_name.lower() in existing_names:
                        continue
                    
                    # CRITICAL FIX: Replace any "Unknown" speakers with proper Speaker N naming
                    if person_name.lower() in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker']:
                        # Convert to proper Speaker N naming using current counter
                        current_speaker_numbers = []
                        for existing_person in all_people:
                            existing_name = existing_person.get('name', '')
                            if existing_name.startswith('Speaker ') and existing_person.get('is_speaker'):
                                try:
                                    num = int(existing_name.split(' ')[1])
                                    current_speaker_numbers.append(num)
                                except (IndexError, ValueError):
                                    pass
                        
                        # Find next available Speaker N number
                        next_speaker_number = max(current_speaker_numbers) + 1 if current_speaker_numbers else 0
                        person['name'] = f'Speaker {next_speaker_number}'
                        person['context'] = 'Unrecognized speaker in conversation'
                        person['is_speaker'] = True
                        logger.warning(f"AI generated Unknown speaker, converted to 'Speaker {next_speaker_number}' for {log_id[:8]}...")
                    
                    # Add valid AI-extracted people (named individuals)
                    if person_name and len(person_name.strip()) > 0:
                        all_people.append(person)
                
                extracted['people'] = all_people
                
                # ✅ POST-PROCESSING CLEANUP: Standardize any remaining inconsistent speaker names
                standardized_people = []
                unknown_speaker_counter = 0
                
                for person in extracted['people']:
                    person_name = person.get('name', '')
                    
                    # Fix any "Unknown" speakers that might come from cached data or AI extraction
                    if person_name.lower() in ['unknown', 'unknown speaker'] and person.get('is_speaker'):
                        # Replace with proper Speaker N naming
                        new_speaker_name = f"Speaker {unknown_speaker_counter}"
                        person['name'] = new_speaker_name
                        person['context'] = 'Unrecognized speaker in conversation'
                        logger.info(f"Standardized 'Unknown' speaker to '{new_speaker_name}' for {log_id[:8]}...")
                        unknown_speaker_counter += 1
                    
                    standardized_people.append(person)
                
                extracted['people'] = standardized_people
                
                # ✅ ENHANCED FALLBACK: Ensure tasks have attribution
                for task in extracted.get('tasks', []):
                    if not task.get('assigned_to'):
                        task['assigned_to'] = 'You'  # Default to user
                    if not task.get('assigned_by'):
                        task['assigned_by'] = 'You'  # Default to user
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response for Lifelog {log_id}")
                logger.error(f"JSON Decode Error: {str(e)}")
                logger.error(f"Raw Gemini response (first 500 chars): {response[:500]}")
                logger.debug(f"Full Gemini response for {log_id[:8]}: {response}")
                # Continue with speaker data only
                extracted['people'] = speakers_identified
            
            # ✅ ENHANCED FALLBACK: Always ensure we have at least the primary user in people list
            if not extracted.get('people'):
                logger.debug(f"No people extracted for {log_id[:8]}..., adding user")
                extracted['people'] = [{
                    'name': 'You',
                    'context': 'Primary user (default)',
                    'is_speaker': True,
                    'role': 'primary_user'
                }]
                
            # ⏱️ TIMING: Memory creation
            memory_start = time.time()
            
            # Create consolidated memory for this recording
            memory_created = create_consolidated_recording_memory(
                log_id=log_id,
                title=title,
                extracted=extracted,
                phone_number=phone_number,
                transcript_length=len(transcript) if transcript else 0
            )
            
            if memory_created:
                results['memories_created'] += 1
            
            timing_data['memory_creation'] = time.time() - memory_start
            logger.info(f"💾 Memory creation: {timing_data['memory_creation']:.1f}s - Created {results['memories_created']} memories")
                        
            # ⏱️ TIMING: Google Tasks creation
            tasks_start = time.time()
            tasks_created_count = 0
            
            # ✅ ENHANCED: Create tasks with speaker attribution and success validation
            validated_tasks = []  # Track only successfully created tasks
            
            # Check if AI tasks were already processed for this log
            ai_task_key = f"meta-glasses:limitless:ai_tasks_processed:{log_id}"
            ai_tasks_already_processed = redis_client.exists(ai_task_key)
            
            if not ai_tasks_already_processed:
                for task in extracted.get('tasks', []):
                    if task.get('description'):
                        # Create Google Task with enhanced metadata
                        task_title = task['description']
                        task_notes = f"From Limitless recording: {title}"
                        
                        # ✅ NEW: Add speaker attribution to task notes
                        if task.get('assigned_to'):
                            task_notes += f"\nAssigned to: {task['assigned_to']}"
                        if task.get('assigned_by'):
                            task_notes += f"\nMentioned by: {task['assigned_by']}"
                        
                        task_data = {
                            'title': task_title,
                            'notes': task_notes
                        }
                        
                        if task.get('due_date'):
                            try:
                                due = datetime.strptime(task['due_date'], '%Y-%m-%d')
                                task_data['due'] = due.isoformat() + 'Z'
                            except:
                                pass
                                
                        # ⏱️ Individual task creation timing
                        task_creation_start = time.time()
                        success = create_task_from_limitless(task_data, phone_number)
                        task_creation_time = time.time() - task_creation_start
                        
                        if success:
                            results['tasks_created'] += 1
                            tasks_created_count += 1
                            # FIXED: Only store successfully created tasks
                            task_with_success = task.copy()
                            task_with_success['created_successfully'] = True
                            task_with_success['google_task_created'] = True
                            task_with_success['source'] = 'ai_extracted'
                            validated_tasks.append(task_with_success)
                            logger.debug(f"✅ Created task '{task_title[:30]}...' in {task_creation_time:.1f}s")
                        else:
                            # Mark as failed but still log for debugging
                            logger.warning(f"❌ Failed to create Google Task: {task_title} ({task_creation_time:.1f}s)")
                            # Don't add to validated_tasks - this excludes it from counts
                
                # Mark AI tasks as processed to prevent duplicate creation
                redis_client.setex(ai_task_key, 86400 * 7, "1")  # 7 days TTL
            else:
                logger.debug(f"AI tasks already processed for {log_id[:8]}..., skipping task creation")
                # Preserve existing successful tasks from cache (both AI and natural language)
                for task in extracted.get('tasks', []):
                    if isinstance(task, dict) and task.get('created_successfully') is True:
                        # Include both ai_extracted and natural_language tasks
                        if task.get('source') in ['ai_extracted', 'natural_language']:
                            validated_tasks.append(task)
                        
            # OPTIMIZATION: Natural language tasks are now included in AI extraction
            # No need to merge separately as they're already in extracted['tasks']
            
            # CRITICAL FIX: Also preserve natural language tasks from previous cache
            # This handles cases where natural language tasks were skipped due to deduplication
            for task in extracted.get('tasks', []):
                if isinstance(task, dict) and task.get('source') == 'natural_language':
                    # Only add if not already in validated_tasks
                    task_desc = task.get('description', '')
                    if not any(t.get('description') == task_desc for t in validated_tasks):
                        validated_tasks.append(task)
            
            # Update extracted data with only successful tasks
            extracted['tasks'] = validated_tasks
            
            # ⏱️ Complete tasks timing
            timing_data['tasks_creation'] = time.time() - tasks_start
            logger.info(f"✅ Google Tasks creation: {timing_data['tasks_creation']:.1f}s - Created {tasks_created_count} tasks")
            
            # DIAGNOSTIC: Log final task count for this recording
            if validated_tasks:
                task_sources = [t.get('source', 'unknown') for t in validated_tasks]
                logger.debug(f"Lifelog {log_id[:8]}... final task count: {len(validated_tasks)} "
                           f"(sources: {task_sources})")
                        
            # People are now included in the consolidated memory created above
            # No separate people memories needed
        else:
            # ✅ FALLBACK: Even without transcript, ensure user appears in people
            extracted['people'] = speakers_identified if speakers_identified else [{
                'name': 'You',
                'context': 'Primary user (no transcript)',
                'is_speaker': True,
                'role': 'primary_user'
            }]
                
        # ✅ FINAL VALIDATION: Ensure no "Unknown" speakers slip through
        extracted = validate_speaker_names(extracted, log_id)
        
        # Cache the processed Lifelog with enhanced data
        cache_key = RedisKeyBuilder.build_limitless_lifelog_key(log_id)
        cache_data = {
            'id': log_id,
            'title': title,
            'summary': summary,
            'start_time': start_time,
            'end_time': end_time,
            'created_at': log.get('createdAt') or log.get('created_at'),
            'extracted': extracted,  # Now includes speaker info and fallbacks
            'speaker_mapping': log.get('_speaker_mapping', {}),  # Store Speaker N mapping
            'processed_at': datetime.now().isoformat()
        }
        
        # ⏱️ TIMING: Redis caching
        cache_start = time.time()
        
        logger.info(f"Caching Lifelog {log_id} with start_time: {start_time} and {len(speakers_identified)} speakers to key: {cache_key}")
        redis_client.setex(
            cache_key,
            86400 * 7,  # Cache for 7 days
            json.dumps(cache_data)
        )
        
        timing_data['redis_caching'] = time.time() - cache_start
        
        # ⏱️ FINAL: Overall processing summary
        total_time = time.time() - processing_start_time
        timing_data['total_processing'] = total_time
        
        # Log detailed timing breakdown
        logger.info(f"📊 COMPLETED recording {log_id[:8]}... in {total_time:.1f}s:")
        logger.info(f"├─ 🎭 Speaker identification: {timing_data.get('speaker_identification', 0):.1f}s ({timing_data.get('speaker_identification', 0)/total_time*100:.1f}%)")
        
        if has_transcript:
            logger.info(f"├─ 🤖 Combined AI extraction: {timing_data.get('gemini_extraction', 0):.1f}s ({timing_data.get('gemini_extraction', 0)/total_time*100:.1f}%)")
            logger.info(f"├─ 💾 Memory creation: {timing_data.get('memory_creation', 0):.1f}s ({timing_data.get('memory_creation', 0)/total_time*100:.1f}%)")
            logger.info(f"├─ ✅ Tasks creation: {timing_data.get('tasks_creation', 0):.1f}s ({timing_data.get('tasks_creation', 0)/total_time*100:.1f}%)")
        
        logger.info(f"├─ 💾 Redis caching: {timing_data.get('redis_caching', 0):.1f}s ({timing_data.get('redis_caching', 0)/total_time*100:.1f}%)")
        logger.info(f"└─ 📈 Created: {results['memories_created']} memories, {results['tasks_created']} tasks")
        
        # Store performance data in Redis for dashboard monitoring
        performance_key = f"meta-glasses:limitless:performance:{log_id}"
        performance_data = {
            'log_id': log_id,
            'title': title[:50],
            'total_time': total_time,
            'timing_breakdown': timing_data,
            'results': results,
            'processed_at': datetime.now().isoformat(),
            'has_transcript': has_transcript,
            'transcript_length': len(transcript) if has_transcript else 0
        }
        redis_client.setex(performance_key, 3600, json.dumps(performance_data))  # 1 hour TTL
        
    except Exception as e:
        total_time = time.time() - processing_start_time
        logger.error(f"❌ Error processing Lifelog {log.get('id', 'unknown')[:8]}... after {total_time:.1f}s: {str(e)}")
        
    return results


def validate_speaker_names(extracted_data: Dict, log_id: str = "unknown") -> Dict:
    """
    Final validation to ensure no "Unknown" speakers exist in the data.
    This is the last line of defense against any remaining Unknown speakers.
    """
    if not isinstance(extracted_data, dict):
        return extracted_data
    
    people = extracted_data.get('people', [])
    if not people:
        return extracted_data
    
    # Get all existing Speaker N numbers
    existing_speaker_numbers = set()
    for person in people:
        person_name = person.get('name', '')
        if person_name.startswith('Speaker ') and person.get('is_speaker'):
            try:
                num = int(person_name.split(' ')[1])
                existing_speaker_numbers.add(num)
            except (IndexError, ValueError):
                pass
    
    # Find any remaining problematic speakers and fix them
    next_speaker_number = max(existing_speaker_numbers) + 1 if existing_speaker_numbers else 0
    
    for person in people:
        person_name = person.get('name', '')
        
        # Check for any remaining Unknown speakers
        if (person_name.lower() in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker', ''] or
            not person_name or person_name.isspace()):
            
            if person.get('is_speaker'):
                # Replace with proper Speaker N naming
                person['name'] = f'Speaker {next_speaker_number}'
                person['context'] = 'Unrecognized speaker in conversation'
                logger.error(f"🚨 CRITICAL: Found {person_name or 'empty'} speaker in final validation for {log_id[:8]}..., fixed to Speaker {next_speaker_number}")
                next_speaker_number += 1
            else:
                # For non-speakers, we can be more lenient but still log
                logger.warning(f"Found empty/unknown non-speaker for {log_id[:8]}...: {person}")
    
    return extracted_data


def standardize_cached_speakers(extracted_data: Dict) -> Dict:
    """
    Standardize speaker names in cached data to ensure consistency.
    Converts any "Unknown" speakers to proper "Speaker N" naming.
    """
    if not isinstance(extracted_data, dict):
        return extracted_data
    
    people = extracted_data.get('people', [])
    if not people:
        return extracted_data
    
    unknown_speaker_counter = 0
    # Count existing Speaker N names to continue numbering
    for person in people:
        person_name = person.get('name', '')
        if person_name.startswith('Speaker ') and person.get('is_speaker'):
            try:
                speaker_num = int(person_name.split(' ')[1])
                unknown_speaker_counter = max(unknown_speaker_counter, speaker_num + 1)
            except (IndexError, ValueError):
                pass
    
    # Fix any "Unknown" speakers with more comprehensive detection
    for person in people:
        person_name = person.get('name', '')
        if (person_name.lower() in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker', ''] and 
            person.get('is_speaker')):
            new_speaker_name = f"Speaker {unknown_speaker_counter}"
            person['name'] = new_speaker_name
            person['context'] = 'Unrecognized speaker in conversation'
            logger.info(f"Standardized cached '{person_name or 'empty'}' speaker to '{new_speaker_name}'")
            unknown_speaker_counter += 1
        # Also fix any malformed Speaker N names
        elif person_name.startswith('Speaker ') and person.get('is_speaker'):
            try:
                # Validate the Speaker N format
                parts = person_name.split(' ')
                if len(parts) != 2 or not parts[1].isdigit():
                    # Fix malformed Speaker N name
                    new_speaker_name = f"Speaker {unknown_speaker_counter}"
                    person['name'] = new_speaker_name
                    logger.info(f"Fixed malformed Speaker name '{person_name}' to '{new_speaker_name}'")
                    unknown_speaker_counter += 1
            except (IndexError, ValueError):
                # Fix invalid Speaker N name
                new_speaker_name = f"Speaker {unknown_speaker_counter}"
                person['name'] = new_speaker_name
                logger.info(f"Fixed invalid Speaker name '{person_name}' to '{new_speaker_name}'")
                unknown_speaker_counter += 1
    
    return extracted_data


def determine_memory_type(content: str, facts: List, people: List, tasks: List) -> str:
    """
    Determine the appropriate memory type based on content and extracted data.
    Returns one of the standard memory types instead of 'recording_summary'.
    """
    content_lower = content.lower()
    
    # Check for tasks/reminders
    if tasks or any(keyword in content_lower for keyword in ['task', 'reminder', 'need to', 'should', 'must']):
        return 'note'  # Use 'note' for task-related content
    
    # Check for people/relationships
    if people or any(keyword in content_lower for keyword in ['involves', 'with', 'family', 'friend']):
        return 'relationship'
    
    # Check for personal information patterns
    if any(keyword in content_lower for keyword in ['house', 'home', 'address', 'phone', 'email']):
        return 'personal_info'
    
    # Check for routine/schedule
    if any(keyword in content_lower for keyword in ['daily', 'regular', 'schedule', 'routine', 'every']):
        return 'routine'
    
    # Check for preferences
    if any(keyword in content_lower for keyword in ['like', 'prefer', 'favorite', 'enjoy', 'hate', 'dislike']):
        return 'preference'
    
    # Check for important dates/events
    if any(keyword in content_lower for keyword in ['birthday', 'anniversary', 'appointment', 'meeting', 'event']):
        return 'important_date'
    
    # Default to 'fact' for general information
    return 'fact'



def create_consolidated_recording_memory(
    log_id: str, 
    title: str, 
    extracted: Dict, 
    phone_number: str,
    transcript_length: int = 0
) -> bool:
    """
    Create a single consolidated memory per recording instead of multiple memories.
    Combines facts, people, and key information into one comprehensive memory.
    
    Returns True if memory was created, False if skipped.
    """
    try:
        # OPTIMIZATION: Fast duplicate check using Redis key pattern instead of loading all memories
        limitless_memory_key = f"meta-glasses:limitless:memory_created:{log_id}"
        if redis_client.exists(limitless_memory_key):
            logger.debug(f"Memory already exists for recording {log_id[:8]}...")
            return False
        
        # Check quality thresholds
        facts = extracted.get('facts', [])
        people = extracted.get('people', [])
        tasks = extracted.get('tasks', [])
        
        # Enhanced quality filtering
        # Skip very short recordings with no meaningful content
        if transcript_length < 100 and not facts and not people and not tasks:
            logger.debug(f"Skipping low-quality recording {log_id[:8]}... (no meaningful content)")
            return False
        
        # Skip recordings with generic or low-quality titles
        generic_titles = [
            'a brief, unclear exchange', 'disjointed utterances', 'navigation instructions',
            'discussing someone\'s age', 'discussing a teacher', 'giving directions',
            'unclear exchange', 'brief conversation', 'short discussion'
        ]
        if any(generic in title.lower() for generic in generic_titles):
            logger.debug(f"Skipping generic recording {log_id[:8]}... (generic title: {title})")
            return False
        
        # Filter facts to only the most important ones (max 3)
        meaningful_facts = []
        for fact in facts:
            # Skip generic, political, or very short facts
            skip_terms = [
                'meeting', 'discussion', 'talked about', 'government', 'political',
                'madani', 'election', 'policy', 'minister', 'parliament',
                'brief', 'unclear', 'exchange', 'conversation'
            ]
            if (fact and len(fact) > 25 and 
                not any(skip_term in fact.lower() for skip_term in skip_terms) and
                not fact.lower().startswith('the current') and
                not fact.lower().startswith('everything is going')):
                meaningful_facts.append(fact)
        
        # Limit to top 3 most important facts
        meaningful_facts = meaningful_facts[:3]
        
        # Filter people to exclude generic speakers without meaningful context
        meaningful_people = []
        for person in people:
            person_name = person.get('name', '')
            context = person.get('context', '')
            
            # Skip generic speaker contexts
            skip_contexts = [
                'solo recording', 'technical brainstorming', 'general conversation',
                'unrecognized speaker', 'casual discussion', 'brief exchange'
            ]
            
            # Only include if person has a real name or meaningful context
            if (person_name and person_name != 'You' and 
                not person_name.startswith('Speaker ') and
                context and len(context) > 10 and
                not any(skip_ctx in context.lower() for skip_ctx in skip_contexts)):
                meaningful_people.append(person)
        
        # Limit to top 3 meaningful people
        meaningful_people = meaningful_people[:3]
        
        # Enhanced content validation - require substantial meaningful content
        has_meaningful_content = (
            len(meaningful_facts) > 0 or  # Has important facts
            len(meaningful_people) > 0 or  # Has meaningful people
            len(tasks) > 0 or  # Has tasks
            (transcript_length > 200 and any(keyword in title.lower() for keyword in [
                'work', 'project', 'plan', 'buy', 'family', 'meeting', 'appointment',
                'decision', 'important', 'remember', 'task', 'goal', 'problem', 'solution'
            ]))  # Longer recording with meaningful keywords
        )
        
        if not has_meaningful_content:
            logger.debug(f"Skipping recording {log_id[:8]}... (no substantial meaningful content)")
            return False
        
        # Build consolidated memory content - CONCISE SUMMARY FORMAT
        memory_parts = []
        
        # Create a natural summary instead of bullet points
        summary_parts = []
        
        # Add main topic from title
        main_topic = title.split('.')[0]  # Take first sentence if multiple
        summary_parts.append(main_topic)
        
        # Add key insights (not all facts, just the essence)
        if meaningful_facts:
            # Combine facts into a flowing summary instead of bullet points
            key_insight = meaningful_facts[0] if meaningful_facts else ""
            if len(meaningful_facts) > 1:
                # Find the most important fact or combine them naturally
                key_insight = f"{meaningful_facts[0]}. {meaningful_facts[1]}" if len(meaningful_facts[1]) < 50 else meaningful_facts[0]
        
        # Add people context naturally if relevant
        if meaningful_people:
            people_names = [p['name'] for p in meaningful_people[:2]]  # Max 2 people
            if len(people_names) == 1:
                summary_parts.append(f"Involves {people_names[0]}")
            elif len(people_names) == 2:
                summary_parts.append(f"Involves {people_names[0]} and {people_names[1]}")
        
        # Add task mention if any
        if tasks:
            summary_parts.append(f"Includes {len(tasks)} task(s)")
        
        # Create concise summary (max 2-3 sentences)
        content = ". ".join(summary_parts)
        if not content.endswith('.'):
            content += "."
        
        # Determine appropriate memory type based on content
        memory_type = determine_memory_type(content, meaningful_facts, meaningful_people, tasks)
        
        memory_id = memory_manager.create_memory(
            user_id=phone_number,
            content=content,
            memory_type=memory_type,
            extracted_from='limitless',
            importance=7,  # Higher importance for consolidated memories
            skip_deduplication=True  # OPTIMIZATION: Skip expensive AI deduplication - we already checked
        )
        
        # OPTIMIZATION: Efficient metadata update and tracking
        if memory_id and memory_id != "duplicate":
            # Set tracking key to prevent future duplicates (TTL: 30 days)
            redis_client.setex(limitless_memory_key, 86400 * 30, "1")
            
            # Single optimized metadata update
            memory_key = RedisKeyBuilder.get_user_memory_key(phone_number, memory_id)
            memory_data = redis_client.get(memory_key)
            if memory_data:
                memory_obj = json.loads(memory_data.decode() if isinstance(memory_data, bytes) else memory_data)
                # Batch all metadata updates into single operation
                memory_obj['metadata'] = {
                    **memory_obj.get('metadata', {}),
                    'source': 'limitless',
                    'log_id': log_id,
                    'is_consolidated': True,
                    'facts_count': len(meaningful_facts),
                    'people_count': len(meaningful_people),
                    'people_mentioned': [
                        {
                            'name': person['name'],
                            'context': person.get('context', ''),
                            'is_speaker': person.get('is_speaker', False)
                        } for person in meaningful_people
                    ]
                }
                redis_client.set(memory_key, json.dumps(memory_obj))
            
            logger.info(f"Created consolidated memory for recording {log_id[:8]}... with {len(meaningful_facts)} facts and {len(meaningful_people)} people")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error creating consolidated memory for {log_id}: {str(e)}")
        return False


def get_context_from_title_and_summary(title: str, summary: str, is_single_speaker: bool = False, phone_number: str = None) -> str:
    """
    Generate descriptive context based on recording type.
    
    Args:
        title: Recording title (unused - kept for backward compatibility)
        summary: Recording summary (unused - kept for backward compatibility)
        is_single_speaker: Whether this is a single-speaker recording
        phone_number: User's phone number for context (unused - kept for backward compatibility)
        
    Returns:
        Descriptive context string
    """
    # Simple deterministic context - no AI needed
    # This optimization reduces speaker identification from ~35s to <0.1s
    if is_single_speaker:
        return "Solo recording"
    else:
        return "Participant in conversation"


def extract_speakers_from_contents(log: Dict) -> List[Dict[str, str]]:
    """
    Extract speaker information directly from Limitless API contents.
    Uses dynamic "Speaker N" naming for unrecognized speakers.
    Properly handles multiple speakers with same name (e.g., "Unknown").
    
    Returns:
        List of speakers with their roles
    """
    speakers = []
    contents = log.get('contents', [])
    
    speaker_id_mapping = {}  # Map speaker IDs to Speaker N names
    speaker_id_to_info = {}  # Track all info about each speaker ID
    unrecognized_speaker_counter = 0
    user_detected = False
    
    # First pass: collect all unique speaker IDs and their names
    for content in contents:
        speaker_name = content.get('speakerName', '').strip()
        speaker_id = content.get('speakerIdentifier', '').strip()
        
        if not speaker_id:
            continue
            
        # Store speaker info by ID
        if speaker_id not in speaker_id_to_info:
            speaker_id_to_info[speaker_id] = {
                'names': set(),
                'is_user': speaker_id == 'user'
            }
        
        if speaker_name:
            speaker_id_to_info[speaker_id]['names'].add(speaker_name)
    
    # Second pass: create speaker entries based on unique IDs
    for speaker_id, info in speaker_id_to_info.items():
        names = info['names']
        is_user = info['is_user']
        
        if is_user:
            # Handle primary user
            speakers.append({
                'name': 'You',
                'context': 'Primary user (speaker)',
                'role': 'primary_user',
                'speaker_id': speaker_id
            })
            user_detected = True
        elif names:
            # Check if any of the names are problematic
            valid_names = [n for n in names if n and 
                          n.lower() not in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker', '']]
            
            if valid_names:
                # Use the first valid name (sorted for consistency)
                speaker_name = sorted(valid_names)[0]
                speakers.append({
                    'name': speaker_name,
                    'context': 'Identified speaker in conversation',
                    'role': 'participant',
                    'speaker_id': speaker_id
                })
            else:
                # All names are problematic (e.g., "Unknown") - assign Speaker N
                speaker_n_name = f"Speaker {unrecognized_speaker_counter}"
                speaker_id_mapping[speaker_id] = speaker_n_name
                
                # Get context based on recording content
                title = log.get('title', '')
                summary = log.get('summary', '')
                # Check if this is likely a single speaker based on speaker count
                is_single = len(speaker_id_to_info) == 1
                # Get phone number from log metadata if available
                phone_number = log.get('_phone_number', None)
                context = get_context_from_title_and_summary(title, summary, is_single_speaker=is_single, phone_number=phone_number)
                
                speakers.append({
                    'name': speaker_n_name,
                    'context': context,
                    'role': 'participant',
                    'speaker_id': speaker_id
                })
                unrecognized_speaker_counter += 1
                logger.info(f"Converted problematic speaker name '{list(names)}' to '{speaker_n_name}' for {log.get('id', 'unknown')[:8]}...")
        else:
            # No name at all - assign Speaker N
            speaker_n_name = f"Speaker {unrecognized_speaker_counter}"
            speaker_id_mapping[speaker_id] = speaker_n_name
            
            # Get context based on recording content
            title = log.get('title', '')
            summary = log.get('summary', '')
            # Check if this is likely a single speaker based on speaker count
            is_single = len(speaker_id_to_info) == 1
            # Get phone number from log metadata if available
            phone_number = log.get('_phone_number', None)
            context = get_context_from_title_and_summary(title, summary, is_single_speaker=is_single, phone_number=phone_number)
            
            speakers.append({
                'name': speaker_n_name,
                'context': context,
                'role': 'participant',
                'speaker_id': speaker_id
            })
            unrecognized_speaker_counter += 1
    
    # Handle contents without any speaker ID (edge case)
    has_unattributed_content = any(
        not content.get('speakerIdentifier', '').strip() 
        for content in contents 
        if content.get('content', '').strip()
    )
    
    if has_unattributed_content and not speakers:
        # Get context from title and summary
        title = log.get('title', '')
        summary = log.get('summary', '')
        # Get phone number from log metadata if available
        phone_number = log.get('_phone_number', None)
        context = get_context_from_title_and_summary(title, summary, is_single_speaker=True, phone_number=phone_number)
        
        # Add a speaker with descriptive context
        speakers.append({
            'name': f"Speaker {unrecognized_speaker_counter}",
            'context': context,
            'role': 'participant'
        })
    
    # ✅ ENHANCED FALLBACK: If no speakers detected, assume user is speaking
    if not speakers:
        logger.warning(f"No speakers detected in log {log.get('id')}, assuming primary user")
        speakers.append({
            'name': 'You',
            'context': 'Primary user (assumed speaker)',
            'role': 'primary_user'
        })
    
    # Store speaker mapping for consistent naming throughout transcript
    log['_speaker_mapping'] = speaker_id_mapping
    
    return speakers


def get_enhanced_extraction_prompt(title: str, summary: str, transcript: str) -> str:
    """Enhanced prompt with Speaker N naming support and fallback for when speaker info is missing."""
    
    # Check if transcript has speaker attribution (including any Speaker N naming)
    has_speaker_info = (
        'You:' in transcript or 
        any(f'Speaker {i}:' in transcript for i in range(0, 20)) or
        ':' in transcript  # Fallback for any speaker attribution
    )
    
    if has_speaker_info:
        # Use speaker-aware prompt with Speaker N support
        logger.debug("Using speaker-aware prompt with Speaker N naming for AI extraction")
        prompt = f"""Analyze this conversation transcript and extract ONLY the most important information:

1. Key facts and decisions - MAXIMUM 3 most important facts only
2. Action items and tasks - Look for natural language patterns like:
   - "remind me to...", "I need to...", "don't forget to..."
   - "my wife/husband told me to...", "I should...", "I have to..."
   - "make sure to...", "remember to..."
   - Any clear, actionable tasks or reminders mentioned in conversation
3. Important dates or events - ONLY specific dates mentioned
4. People mentioned - MAXIMUM 3 most relevant people

CRITICAL EXTRACTION RULES:
- Extract ONLY the most important 2-3 facts (decisions, outcomes, critical info)
- IGNORE casual mentions, observations, or trivial details
- For facts, focus on: important decisions, key outcomes, critical information to remember
- Skip generic statements like "we discussed X" or "talked about Y"
- Only extract tasks that are explicitly stated with clear action items
- Only include people who play a significant role in the conversation

IMPORTANT: Pay attention to speaker attribution in the transcript:
- If "You:" said something, it's the user's task
- If "Speaker 0:", "Speaker 1:", "Speaker 2:", etc. mentioned tasks, note who assigned them
- Preserve exact "Speaker N" names when referencing unrecognized speakers
- NEVER use "Unknown" or "Unknown Speaker"

Title: {title}
Summary: {summary}
Transcript: {transcript[:3000]}

Return a JSON object with:
{{
    "facts": ["fact1", "fact2"],  // MAX 3 facts
    "tasks": [{{
        "description": "task description", 
        "due_date": "YYYY-MM-DD or null",
        "assigned_to": "You" or "Speaker 0" or exact name,
        "assigned_by": "Speaker N who mentioned it",
        "source": "natural_language" or "ai_extracted",
        "urgency": "high" or "medium" or "low"
    }}],
    "events": [{{"title": "event", "date": "YYYY-MM-DD", "time": "HH:MM or null"}}],
    "people": [{{
        "name": "exact name or Speaker 0/1/2", 
        "context": "their role or relationship",
        "is_speaker": true/false
    }}]  // MAX 3 people
}}

Be VERY selective. Quality over quantity. Extract only clearly important information."""
    else:
        # ✅ FALLBACK: Use original prompt assuming single speaker
        logger.debug("No speaker attribution detected, using single-user prompt")
        prompt = f"""Analyze this single-speaker recording and extract ONLY the most important information:

1. Key facts and decisions - MAXIMUM 3 most important facts only
2. Action items and tasks - Look for natural language patterns like:
   - "remind me to...", "I need to...", "don't forget to..."
   - "my wife/husband told me to...", "I should...", "I have to..."
   - "make sure to...", "remember to..."
   - Any clear, actionable tasks or reminders mentioned in conversation
3. Important dates or events - ONLY specific dates mentioned
4. People mentioned - MAXIMUM 3 most relevant people

CRITICAL EXTRACTION RULES:
- Extract ONLY the most important 2-3 facts (decisions, outcomes, critical info)
- IGNORE casual mentions, observations, or trivial details
- For facts, focus on: important decisions, key outcomes, critical information to remember
- Skip generic statements like "I need to" without specific actions
- Only extract tasks that are explicitly stated with clear action items
- Only include people who are specifically named and relevant

NOTE: This appears to be a single-speaker recording. Assume all tasks are for the primary user.

Title: {title}
Summary: {summary}
Transcript: {transcript[:3000]}

Return a JSON object with:
{{
    "facts": ["fact1", "fact2"],  // MAX 3 facts
    "tasks": [{{
        "description": "task description", 
        "due_date": "YYYY-MM-DD or null",
        "assigned_to": "You",
        "assigned_by": "You",
        "source": "natural_language" or "ai_extracted",
        "urgency": "high" or "medium" or "low"
    }}],
    "events": [{{"title": "event", "date": "YYYY-MM-DD", "time": "HH:MM or null"}}],
    "people": [{{
        "name": "person", 
        "context": "their role or relationship",
        "is_speaker": false
    }}]  // MAX 3 people
}}

Be VERY selective. Quality over quantity. Extract only clearly important information."""
    
    return prompt


def create_task_from_limitless(task_data: Dict, phone_number: str) -> bool:
    """Create a Google Task from Limitless data."""
    try:
        # Get task lists
        lists = get_task_lists()
        if not lists:
            return False
            
        # Use first list or default
        task_list_id = lists[0]['id']
        
        # Create the task
        result = create_task(
            title=task_data.get('title', ''),
            notes=task_data.get('notes', ''),
            due_date=task_data.get('due'),
            list_id=task_list_id
        )
        return result is not None
        
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return False


def extract_natural_language_tasks(transcript: str, log_id: str, phone_number: str, title: str = "") -> tuple[int, List[Dict]]:
    """
    Extract natural language tasks and reminders from transcript.
    
    Detects spoken statements like:
    - "remind me to..."
    - "I need to..."  
    - "my wife told me to buy..."
    - "don't forget to..."
    
    Returns tuple of (number of tasks created, list of task data).
    """
    try:
        # Check if we've already processed this transcript for tasks
        task_key = RedisKeyBuilder.build_limitless_task_created_key(log_id)
        if redis_client.exists(task_key):
            logger.debug(f"Tasks already extracted for {log_id[:8]}...")
            # Return cached data if available
            cached_data = redis_client.get(task_key)
            if cached_data:
                try:
                    cache_info = json.loads(cached_data.decode() if isinstance(cached_data, bytes) else cached_data)
                    cached_tasks = cache_info.get('task_data', [])
                    return cache_info.get('tasks_created', 0), cached_tasks
                except:
                    pass
            return 0, []
        
        # Use Gemini to detect natural language task instructions
        task_detection_prompt = f"""Analyze this conversation transcript and identify any natural language task or reminder instructions.

Look for phrases like:
- "remind me to..."
- "I need to..."
- "don't forget to..."
- "my wife/husband told me to..."
- "I should..."
- "I have to..."
- "make sure to..."
- "remember to..."

Transcript:
{transcript[:4000]}

Return a JSON object with detected tasks:
{{
    "tasks_found": true/false,
    "natural_tasks": [
        {{
            "task_text": "exact task description",
            "urgency": "high/medium/low",
            "context": "who mentioned it or context"
        }}
    ]
}}

Only extract clear, actionable tasks. Ignore vague statements or general discussions.
Be conservative - only extract when you're confident it's a personal task/reminder."""

        response = simple_prompt_request(task_detection_prompt, phone_number)
        
        # Parse the response
        try:
            # Handle mixed responses with explanation and JSON
            cleaned_response = response.strip()
            
            # Extract JSON from response if it contains ```json blocks
            if '```json' in cleaned_response:
                json_match = re.search(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(1).strip()
            elif '```' in cleaned_response:
                json_match = re.search(r'```\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(1).strip()
            
            # Try to find JSON object in the response
            if not cleaned_response.startswith('{'):
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(0)
                else:
                    # No JSON found, return 0 tasks (this is normal for recordings without tasks)
                    logger.debug(f"No JSON structure found in task response for log {log_id}, no tasks extracted")
                    return 0, []
                
            task_data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            logger.debug(f"Failed to parse natural language task response for log {log_id}, no tasks extracted")
            return 0, []
        
        tasks_created = 0
        successful_tasks_data = []  # Track task data for successful tasks
        
        if task_data.get("tasks_found", False):
            natural_tasks = task_data.get("natural_tasks", [])
            
            for task in natural_tasks:
                task_text = task.get("task_text", "").strip()
                urgency = task.get("urgency", "medium")
                context = task.get("context", "")
                
                if task_text and len(task_text) > 5:  # Ensure meaningful task
                    # Create the task
                    task_title = f"{task_text}"
                    task_notes = f"From Limitless recording"
                    if title:
                        task_notes += f": {title}"
                    if context:
                        task_notes += f" - {context}"
                    
                    success = create_task_from_limitless({
                        'title': task_title,
                        'notes': task_notes
                    }, phone_number)
                    
                    if success:
                        tasks_created += 1
                        logger.debug(f"Created task: {task_title[:50]}...")
                        
                        # Store task data for unified storage
                        task_data_item = {
                            'description': task_title,
                            'urgency': urgency,
                            'context': context,
                            'source': 'natural_language',
                            'created_successfully': True,
                            'google_task_created': True,
                            'assigned_to': 'You',
                            'assigned_by': 'You'
                        }
                        successful_tasks_data.append(task_data_item)
                        
                        # Send WhatsApp notification
                        notification_msg = f"📝 *Task Created from Recording*\n\n✅ {task_title}\n\n_From your Limitless Pendant recording_"
                        send_whatsapp_threaded(notification_msg)
        
        # Mark this transcript as processed for natural language tasks
        redis_client.setex(
            task_key,
            86400 * 7,  # Keep for 7 days
            json.dumps({
                "processed_at": datetime.now().isoformat(),
                "tasks_created": tasks_created,
                "log_id": log_id,
                "task_data": successful_tasks_data  # Store task data for unified counting
            })
        )
        
        if tasks_created > 0:
            logger.debug(f"Extracted {tasks_created} tasks from {log_id[:8]}...")
        
        return tasks_created, successful_tasks_data
        
    except Exception as e:
        logger.error(f"Error extracting natural language tasks from log {log_id}: {str(e)}")
        return 0, []


async def get_today_lifelogs(phone_number: str) -> str:
    """Get today's Lifelog recordings."""
    try:
        # Get today's date in YYYY-MM-DD format
        today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        lifelogs = await limitless_client.get_lifelogs_by_date(
            date=today_date,
            include_markdown=False  # Just summaries for listing
        )
        
        if not lifelogs:
            return "No recordings found for today."
            
        # Format the response
        response = f"📅 *Today's Recordings ({len(lifelogs)})*\n\n"
        
        for i, log in enumerate(lifelogs, 1):
            title = log.get('title', 'Untitled')
            summary = log.get('summary', 'No summary available')
            start_time = log.get('startTime', '')
            
            # Parse and format time
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    time_str = dt.strftime('%I:%M %p')
                except:
                    time_str = ''
            else:
                time_str = ''
                
            response += f"{i}. *{title}*\n"
            response += f"   🕐 {time_str}\n"
            response += f"   📝 {summary[:100]}...\n\n"
            
        response += "_Use 'limitless search [topic]' to search recordings_"
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting today's Lifelogs: {str(e)}")
        return "❌ Error retrieving today's recordings."


async def get_yesterday_lifelogs(phone_number: str) -> str:
    """Get yesterday's Lifelog recordings."""
    try:
        # Get yesterday's date in YYYY-MM-DD format
        yesterday_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
        
        lifelogs = await limitless_client.get_lifelogs_by_date(
            date=yesterday_date,
            include_markdown=False  # Just summaries for listing
        )
        
        if not lifelogs:
            return "No recordings found for yesterday."
            
        # Format similar to today's response
        response = f"📅 *Yesterday's Recordings ({len(lifelogs)})*\n\n"
        
        for i, log in enumerate(lifelogs, 1):
            title = log.get('title', 'Untitled')
            summary = log.get('summary', 'No summary available')
            start_time = log.get('startTime', '')
            
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    time_str = dt.strftime('%I:%M %p')
                except:
                    time_str = ''
            else:
                time_str = ''
                
            response += f"{i}. *{title}*\n"
            response += f"   🕐 {time_str}\n"
            response += f"   📝 {summary[:100]}...\n\n"
            
        return response
        
    except Exception as e:
        logger.error(f"Error getting yesterday's Lifelogs: {str(e)}")
        return "❌ Error retrieving yesterday's recordings."


async def search_lifelogs(query: str, phone_number: str) -> str:
    """Search through cached Lifelog transcripts."""
    try:
        # Get all cached Lifelogs
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        keys = []
        for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
            
        if not keys:
            return "No cached recordings found. Try 'sync limitless' first."
            
        matches = []
        query_lower = query.lower()
        
        # Search through cached data
        for key in keys:
            data = redis_client.get(key)
            if not data:
                continue
                
            try:
                log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                
                # Search in title, summary, and extracted data
                title = log_data.get('title', '').lower()
                summary = log_data.get('summary', '').lower()
                extracted = log_data.get('extracted', {})
                # ✅ CRITICAL FIX: Standardize speaker names in cached data for search
                extracted = standardize_cached_speakers(extracted)
                
                # Check if query matches
                if (query_lower in title or 
                    query_lower in summary or
                    any(query_lower in fact.lower() for fact in extracted.get('facts', [])) or
                    any(query_lower in task.get('description', '').lower() for task in extracted.get('tasks', []))):
                    
                    matches.append(log_data)
                    
            except json.JSONDecodeError:
                continue
                
        if not matches:
            return f"No recordings found matching '{query}'."
            
        # Format results
        response = f"🔍 *Search Results for '{query}' ({len(matches)})*\n\n"
        
        for i, log in enumerate(matches[:5], 1):  # Limit to 5 results
            title = log.get('title', 'Untitled')
            summary = log.get('summary', 'No summary')
            start_time = log.get('start_time', '')
            
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    date_str = dt.strftime('%b %d, %I:%M %p')
                except:
                    date_str = ''
            else:
                date_str = ''
                
            response += f"{i}. *{title}*\n"
            response += f"   📅 {date_str}\n"
            response += f"   📝 {summary[:150]}...\n\n"
            
        if len(matches) > 5:
            response += f"_...and {len(matches) - 5} more results_"
            
        return response
        
    except Exception as e:
        logger.error(f"Error searching Lifelogs: {str(e)}")
        return "❌ Error searching recordings."


async def find_person_discussions(person_name: str, phone_number: str) -> str:
    """Find all discussions mentioning a specific person."""
    try:
        # Search for the person in cached Lifelogs
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        keys = []
        for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
            
        if not keys:
            return "No cached recordings found. Try 'sync limitless' first."
            
        matches = []
        person_lower = person_name.lower()
        
        for key in keys:
            data = redis_client.get(key)
            if not data:
                continue
                
            try:
                log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                extracted = log_data.get('extracted', {})
                # ✅ CRITICAL FIX: Standardize speaker names in cached data for person search
                extracted = standardize_cached_speakers(extracted)
                
                # Check people mentioned
                people = extracted.get('people', [])
                for person in people:
                    if person_lower in person.get('name', '').lower():
                        matches.append({
                            'log': log_data,
                            'context': person.get('context', 'No context')
                        })
                        break
                        
            except json.JSONDecodeError:
                continue
                
        if not matches:
            return f"No discussions found with '{person_name}'."
            
        # Format results
        response = f"👤 *Discussions with '{person_name}' ({len(matches)})*\n\n"
        
        for i, match in enumerate(matches[:5], 1):
            log = match['log']
            context = match['context']
            title = log.get('title', 'Untitled')
            start_time = log.get('start_time', '')
            
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    date_str = dt.strftime('%b %d, %I:%M %p')
                except:
                    date_str = ''
            else:
                date_str = ''
                
            response += f"{i}. *{title}*\n"
            response += f"   📅 {date_str}\n"
            response += f"   👤 Context: {context}\n\n"
            
        return response
        
    except Exception as e:
        logger.error(f"Error finding person discussions: {str(e)}")
        return "❌ Error searching for person."


async def get_daily_summary(date_str: Optional[str], phone_number: str) -> str:
    """Get a summary of recordings for a specific date."""
    try:
        # Parse date or use today
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                return "Invalid date format. Use YYYY-MM-DD."
        else:
            target_date = datetime.now()
            
        # Get date in YYYY-MM-DD format
        date_str = target_date.strftime('%Y-%m-%d')
        
        # Fetch Lifelogs for that day
        lifelogs = await limitless_client.get_lifelogs_by_date(
            date=date_str,
            include_markdown=False  # Just summaries for processing
        )
        
        if not lifelogs:
            date_str = target_date.strftime('%B %d, %Y')
            return f"No recordings found for {date_str}."
            
        # Use Gemini to create a cohesive summary
        summaries = []
        for log in lifelogs:
            title = log.get('title', 'Untitled')
            summary = log.get('summary', '')
            if summary:
                summaries.append(f"{title}: {summary}")
                
        combined_text = "\n\n".join(summaries)
        
        summary_prompt = f"""Create a concise daily summary from these meeting recordings:

{combined_text}

Provide:
1. Key themes discussed
2. Important decisions made
3. Action items identified
4. Notable insights

Keep it brief and well-structured."""

        ai_summary = simple_prompt_request(summary_prompt, phone_number)
        
        # Format response
        date_str = target_date.strftime('%B %d, %Y')
        response = f"📊 *Daily Summary - {date_str}*\n"
        response += f"_Total recordings: {len(lifelogs)}_\n\n"
        response += ai_summary
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating daily summary: {str(e)}")
        return "❌ Error generating daily summary."
