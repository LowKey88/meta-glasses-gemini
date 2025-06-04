"""
Limitless dashboard API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
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
        today = datetime.now(timezone.utc).date()
        
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
        
        # Get last sync time
        sync_key = RedisKeyBuilder.build_limitless_sync_key("default")  # Using default user for now
        last_sync = redis_client.get(sync_key)
        
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
        
        # Calculate pending sync (simplified - check last 24 hours)
        pending_sync = 0
        if limitless_client.api_key:
            try:
                # Get lifelogs from last 24 hours
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(hours=24)
                
                logger.info(f"Checking pending sync from {start_time} to {end_time}")
                
                # Check how many are not processed
                # Try without date filtering first to test API connectivity
                logger.info("Testing Limitless API without date filtering...")
                lifelogs = await limitless_client.get_all_lifelogs(
                    start_time=None,
                    end_time=None,
                    include_transcript=False,
                    include_summary=False,
                    max_entries=10
                )
                
                for log in lifelogs:
                    processed_key = RedisKeyBuilder.build_limitless_processed_key(log['id'])
                    if not redis_client.exists(processed_key):
                        pending_sync += 1
            except Exception as e:
                logger.error(f"Error checking pending sync: {str(e)}")
        
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
    date: Optional[str] = None,
    user: str = Depends(verify_dashboard_token)
) -> List[Dict[str, Any]]:
    """Get Lifelogs for a specific date."""
    try:
        # Parse date or use today
        if date:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            target_date = datetime.now(timezone.utc).date()
        
        # Get cached Lifelogs
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        lifelogs = []
        
        for key in redis_client.scan_iter(match=pattern):
            data = redis_client.get(key)
            if not data:
                continue
                
            try:
                log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                
                # Check if log is from target date
                start_time = log_data.get('start_time')
                if start_time:
                    log_date = datetime.fromisoformat(start_time.replace('Z', '+00:00')).date()
                    if log_date == target_date:
                        # Format for frontend
                        formatted_log = {
                            'id': log_data.get('id'),
                            'title': log_data.get('title', 'Untitled'),
                            'summary': log_data.get('summary', ''),
                            'start_time': log_data.get('start_time'),
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
                    
                    # Format for frontend
                    formatted_log = {
                        'id': log_data.get('id'),
                        'title': log_data.get('title', 'Untitled'),
                        'summary': log_data.get('summary', ''),
                        'start_time': log_data.get('start_time'),
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
    force: bool = False,
    user: str = Depends(verify_dashboard_token)
) -> Dict[str, Any]:
    """Manually trigger Limitless sync."""
    try:
        # Use a default phone number for dashboard sync
        phone_number = "dashboard_user"
        
        # If force sync, clear all processed flags first
        if force:
            logger.info("Force sync requested - clearing all processed flags")
            cleared_count = 0
            
            # Clear processed flags
            processed_pattern = RedisKeyBuilder.build_limitless_processed_key("*")
            for key in redis_client.scan_iter(match=processed_pattern):
                redis_client.delete(key)
                cleared_count += 1
            
            # Clear task creation flags
            task_pattern = RedisKeyBuilder.build_limitless_task_created_key("*")
            for key in redis_client.scan_iter(match=task_pattern):
                redis_client.delete(key)
                cleared_count += 1
                
            logger.info(f"Cleared {cleared_count} processed/task flags for force re-sync")
        
        # Run sync synchronously to provide immediate feedback
        result = await sync_recent_lifelogs(phone_number, hours=None)  # No hour limit for initial sync
        
        return {
            "message": "Sync completed successfully", 
            "result": result,
            "force_sync": force
        }
        
    except Exception as e:
        logger.error(f"Error running Limitless sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))