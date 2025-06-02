"""Dashboard API endpoints for Meta Glasses Admin Interface"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import jwt
from utils.redis_utils import r
from utils.memory_manager import MemoryManager
from utils.context_manager import ContextManager
from utils.reminder import ReminderManager
from .config import (
    JWT_SECRET, DASHBOARD_PASSWORD, TOKEN_EXPIRY_HOURS,
    API_PREFIX, DEFAULT_USER_ID, DEFAULT_LIMIT, MAX_LIMIT
)

logger = logging.getLogger("uvicorn")

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
        reminder_keys = r.keys("reminder:*")
        active_reminders = len(reminder_keys)
        
        # Get recent message count
        history = ContextManager.get_conversation_history(user_id, limit=100)
        recent_messages = len(history)
        
        # Calculate uptime (simple estimation)
        uptime = "Running"
        
        return DashboardStats(
            total_memories=len(memories),
            memory_by_type=memory_by_type,
            redis_keys=redis_keys,
            active_reminders=active_reminders,
            recent_messages=recent_messages,
            uptime=uptime
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
        if not r.exists(key):
            raise HTTPException(status_code=404, detail="Key not found")
        
        key_type = r.type(key).decode() if hasattr(r.type(key), 'decode') else str(r.type(key))
        
        if key_type == "string":
            value = r.get(key)
            if isinstance(value, bytes):
                try:
                    value = value.decode()
                    # Try to parse as JSON
                    value = json.loads(value)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        elif key_type == "hash":
            value = r.hgetall(key)
            value = {k.decode(): v.decode() for k, v in value.items()}
        elif key_type == "list":
            value = r.lrange(key, 0, -1)
            value = [v.decode() if isinstance(v, bytes) else v for v in value]
        elif key_type == "set":
            value = r.smembers(key)
            value = [v.decode() if isinstance(v, bytes) else v for v in value]
        else:
            value = f"Unsupported type: {key_type}"
        
        return {
            "key": key,
            "type": key_type,
            "value": value,
            "ttl": r.ttl(key)
        }
    except Exception as e:
        logger.error(f"Error getting Redis value: {e}")
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
        reminder_keys = r.keys("reminder:*")
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