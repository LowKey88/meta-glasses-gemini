"""Dashboard API endpoints for Meta Glasses Admin Interface"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import jwt
from utils.redis_utils import r
from utils.memory_manager import MemoryManager
from utils.context_manager import ContextManager
from utils.reminder import ReminderManager
from utils.gemini import GEMINI_VISION_MODEL, GEMINI_CHAT_MODEL
from utils.metrics import MetricsTracker
from utils.whatsapp_status import check_whatsapp_token_status
from .config import (
    JWT_SECRET, DASHBOARD_PASSWORD, TOKEN_EXPIRY_HOURS,
    API_PREFIX, DEFAULT_USER_ID, DEFAULT_LIMIT, MAX_LIMIT
)

logger = logging.getLogger("uvicorn")

# Track application start time
app_start_time = datetime.now()

# Dashboard API Router
dashboard_router = APIRouter(prefix=API_PREFIX, tags=["dashboard"])

class LoginRequest(BaseModel):
    password: str

class MemoryUpdate(BaseModel):
    content: str
    memory_type: str
    importance: int = 5

class DashboardStats(BaseModel):
    total_memories: int
    memory_by_type: Dict[str, int]
    redis_keys: int
    active_reminders: int
    recent_messages: int
    uptime: str
    ai_model_vision: str
    ai_model_chat: str
    total_ai_requests_today: int
    message_activity: Dict[str, int]  # Hourly message counts for last 24 hours
    weekly_activity: Dict[str, int]  # Daily totals for last 7 days
    today_vs_yesterday: Dict[str, Dict[str, int]]  # Hourly comparison
    whatsapp_status: str
    whatsapp_token_info: Dict[str, Any]  # Token status and expiry info

def verify_token(authorization: Optional[str] = Header(None)):
    """Verify JWT token for dashboard access"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@dashboard_router.post("/login")
