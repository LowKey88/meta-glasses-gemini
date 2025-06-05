"""
Limitless dashboard API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from datetime import datetime, timedelta, timezone
import json
import logging
import jwt
from typing import List, Dict, Optional, Any

from api.dashboard.config import JWT_SECRET
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder
from functionality.limitless import sync_recent_lifelogs, limitless_client

def verify_dashboard_token(authorization: Optional[str] = Header(None)):
    """Verify JWT token for dashboard access"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("user", "admin")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/limitless", tags=["limitless"])


@router.get("/stats")
async def get_limitless_stats(user: str = Depends(verify_dashboard_token)) -> Dict[str, Any]:
    """Get Limitless integration statistics."""
    try:
        # Get total cached Lifelogs
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        total_lifelogs = 0
        synced_today = 0
        today = datetime.now().date()
        
        for key in redis_client.scan_iter(match=pattern):
            total_lifelogs += 1
            # Check if synced today
            data = redis_client.get(key)
            if data:
                try:
                    log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                    processed_at = log_data.get('processed_at')
                    if processed_at:
                        processed_date = datetime.fromisoformat(processed_at).date()
                        if processed_date == today:
                            synced_today += 1
                except:
                    pass
        
        # Get last sync time - use same user_id as sync function
        phone_number = "60122873632"
        sync_key = RedisKeyBuilder.build_limitless_sync_key(phone_number)
        last_sync_raw = redis_client.get(sync_key)
        last_sync = last_sync_raw.decode() if isinstance(last_sync_raw, bytes) else last_sync_raw
        
        # Get sync status (simplified for now)
        sync_status = 'idle'
        
        # Count memories and tasks created from Limitless
        memories_created = 0
        tasks_created = 0
        
        # Count memories with limitless source
        memory_pattern = RedisKeyBuilder.get_user_memory_key("*", "*")
        for key in redis_client.scan_iter(match=memory_pattern):
            data = redis_client.get(key)
            if data:
                try:
                    memory_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                    metadata = memory_data.get('metadata', {})
                    if metadata.get('source') == 'limitless':
                        memories_created += 1
                except:
                    pass
        
        # Count tasks created from Limitless recordings
        lifelog_pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        for key in redis_client.scan_iter(match=lifelog_pattern):
            data = redis_client.get(key)
            if data:
                try:
                    log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                    extracted = log_data.get('extracted', {})
                    
                    # Count tasks from extracted data
                    tasks_from_recording = extracted.get('tasks', [])
                    tasks_created += len(tasks_from_recording)
                    
                except:
                    pass
        
        # Also count natural language tasks from Redis cache
        task_created_pattern = "meta-glasses:limitless:task_created:*"
        for key in redis_client.scan_iter(match=task_created_pattern):
            data = redis_client.get(key)
            if data:
                try:
                    task_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                    tasks_from_nlp = task_data.get('tasks_created', 0)
                    tasks_created += tasks_from_nlp
                except:
                    pass
        
        # Get cached pending sync count (avoid API calls on page load)
        pending_sync_key = "meta-glasses:limitless:pending_sync_cache"
        cached_pending = redis_client.get(pending_sync_key)
        
        if cached_pending:
            try:
                pending_sync = int(cached_pending.decode() if isinstance(cached_pending, bytes) else cached_pending)
                logger.debug(f"Using cached pending sync count: {pending_sync}")
            except:
                pending_sync = 0
        else:
            # Only calculate pending sync if not cached (to avoid unnecessary API calls)
            pending_sync = 0
            logger.info("No cached pending sync count, showing 0 (will update after next sync)")
        
        logger.info(f"📊 Dashboard stats: total_lifelogs={total_lifelogs}, synced_today={synced_today}, memories_created={memories_created}, tasks_created={tasks_created}")
        
        return {
            "total_lifelogs": total_lifelogs,
            "synced_today": synced_today,
            "last_sync": last_sync,
            "sync_status": sync_status,
            "memories_created": memories_created,
            "tasks_created": tasks_created,
            "pending_sync": pending_sync
        }
        
    except Exception as e:
        logger.error(f"Error getting Limitless stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lifelogs")
async def get_lifelogs(
    user: str = Depends(verify_dashboard_token)
) -> List[Dict[str, Any]]:
    """Get today's Lifelogs."""
    try:
        # Always use today's date
        target_date = datetime.now().date()
        
        # Get cached Lifelogs
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        lifelogs = []
        
        logger.info(f"Dashboard searching for Lifelogs with pattern: {pattern} for date: {target_date}")
        key_count = 0
        for key in redis_client.scan_iter(match=pattern):
            key_count += 1
            data = redis_client.get(key)
            if not data:
                continue
                
            try:
                log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                
                # Check if log is from target date
                start_time = log_data.get('start_time')
                logger.info(f"Found cached log {log_data.get('id')} with start_time: {start_time}")
                
                # If no start_time, show the recording (fallback behavior)
                # or if start_time matches target date
                should_include = False
                if not start_time:
                    logger.info(f"Log {log_data.get('id')} has no start_time, including in results")
                    should_include = True
                else:
                    try:
                        log_date = datetime.fromisoformat(start_time.replace('Z', '+00:00')).date()
                        logger.info(f"Parsed log date: {log_date}, target date: {target_date}")
                        should_include = (log_date == target_date)
                    except Exception as e:
                        logger.error(f"Error parsing date for log {log_data.get('id')}: {e}")
                        should_include = True  # Include if date parsing fails
                
                if should_include:
                    # Format for frontend - use created_at as fallback for start_time
                    start_time = log_data.get('start_time')
                    if not start_time:
                        # Try created_at or processed_at as fallback
                        start_time = log_data.get('created_at') or log_data.get('processed_at')
                    
                    formatted_log = {
                        'id': log_data.get('id'),
                        'title': log_data.get('title', 'Untitled'),
                        'summary': log_data.get('summary', ''),
                        'start_time': start_time,
                        'end_time': log_data.get('end_time'),
                        'duration_minutes': 0,
                        'has_transcript': True,
                        'processed': True,
                        'extracted_data': log_data.get('extracted', {})
                    }
                    
                    # Calculate duration
                    if log_data.get('start_time') and log_data.get('end_time'):
                        try:
                            start = datetime.fromisoformat(log_data['start_time'].replace('Z', '+00:00'))
                            end = datetime.fromisoformat(log_data['end_time'].replace('Z', '+00:00'))
                            duration = (end - start).total_seconds() / 60
                            formatted_log['duration_minutes'] = int(duration)
                        except:
                            pass
                    
                    lifelogs.append(formatted_log)
                        
            except json.JSONDecodeError:
                continue
        
        # Sort by start time
        lifelogs.sort(key=lambda x: x['start_time'] or '', reverse=True)
        
        logger.info(f"Dashboard found {key_count} cached keys, returning {len(lifelogs)} lifelogs for date {target_date}")
        return lifelogs
        
    except Exception as e:
        logger.error(f"Error getting Lifelogs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_lifelogs(
    q: str,
    user: str = Depends(verify_dashboard_token)
) -> List[Dict[str, Any]]:
    """Search Lifelogs by query."""
    try:
        if not q:
            return []
            
        # Get all cached Lifelogs
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        matches = []
        query_lower = q.lower()
        
        for key in redis_client.scan_iter(match=pattern):
            data = redis_client.get(key)
            if not data:
                continue
                
            try:
                log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                
                # Search in title, summary, and extracted data
                title = log_data.get('title', '').lower()
                summary = log_data.get('summary', '').lower()
                extracted = log_data.get('extracted', {})
                
                # Check if query matches
                if (query_lower in title or 
                    query_lower in summary or
                    any(query_lower in fact.lower() for fact in extracted.get('facts', [])) or
                    any(query_lower in task.get('description', '').lower() for task in extracted.get('tasks', [])) or
                    any(query_lower in person.get('name', '').lower() or 
                        query_lower in person.get('context', '').lower() 
                        for person in extracted.get('people', []))):
                    
                    # Format for frontend - use created_at as fallback for start_time
                    start_time = log_data.get('start_time')
                    if not start_time:
                        # Try created_at or processed_at as fallback
                        start_time = log_data.get('created_at') or log_data.get('processed_at')
                    
                    formatted_log = {
                        'id': log_data.get('id'),
                        'title': log_data.get('title', 'Untitled'),
                        'summary': log_data.get('summary', ''),
                        'start_time': start_time,
                        'end_time': log_data.get('end_time'),
                        'duration_minutes': 0,
                        'has_transcript': True,
                        'processed': True,
                        'extracted_data': extracted
                    }
                    
                    # Calculate duration
                    if log_data.get('start_time') and log_data.get('end_time'):
                        try:
                            start = datetime.fromisoformat(log_data['start_time'].replace('Z', '+00:00'))
                            end = datetime.fromisoformat(log_data['end_time'].replace('Z', '+00:00'))
                            duration = (end - start).total_seconds() / 60
                            formatted_log['duration_minutes'] = int(duration)
                        except:
                            pass
                    
                    matches.append(formatted_log)
                    
            except json.JSONDecodeError:
                continue
        
        # Sort by relevance (simple approach - title matches first)
        def relevance_score(log):
            score = 0
            if query_lower in log['title'].lower():
                score += 10
            if query_lower in log['summary'].lower():
                score += 5
            return score
        
        matches.sort(key=relevance_score, reverse=True)
        
        return matches[:20]  # Limit to 20 results
        
    except Exception as e:
        logger.error(f"Error searching Lifelogs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_limitless(
    user: str = Depends(verify_dashboard_token)
) -> Dict[str, Any]:
    """Manually trigger Limitless sync."""
    try:
        logger.info("🔄 MANUAL SYNC ENDPOINT CALLED - Starting sync process...")
        # Use the same user_id as the main dashboard
        phone_number = "60122873632"
        
        # Run sync for last 24 hours to match pending check window
        logger.info(f"📡 Calling sync_recent_lifelogs with user: {phone_number}, hours: 24")
        result = await sync_recent_lifelogs(phone_number, hours=24)
        logger.info(f"✅ Manual sync completed with result: {result[:100]}...")
        
        # Update pending sync cache after manual sync
        try:
            logger.info("🔄 Updating pending sync cache after manual sync...")
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            # Get recordings from the actual time range (no limit for accurate pending count)
            lifelogs = await limitless_client.get_all_lifelogs(
                start_time=start_time,
                end_time=end_time,
                timezone_str="Asia/Kuala_Lumpur",  # FIXED: Add timezone parameter
                max_entries=None,  # Remove limit to get accurate pending count
                include_markdown=False,
                include_headings=False
            )
            
            # Count pending recordings
            pending_count = 0
            for log in lifelogs:
                log_id = log.get('id', 'unknown')
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
                if not redis_client.exists(processed_key):
                    pending_count += 1
            
            # Cache the result for 5 minutes
            pending_sync_key = "meta-glasses:limitless:pending_sync_cache"
            redis_client.setex(pending_sync_key, 300, str(pending_count))  # 5 minute cache
            logger.info(f"📊 Updated pending sync cache: {pending_count} recordings pending")
            
        except Exception as e:
            logger.error(f"Error updating pending sync cache: {str(e)}")
        
        return {
            "message": "Sync completed successfully", 
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error running Limitless sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
