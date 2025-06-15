"""Dashboard API endpoints for Meta Glasses Admin Interface"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
import jwt
from utils.redis_utils import r
from utils.memory_manager import MemoryManager
from utils.context_manager import ContextManager
from utils.reminder import ReminderManager
from utils.gemini import GEMINI_VISION_MODEL, GEMINI_CHAT_MODEL
from utils.metrics import MetricsTracker
from utils.performance_tracker import PerformanceTracker
from utils.whatsapp_status import check_whatsapp_token_status_sync, get_cached_or_check_whatsapp_status
from utils.ai_status import check_gemini_api_status_sync, get_ai_usage_stats, get_cached_or_check_gemini_status
from .config import (
    JWT_SECRET, DASHBOARD_PASSWORD, TOKEN_EXPIRY_HOURS,
    API_PREFIX, DEFAULT_USER_ID, DEFAULT_LIMIT, MAX_LIMIT
)
from .auth import verify_token, authenticate_user, create_access_token
from utils.redis_key_builder import redis_keys

logger = logging.getLogger("uvicorn")

# Track application start time
app_start_time = datetime.now()

# Dashboard API Router
dashboard_router = APIRouter(prefix=API_PREFIX, tags=["dashboard"])

# Import Limitless router
from .limitless_routes import router as limitless_router
dashboard_router.include_router(limitless_router)

# Import Settings router
from .settings_routes import router as settings_router
dashboard_router.include_router(settings_router)

# Import Task router
from .task_routes import router as task_router
dashboard_router.include_router(task_router)

class LoginRequest(BaseModel):
    password: str

class MemoryCreate(BaseModel):
    user_id: str
    content: str
    type: str
    tags: List[str] = []

class MemoryUpdate(BaseModel):
    content: str
    memory_type: str

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
    ai_status: Dict[str, Any]  # AI API status and rate limits
    ai_usage_stats: Dict[str, Any]  # AI usage statistics

@dashboard_router.post("/login")
async def dashboard_login(request: LoginRequest, http_request: Request):
    """Login to dashboard with enhanced security"""
    try:
        # Get client IP for rate limiting
        client_ip = http_request.client.host if http_request.client else "unknown"
        
        # Authenticate user with rate limiting and security checks
        if not authenticate_user(request.password, client_ip):
            raise HTTPException(status_code=401, detail="Invalid password")
        
        # Create secure JWT token
        user_data = {"user": "admin"}
        token = create_access_token(user_data, timedelta(hours=TOKEN_EXPIRY_HOURS))
        
        logger.info(f"Successful login from IP: {client_ip}")
        return {"token": token, "user": "admin"}
    
    except HTTPException:
        # Re-raise HTTP exceptions (like rate limiting)
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@dashboard_router.get("/stats", dependencies=[Depends(verify_token)])
async def get_dashboard_stats(user_id: str = "60122873632"):
    """Get overall system statistics"""
    try:
        # Get memory counts efficiently without loading all data
        memory_counts = MemoryManager.get_memory_counts_by_type(user_id)
        total_memories = sum(memory_counts.values())
        
        # Use DBSIZE instead of KEYS * for total count (much faster)
        from utils.redis_monitor import redis_monitor
        total_redis_keys = redis_monitor.execute_with_monitoring("DBSIZE", "db", r.dbsize)
        
        # Use scan with pattern for reminders (more efficient than KEYS)
        reminder_pattern = redis_keys.get_all_reminder_keys_pattern()
        active_reminders = 0
        for key in r.scan_iter(match=reminder_pattern, count=100):
            active_reminders += 1
        
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
        
        # Get WhatsApp and AI status concurrently for better performance
        import asyncio
        import concurrent.futures
        
        def get_concurrent_status():
            """Run WhatsApp and AI status checks in parallel with fast-path caching"""
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both API checks to run concurrently using optimized fast-path functions
                whatsapp_future = executor.submit(get_cached_or_check_whatsapp_status)
                ai_future = executor.submit(get_cached_or_check_gemini_status)
                
                # Wait for both to complete with 4-second timeout total (reduced from 6s)
                try:
                    whatsapp_result = whatsapp_future.result(timeout=4)
                    ai_result = ai_future.result(timeout=4)
                    return whatsapp_result, ai_result
                except concurrent.futures.TimeoutError:
                    # Return cached or default values on timeout
                    return {"status": "timeout", "is_valid": False}, {"status": "timeout", "is_available": False}
        
        whatsapp_token_info, ai_status_info = get_concurrent_status()
        whatsapp_status = whatsapp_token_info.get('status', 'unknown')
        
        # Get AI usage stats (Redis-only, fast)
        ai_usage_stats = get_ai_usage_stats()
        
        return DashboardStats(
            total_memories=total_memories,
            memory_by_type=memory_counts,
            redis_keys=total_redis_keys,
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
            whatsapp_token_info=whatsapp_token_info,
            ai_status=ai_status_info,
            ai_usage_stats=ai_usage_stats
        )
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/memories", dependencies=[Depends(verify_token)])
async def get_memories(
    user_id: str = "60122873632",
    memory_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    # Legacy parameters for backward compatibility
    limit: Optional[int] = None
):
    """Get user memories with pagination, filtering, and sorting"""
    try:
        # Validate parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 50
        if sort_by not in ["created_at", "type", "content"]:
            sort_by = "created_at"
        if sort_order not in ["asc", "desc"]:
            sort_order = "desc"
        
        # Use legacy behavior if limit is specified (for backward compatibility)
        if limit is not None:
            logger.warning("Using legacy limit parameter - consider switching to pagination")
            if search:
                memories = MemoryManager.search_memories(user_id, search, memory_type, limit)
            elif memory_type:
                memories = MemoryManager.get_memories_by_type(user_id, memory_type)[:limit]
            else:
                memories = MemoryManager.get_all_memories(user_id)[:limit]
            
            return {
                "memories": memories, 
                "total": len(memories),
                "page": 1,
                "page_size": len(memories),
                "total_pages": 1,
                "has_next": False,
                "has_prev": False
            }
        
        # Use new pagination method
        memories, total_count = MemoryManager.get_memories_paginated(
            user_id=user_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            memory_type=memory_type,
            search_query=search
        )
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "memories": memories,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
    except Exception as e:
        logger.error(f"Error getting memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.post("/memories", dependencies=[Depends(verify_token)])
async def create_memory(memory: MemoryCreate):
    """Create a new memory"""
    try:
        # Use default importance of 6 for manual memories created via dashboard
        memory_id = MemoryManager.create_memory(
            user_id=memory.user_id,
            content=memory.content,
            memory_type=memory.type,
            tags=memory.tags,
            importance=6,  # Fixed default for manual memories
            extracted_from="manual"
        )
        
        if memory_id == "duplicate":
            raise HTTPException(status_code=409, detail="Memory already exists")
        
        return {"success": True, "message": "Memory created", "id": memory_id}
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
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
                "type": update.memory_type
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
    """Get Redis keys matching pattern with monitoring"""
    try:
        from utils.redis_monitor import redis_monitor
        
        # Use monitored keys operation
        keys = redis_monitor.execute_with_monitoring("KEYS", pattern, r.keys, pattern)
        keys = [k.decode() if isinstance(k, bytes) else k for k in keys][:limit]
        
        result = []
        for key in keys:
            # Use monitored operations for TTL and TYPE
            ttl = redis_monitor.execute_with_monitoring("TTL", key, r.ttl, key)
            key_type = redis_monitor.execute_with_monitoring("TYPE", key, r.type, key)
            key_type = key_type.decode() if hasattr(key_type, 'decode') else str(key_type)
            
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
    """Get value of a specific Redis key with monitoring"""
    try:
        from utils.redis_monitor import redis_monitor
        
        # URL decode the key since it comes encoded from the frontend
        from urllib.parse import unquote
        decoded_key = unquote(key)
        
        if not redis_monitor.execute_with_monitoring("EXISTS", decoded_key, r.exists, decoded_key):
            raise HTTPException(status_code=404, detail=f"Key not found: {decoded_key}")
        
        key_type = redis_monitor.execute_with_monitoring("TYPE", decoded_key, r.type, decoded_key)
        key_type = key_type.decode() if hasattr(key_type, 'decode') else str(key_type)
        
        if key_type == "string":
            value = redis_monitor.execute_with_monitoring("GET", decoded_key, r.get, decoded_key)
            if isinstance(value, bytes):
                try:
                    value = value.decode()
                    # Try to parse as JSON
                    value = json.loads(value)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        elif key_type == "hash":
            value = redis_monitor.execute_with_monitoring("HGETALL", decoded_key, r.hgetall, decoded_key)
            value = {k.decode(): v.decode() for k, v in value.items()}
        elif key_type == "list":
            value = redis_monitor.execute_with_monitoring("LRANGE", decoded_key, r.lrange, decoded_key, 0, -1)
            value = [v.decode() if isinstance(v, bytes) else v for v in value]
        elif key_type == "set":
            value = redis_monitor.execute_with_monitoring("SMEMBERS", decoded_key, r.smembers, decoded_key)
            value = [v.decode() if isinstance(v, bytes) else v for v in value]
        else:
            value = f"Unsupported type: {key_type}"
        
        ttl = redis_monitor.execute_with_monitoring("TTL", decoded_key, r.ttl, decoded_key)
        
        return {
            "key": decoded_key,
            "type": key_type,
            "value": value,
            "ttl": ttl
        }
    except Exception as e:
        logger.error(f"Error getting Redis value: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.delete("/redis/key/{key:path}", dependencies=[Depends(verify_token)])
async def delete_redis_key(key: str):
    """Delete a specific Redis key with monitoring"""
    try:
        from utils.redis_monitor import redis_monitor
        
        # URL decode the key since it comes encoded from the frontend
        from urllib.parse import unquote
        decoded_key = unquote(key)
        
        if not redis_monitor.execute_with_monitoring("EXISTS", decoded_key, r.exists, decoded_key):
            raise HTTPException(status_code=404, detail=f"Key not found: {decoded_key}")
        
        # Delete the key with monitoring
        redis_monitor.execute_with_monitoring("DEL", decoded_key, r.delete, decoded_key)
        
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
        from utils.redis_monitor import redis_monitor
        
        pattern = redis_keys.get_all_reminder_keys_pattern()
        reminder_keys = redis_monitor.execute_with_monitoring("KEYS", pattern, r.keys, pattern)
        reminders = []
        
        for key in reminder_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            value = redis_monitor.execute_with_monitoring("GET", key_str, r.get, key_str)
            if value:
                try:
                    reminder_data = json.loads(value)
                    ttl = redis_monitor.execute_with_monitoring("TTL", key_str, r.ttl, key_str)
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

@dashboard_router.get("/redis/info", dependencies=[Depends(verify_token)])
async def get_redis_info():
    """Get Redis server information and statistics"""
    try:
        # Get Redis server info
        info = r.info()
        
        # Calculate uptime in human readable format
        uptime_seconds = info.get('uptime_in_seconds', 0)
        uptime_hours = uptime_seconds // 3600
        uptime_minutes = (uptime_seconds % 3600) // 60
        
        if uptime_hours > 0:
            uptime = f"{uptime_hours} h {uptime_minutes} m"
        else:
            uptime = f"{uptime_minutes} m"
        
        # Get memory info
        used_memory = info.get('used_memory', 0)
        used_memory_human = info.get('used_memory_human', '0B')
        maxmemory = info.get('maxmemory', 0)
        
        # If no max memory set, use system available memory estimate
        if maxmemory == 0:
            maxmemory_human = "Unlimited"
        else:
            # Convert bytes to MB
            maxmemory_mb = maxmemory / (1024 * 1024)
            maxmemory_human = f"{maxmemory_mb:.1f}MB"
        
        # Get total keys count with monitoring
        from utils.redis_monitor import redis_monitor
        total_keys = redis_monitor.execute_with_monitoring("DBSIZE", "db0", r.dbsize)  # Current database
        
        # Get connected clients
        connected_clients = info.get('connected_clients', 0)
        
        # Get Redis version
        redis_version = info.get('redis_version', 'Unknown')
        
        return {
            "status": "CONNECTED",
            "uptime": uptime,
            "memory_used": used_memory_human,
            "memory_total": maxmemory_human,
            "total_keys": total_keys,
            "connected_clients": connected_clients,
            "redis_version": redis_version,
            "uptime_seconds": uptime_seconds
        }
    except Exception as e:
        logger.error(f"Error getting Redis info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/redis/stats", dependencies=[Depends(verify_token)])
async def get_redis_stats():
    """Get Redis performance statistics with real-time monitoring data"""
    try:
        # Import the monitor here to avoid circular imports
        from utils.redis_monitor import redis_monitor
        
        # Get Redis server stats
        info = r.info('stats')
        total_commands = info.get('total_commands_processed', 0)
        instantaneous_ops = info.get('instantaneous_ops_per_sec', 0)
        
        # Get recent commands from our monitor
        recent_commands = redis_monitor.get_recent_commands(limit=3)
        
        # Get latency statistics from our monitor
        latency_stats = redis_monitor.get_latency_stats()
        
        # If no monitored commands yet, provide some sample data
        if not recent_commands:
            recent_commands = [
                {"command": "INFO", "key": "server", "time": "0.5ms"},
                {"command": "DBSIZE", "key": "*", "time": "0.3ms"},
                {"command": "KEYS", "key": "*", "time": "1.2ms"}
            ]
        
        return {
            "total_commands": total_commands,
            "ops_per_sec": instantaneous_ops,
            "recent_commands": recent_commands,
            "avg_latency": latency_stats["avg_latency"],
            "latency_data": latency_stats["latency_data"],
            "min_latency": latency_stats["min_latency"],
            "max_latency": latency_stats["max_latency"],
            "sample_count": latency_stats["sample_count"]
        }
    except Exception as e:
        logger.error(f"Error getting Redis stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/performance", dependencies=[Depends(verify_token)])
async def get_performance_metrics(range: str = "24h"):
    """Get response performance metrics"""
    try:
        # Parse time range
        if range == "1h":
            hours = 1
        elif range == "24h":
            hours = 24
        elif range == "7d":
            hours = 24 * 7
        else:
            hours = 24  # Default to 24 hours
        
        metrics = PerformanceTracker.get_performance_metrics(hours)
        return metrics
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.delete("/security/blocked-ips/{ip}", dependencies=[Depends(verify_token)])
async def unblock_ip(ip: str):
    """Unblock a specific IP address"""
    try:
        # Remove from Redis
        block_key = f"meta-glasses:security:blocked_ip:{ip}"
        violations_key = f"meta-glasses:security:violations:{ip}"
        
        deleted_block = r.delete(block_key)
        deleted_violations = r.delete(violations_key)
        
        return {
            "success": True,
            "ip": ip,
            "block_removed": bool(deleted_block),
            "violations_cleared": bool(deleted_violations),
            "message": f"IP {ip} has been unblocked"
        }
    except Exception as e:
        logger.error(f"Error unblocking IP {ip}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/security/blocked-ips", dependencies=[Depends(verify_token)])
async def get_blocked_ips():
    """Get all currently blocked IPs"""
    try:
        # Find all blocked IP keys
        blocked_keys = r.keys("meta-glasses:security:blocked_ip:*")
        blocked_ips = []
        
        for key in blocked_keys:
            ip = key.decode().split(":")[-1]
            ttl = r.ttl(key)
            reason = r.get(key)
            
            blocked_ips.append({
                "ip": ip,
                "reason": reason.decode() if reason else "unknown",
                "ttl_seconds": ttl,
                "expires_in": f"{ttl // 3600}h {(ttl % 3600) // 60}m" if ttl > 0 else "permanent"
            })
        
        return {
            "blocked_ips": blocked_ips,
            "total": len(blocked_ips)
        }
    except Exception as e:
        logger.error(f"Error getting blocked IPs: {e}")
        raise HTTPException(status_code=500, detail=str(e))