async def dashboard_login(request: LoginRequest):
    """Login to dashboard with password"""
    # Simple password check (should be hashed in production)
    if request.password != DASHBOARD_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Create JWT token
    payload = {
        "user": "admin",
        "exp": datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    return {"token": token, "user": "admin"}

@dashboard_router.get("/stats", dependencies=[Depends(verify_token)])
async def get_dashboard_stats(user_id: str = "60122873632"):
    """Get overall system statistics"""
    try:
        # Get all memories
        memories = MemoryManager.get_all_memories(user_id)
        
        # Count by type
        memory_by_type = {}
        for memory in memories:
            mem_type = memory.get('type', 'unknown')
            memory_by_type[mem_type] = memory_by_type.get(mem_type, 0) + 1
        
        # Count Redis keys
        redis_keys = len(r.keys("*"))
        
        # Count active reminders
        reminder_keys = r.keys("josancamon:rayban-meta-glasses-api:reminder:*")
        active_reminders = len(reminder_keys)
        
        # Get today's message count from metrics
        recent_messages = MetricsTracker.get_messages_today()
        
        # Calculate uptime
        uptime_seconds = int((datetime.now() - app_start_time).total_seconds())
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        
        if days > 0:
            uptime = f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            uptime = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            uptime = f"{minutes}m {seconds}s"
        else:
            uptime = f"{seconds}s"
        
        # Get AI metrics
        total_ai_requests = MetricsTracker.get_ai_requests_today()
        message_activity = MetricsTracker.get_message_activity(24)  # Last 24 hours
        weekly_activity = MetricsTracker.get_weekly_message_activity()  # Last 7 days
        today_vs_yesterday = MetricsTracker.get_today_vs_yesterday_hourly()  # Comparison
        
        # Get WhatsApp status
        whatsapp_token_info = check_whatsapp_token_status()
        whatsapp_status = whatsapp_token_info.get('status', 'unknown')
        
        return DashboardStats(
            total_memories=len(memories),
            memory_by_type=memory_by_type,
            redis_keys=redis_keys,
            active_reminders=active_reminders,
            recent_messages=recent_messages,
            uptime=uptime,
            ai_model_vision=GEMINI_VISION_MODEL,
            ai_model_chat=GEMINI_CHAT_MODEL,
            total_ai_requests_today=total_ai_requests,
            message_activity=message_activity,
            weekly_activity=weekly_activity,
            today_vs_yesterday=today_vs_yesterday,
            whatsapp_status=whatsapp_status,
            whatsapp_token_info=whatsapp_token_info
        )
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/memories", dependencies=[Depends(verify_token)])
async def get_memories(
    user_id: str = "60122873632",
    memory_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50
):
    """Get user memories with optional filtering"""
    try:
        if search:
            memories = MemoryManager.search_memories(user_id, search, memory_type, limit)
        elif memory_type:
            memories = MemoryManager.get_memories_by_type(user_id, memory_type)[:limit]
        else:
            memories = MemoryManager.get_all_memories(user_id)[:limit]
        
        return {"memories": memories, "total": len(memories)}
    except Exception as e:
        logger.error(f"Error getting memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.put("/memories/{memory_id}", dependencies=[Depends(verify_token)])
async def update_memory(
    memory_id: str,
    update: MemoryUpdate,
    user_id: str = "60122873632"
):
    """Update a specific memory"""
    try:
        success = MemoryManager.update_memory(
            user_id,
            memory_id,
            {
                "content": update.content,
                "type": update.memory_type,
                "importance": update.importance
            }
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {"success": True, "message": "Memory updated"}
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.delete("/memories/{memory_id}", dependencies=[Depends(verify_token)])
async def delete_memory(memory_id: str, user_id: str = "60122873632"):
    """Delete a specific memory"""
    try:
        success = MemoryManager.delete_memory(user_id, memory_id)
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {"success": True, "message": "Memory deleted"}
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/redis/keys", dependencies=[Depends(verify_token)])
async def get_redis_keys(pattern: str = "*", limit: int = 100):
    """Get Redis keys matching pattern"""
    try:
        keys = r.keys(pattern)
        keys = [k.decode() if isinstance(k, bytes) else k for k in keys][:limit]
        
        result = []
        for key in keys:
            ttl = r.ttl(key)
            key_type = r.type(key).decode() if hasattr(r.type(key), 'decode') else str(r.type(key))
            
            result.append({
                "key": key,
                "type": key_type,
                "ttl": ttl if ttl > 0 else None
            })
        
        return {"keys": result, "total": len(result)}
    except Exception as e:
        logger.error(f"Error getting Redis keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/redis/key/{key:path}", dependencies=[Depends(verify_token)])
async def get_redis_value(key: str):
    """Get value of a specific Redis key"""
    try:
        # URL decode the key since it comes encoded from the frontend
        from urllib.parse import unquote
        decoded_key = unquote(key)
        
        if not r.exists(decoded_key):
            raise HTTPException(status_code=404, detail=f"Key not found: {decoded_key}")
        
        key_type = r.type(decoded_key).decode() if hasattr(r.type(decoded_key), 'decode') else str(r.type(decoded_key))
        
        if key_type == "string":
            value = r.get(decoded_key)
            if isinstance(value, bytes):
                try:
                    value = value.decode()
                    # Try to parse as JSON
                    value = json.loads(value)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        elif key_type == "hash":
            value = r.hgetall(decoded_key)
            value = {k.decode(): v.decode() for k, v in value.items()}
        elif key_type == "list":
            value = r.lrange(decoded_key, 0, -1)
            value = [v.decode() if isinstance(v, bytes) else v for v in value]
        elif key_type == "set":
            value = r.smembers(decoded_key)
            value = [v.decode() if isinstance(v, bytes) else v for v in value]
        else:
            value = f"Unsupported type: {key_type}"
        
        return {
            "key": decoded_key,
            "type": key_type,
            "value": value,
            "ttl": r.ttl(decoded_key)
        }
    except Exception as e:
        logger.error(f"Error getting Redis value: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.delete("/redis/key/{key:path}", dependencies=[Depends(verify_token)])
async def delete_redis_key(key: str):
    """Delete a specific Redis key"""
    try:
        # URL decode the key since it comes encoded from the frontend
        from urllib.parse import unquote
        decoded_key = unquote(key)
        
        if not r.exists(decoded_key):
            raise HTTPException(status_code=404, detail=f"Key not found: {decoded_key}")
        
        # Delete the key
        r.delete(decoded_key)
        
        return {"message": f"Key '{decoded_key}' deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting Redis key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/messages/recent", dependencies=[Depends(verify_token)])
async def get_recent_messages(user_id: str = "60122873632", limit: int = 50):
    """Get recent WhatsApp messages"""
    try:
        history = ContextManager.get_conversation_history(user_id, limit)
        return {"messages": history, "total": len(history)}
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/reminders", dependencies=[Depends(verify_token)])
async def get_active_reminders():
    """Get all active reminders"""
    try:
        reminder_keys = r.keys("josancamon:rayban-meta-glasses-api:reminder:*")
        reminders = []
        
        for key in reminder_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            value = r.get(key_str)
            if value:
                try:
                    reminder_data = json.loads(value)
                    ttl = r.ttl(key_str)
                    reminder_data['ttl'] = ttl
                    reminder_data['key'] = key_str
                    reminders.append(reminder_data)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        
        return {"reminders": reminders, "total": len(reminders)}
    except Exception as e:
        logger.error(f"Error getting reminders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.post("/calendar/sync", dependencies=[Depends(verify_token)])
async def trigger_calendar_sync():
    """Manually trigger calendar sync"""
    try:
        success = ReminderManager.sync_with_calendar()
        return {"success": success, "message": "Calendar sync triggered"}
    except Exception as e:
        logger.error(f"Error syncing calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))