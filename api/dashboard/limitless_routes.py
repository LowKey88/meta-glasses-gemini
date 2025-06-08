"""
Limitless dashboard API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query, BackgroundTasks
from datetime import datetime, timedelta, timezone
import json
import logging
import jwt
import uuid
import asyncio
from typing import List, Dict, Optional, Any

from api.dashboard.config import JWT_SECRET
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder
from functionality.limitless import sync_recent_lifelogs, limitless_client
from utils.limitless_logger import limitless_routes_logger

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


async def run_sync_in_background(task_id: str, phone_number: str, hours: int = 24):
    """Run Limitless sync in background and update status in Redis."""
    try:
        # Update status to running
        status_key = f"meta-glasses:limitless:sync_status:{task_id}"
        redis_client.setex(status_key, 3600, json.dumps({
            "status": "running",
            "progress": 0,
            "message": "Starting sync...",
            "started_at": datetime.now().isoformat()
        }))
        
        # Run the actual sync
        result = await sync_recent_lifelogs(phone_number, hours=hours)
        
        # Update status to completed
        redis_client.setex(status_key, 3600, json.dumps({
            "status": "completed",
            "progress": 100,
            "message": "Sync completed successfully",
            "result": result,
            "completed_at": datetime.now().isoformat()
        }))
        
        logger.info(f"✅ Background sync {task_id} completed successfully")
        
        # Update pending sync cache after completion
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            lifelogs = await limitless_client.get_all_lifelogs(
                start_time=start_time,
                end_time=end_time,
                timezone_str="Asia/Kuala_Lumpur",
                max_entries=None,
                include_markdown=False,
                include_headings=False
            )
            
            pending_count = 0
            for log in lifelogs:
                log_id = log.get('id', 'unknown')
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
                if not redis_client.exists(processed_key):
                    pending_count += 1
            
            pending_sync_key = "meta-glasses:limitless:pending_sync_cache"
            redis_client.setex(pending_sync_key, 300, str(pending_count))
            
        except Exception as e:
            logger.error(f"Error updating pending sync cache: {str(e)}")
            
    except Exception as e:
        logger.error(f"Background sync {task_id} failed: {str(e)}")
        redis_client.setex(status_key, 3600, json.dumps({
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }))


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
        # FIXED: Use unified counting to eliminate double counting
        lifelog_pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        total_lifelogs_found = 0
        
        for key in redis_client.scan_iter(match=lifelog_pattern):
            total_lifelogs_found += 1
            data = redis_client.get(key)
            if data:
                try:
                    log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                    extracted = log_data.get('extracted', {})
                    
                    # Count only successfully created tasks from extracted data
                    # This now includes both AI-extracted and natural language tasks
                    tasks_from_recording = extracted.get('tasks', [])
                    
                    # EMERGENCY FIX: Pragmatic counting with backward compatibility
                    validated_count = 0
                    legacy_count = 0
                    failed_count = 0
                    
                    for task in tasks_from_recording:
                        if isinstance(task, dict):
                            # Count tasks based on validation status
                            if task.get('created_successfully') is True:
                                # New format: explicitly successful
                                validated_count += 1
                            elif task.get('created_successfully') is False:
                                # New format: explicitly failed - skip
                                failed_count += 1
                            elif 'created_successfully' not in task:
                                # Legacy format: assume successful if has description
                                if task.get('description') and len(str(task.get('description')).strip()) > 0:
                                    legacy_count += 1
                                # Skip empty or malformed legacy tasks
                    
                    # Count both validated and legitimate legacy tasks
                    tasks_created += (validated_count + legacy_count)
                    
                    # Debug logging for investigation
                    if validated_count > 0 or legacy_count > 0 or failed_count > 0:
                        logger.debug(f"Task count analysis - Log {log_data.get('id', 'unknown')[:8]}...: "
                                   f"validated={validated_count}, legacy={legacy_count}, failed={failed_count}")
                    
                    # DIAGNOSTIC: Log task structure for debugging
                    if len(tasks_from_recording) > 0:
                        sample_task = tasks_from_recording[0]
                        logger.debug(f"Sample task structure: {list(sample_task.keys()) if isinstance(sample_task, dict) else type(sample_task)}")
                    
                except Exception as e:
                    logger.debug(f"Error parsing lifelog data: {e}")
                    pass
        
        logger.debug(f"📊 Task counting summary: Found {total_lifelogs_found} lifelogs, counted {tasks_created} tasks total")
        
        # Get cached pending sync count (avoid API calls on page load)
        pending_sync_key = "meta-glasses:limitless:pending_sync_cache"
        cached_pending = redis_client.get(pending_sync_key)
        
        if cached_pending:
            try:
                pending_sync = int(cached_pending.decode() if isinstance(cached_pending, bytes) else cached_pending)
                limitless_routes_logger.cache_update("pending_sync", pending_sync)
            except:
                pending_sync = 0
        else:
            # Only calculate pending sync if not cached (to avoid unnecessary API calls)
            pending_sync = 0
            logger.debug("No cached pending sync count, defaulting to 0")
        
        limitless_routes_logger.dashboard_request("stats", {
            "total": total_lifelogs,
            "today": synced_today,
            "memories": memories_created,
            "tasks": tasks_created
        })
        
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
    date: Optional[str] = Query(None),
    user: str = Depends(verify_dashboard_token)
) -> List[Dict[str, Any]]:
    """Get Lifelogs for a specific date."""
    try:
        # Use provided date or default to today
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            target_date = datetime.now().date()
        
        # Get cached Lifelogs
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        lifelogs = []
        
        limitless_routes_logger.dashboard_request("lifelogs", {"date": str(target_date)})
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
                
                # If no start_time, show the recording (fallback behavior)
                # or if start_time matches target date
                should_include = False
                if not start_time:
                    should_include = True
                else:
                    try:
                        log_date = datetime.fromisoformat(start_time.replace('Z', '+00:00')).date()
                        should_include = (log_date == target_date)
                    except Exception as e:
                        logger.debug(f"Date parse error for {log_data.get('id')[:8]}...: {e}")
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
        
        logger.debug(f"Found {len(lifelogs)}/{key_count} logs for {target_date}")
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
    background_tasks: BackgroundTasks,
    user: str = Depends(verify_dashboard_token)
) -> Dict[str, Any]:
    """Start Limitless sync in background - returns immediately with task ID."""
    try:
        limitless_routes_logger.dashboard_request("sync", {"manual": True})
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        phone_number = "60122873632"
        
        # Start sync in background
        background_tasks.add_task(run_sync_in_background, task_id, phone_number, 24)
        
        logger.info(f"📋 Started background sync with task ID: {task_id}")
        
        return {
            "task_id": task_id,
            "message": "Sync started in background"
        }
        
    except Exception as e:
        logger.error(f"Error running Limitless sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/status/{task_id}")
async def get_sync_status(
    task_id: str,
    user: str = Depends(verify_dashboard_token)
) -> Dict[str, Any]:
    """Get status of a background sync task."""
    try:
        status_key = f"meta-glasses:limitless:sync_status:{task_id}"
        status_data = redis_client.get(status_key)
        
        if not status_data:
            raise HTTPException(status_code=404, detail="Task not found")
        
        status = json.loads(status_data.decode() if isinstance(status_data, bytes) else status_data)
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
