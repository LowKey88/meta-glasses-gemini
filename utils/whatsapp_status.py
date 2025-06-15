"""WhatsApp API status and token validation utilities"""
import os
import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, Optional
import httpx
from utils.redis_utils import r

logger = logging.getLogger("uvicorn")

async def check_whatsapp_token_status() -> Dict[str, any]:
    """
    Check WhatsApp token status and get token information with caching
    Returns dict with status, expiry, and other token details
    """
    # Check cache first
    cache_key = "meta-glasses:whatsapp:status_cache"
    cached_status = r.get(cache_key)
    
    if cached_status:
        try:
            return json.loads(cached_status.decode('utf-8'))
        except Exception:
            pass  # Fall through to fresh check
    
    try:
        token = os.getenv("WHATSAPP_AUTH_TOKEN")
        phone_id = os.getenv("WHATSAPP_PHONE_ID")
        
        if not token or not phone_id:
            status = {
                "status": "error",
                "message": "Missing WhatsApp credentials",
                "is_valid": False,
                "token_present": bool(token),
                "phone_id_present": bool(phone_id),
                "last_checked": datetime.now().isoformat()
            }
            # Cache error status for 5 minutes (improved performance)
            r.setex(cache_key, 300, json.dumps(status))
            return status
        
        # Make async API call with timeout
        test_url = f"https://graph.facebook.com/v21.0/{phone_id}"
        headers = {'Authorization': f'Bearer {token}'}
        
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(test_url, headers=headers)
        
        if response.status_code == 200:
            status = {
                "status": "active",
                "is_valid": True,
                "message": "Token is valid and active",
                "api_version": "v21.0",
                "phone_id": phone_id,
                "token_type": "Long-lived token (60+ days typical validity)",
                "last_checked": datetime.now().isoformat()
            }
        elif response.status_code == 401:
            status = {
                "status": "expired",
                "is_valid": False,
                "message": "Token is expired or invalid",
                "error": response.json().get('error', {}).get('message', 'Unknown error'),
                "last_checked": datetime.now().isoformat()
            }
        else:
            status = {
                "status": "error",
                "is_valid": False,
                "message": f"API returned status {response.status_code}",
                "error": response.text,
                "last_checked": datetime.now().isoformat()
            }
        
        # Cache successful responses for 45 minutes, errors for 5 minutes (improved performance)
        cache_ttl = 2700 if status["status"] == "active" else 300
        r.setex(cache_key, cache_ttl, json.dumps(status))
        return status
            
    except httpx.TimeoutException:
        # Return cached status on timeout, or default
        status = {
            "status": "timeout",
            "is_valid": False,
            "message": "WhatsApp API timeout (>3s)",
            "error": "Request timeout",
            "last_checked": datetime.now().isoformat()
        }
        r.setex(cache_key, 300, json.dumps(status))
        return status
        
    except Exception as e:
        logger.error(f"Error checking WhatsApp token: {e}")
        status = {
            "status": "error",
            "is_valid": False,
            "message": "Network error checking token",
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }
        r.setex(cache_key, 300, json.dumps(status))
        return status

def get_cached_or_check_whatsapp_status() -> Dict[str, any]:
    """
    Fast-path function that returns cached status immediately if available,
    otherwise falls back to live check. Optimized for dashboard performance.
    """
    cache_key = "meta-glasses:whatsapp:status_cache"
    cached_status = r.get(cache_key)
    
    if cached_status:
        try:
            cached_data = json.loads(cached_status.decode('utf-8'))
            # Always return cached data if it exists and is less than 60 minutes old
            last_checked = datetime.fromisoformat(cached_data.get('last_checked', ''))
            age_minutes = (datetime.now() - last_checked).total_seconds() / 60
            
            if age_minutes < 60:  # Extended cache window for dashboard performance
                return cached_data
        except Exception:
            pass  # Fall through to live check
    
    # If no cache or cache is very old, do live check
    return check_whatsapp_token_status_sync()

def check_whatsapp_token_status_sync() -> Dict[str, any]:
    """Synchronous wrapper for async WhatsApp status check"""
    try:
        # Try to get current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, we can't use run_until_complete
            # Create a new thread to run the async function
            import concurrent.futures
            import threading
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(check_whatsapp_token_status())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=10)  # 10 second timeout
        else:
            return loop.run_until_complete(check_whatsapp_token_status())
    except RuntimeError:
        # No event loop running, create one
        return asyncio.run(check_whatsapp_token_status())
    except Exception as e:
        logger.error(f"Error in sync wrapper: {e}")
        # Return cached status or error status
        cache_key = "meta-glasses:whatsapp:status_cache"
        cached = r.get(cache_key)
        if cached:
            try:
                return json.loads(cached.decode('utf-8'))
            except Exception:
                pass
        
        return {
            "status": "error",
            "is_valid": False,
            "message": "Failed to check WhatsApp status",
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }