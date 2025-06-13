"""AI API status and monitoring utilities"""
import os
import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
import httpx
from utils.redis_utils import r

logger = logging.getLogger("uvicorn")

async def check_gemini_api_status() -> Dict[str, any]:
    """
    Check Gemini AI API status and rate limits with caching
    Returns dict with status, rate limits, response times, and error info
    """
    # Check cache first (15-minute cache for better performance)
    cache_key = "meta-glasses:ai:gemini_status_cache"
    cached_status = r.get(cache_key)
    
    if cached_status:
        try:
            return json.loads(cached_status.decode('utf-8'))
        except Exception:
            pass  # Fall through to fresh check
    
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            status = {
                "status": "error",
                "message": "Missing Gemini API key",
                "is_available": False,
                "api_key_present": False,
                "last_checked": datetime.now().isoformat()
            }
            # Cache error for 5 minutes (improved performance)
            r.setex(cache_key, 300, json.dumps(status))
            return status
        
        # Test Gemini API with a minimal request (models endpoint)
        test_url = "https://generativelanguage.googleapis.com/v1beta/models"
        headers = {'x-goog-api-key': api_key}
        
        start_time = datetime.now()
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(test_url, headers=headers)
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000  # ms
            
            # Additional test: Try a minimal generation request to check for rate limiting
            generation_status = "unknown"
            generation_error = None
            
            try:
                # Test generation endpoint with minimal request using same client
                gen_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
                gen_data = {
                    "contents": [{"parts": [{"text": "Test"}]}],
                    "generationConfig": {"maxOutputTokens": 1}
                }
                gen_response = await client.post(gen_url, headers=headers, json=gen_data, timeout=3.0)
                
                if gen_response.status_code == 200:
                    generation_status = "active"
                elif gen_response.status_code == 429:
                    generation_status = "rate_limited"
                    generation_error = "Generation endpoint rate limited"
                else:
                    generation_status = "error"
                    generation_error = f"Generation endpoint status {gen_response.status_code}"
                    
            except Exception as e:
                generation_status = "error"
                generation_error = f"Generation test failed: {str(e)[:100]}"
        
        # Get rate limit info from headers (if available)
        rate_limit_info = {
            "requests_per_minute": response.headers.get("x-ratelimit-limit"),
            "remaining_requests": response.headers.get("x-ratelimit-remaining"),
            "reset_time": response.headers.get("x-ratelimit-reset")
        }
        
        if response.status_code == 200:
            # Get model info
            models_data = response.json()
            available_models = [model.get("name", "") for model in models_data.get("models", [])]
            
            # Determine overall status based on generation endpoint result
            if generation_status == "rate_limited":
                final_status = "rate_limited"
                final_message = "Gemini generation API is rate limited"
                final_available = False
                final_error = generation_error
            elif generation_status == "error":
                final_status = "degraded"
                final_message = "Models API active, but generation endpoint has issues"
                final_available = True  # Models work, generation doesn't
                final_error = generation_error
            else:
                final_status = "active"
                final_message = "Gemini API is fully active and responding"
                final_available = True
                final_error = None
            
            status = {
                "status": final_status,
                "is_available": final_available,
                "message": final_message,
                "response_time_ms": round(response_time, 2),
                "rate_limit": rate_limit_info,
                "available_models": len(available_models),
                "api_key_present": True,
                "generation_status": generation_status,
                "last_checked": datetime.now().isoformat()
            }
            
            if final_error:
                status["error"] = final_error
        elif response.status_code == 429:
            status = {
                "status": "rate_limited",
                "is_available": False,
                "message": "Gemini API rate limit exceeded",
                "response_time_ms": round(response_time, 2),
                "rate_limit": rate_limit_info,
                "error": "Rate limit exceeded",
                "retry_after": response.headers.get("retry-after"),
                "last_checked": datetime.now().isoformat()
            }
        elif response.status_code == 403:
            status = {
                "status": "unauthorized",
                "is_available": False,
                "message": "Gemini API key invalid or unauthorized",
                "error": "API key invalid",
                "last_checked": datetime.now().isoformat()
            }
        else:
            status = {
                "status": "error",
                "is_available": False,
                "message": f"Gemini API returned status {response.status_code}",
                "response_time_ms": round(response_time, 2),
                "error": response.text[:200],  # Limit error text
                "last_checked": datetime.now().isoformat()
            }
        
        # Cache successful responses for 15 minutes, errors for 5 minutes (improved performance)
        cache_ttl = 900 if status["status"] == "active" else 300
        r.setex(cache_key, cache_ttl, json.dumps(status))
        return status
            
    except httpx.TimeoutException:
        status = {
            "status": "timeout",
            "is_available": False,
            "message": "Gemini API timeout (>5s)",
            "error": "Request timeout",
            "last_checked": datetime.now().isoformat()
        }
        r.setex(cache_key, 300, json.dumps(status))
        return status
        
    except Exception as e:
        logger.error(f"Error checking Gemini API: {e}")
        status = {
            "status": "error",
            "is_available": False,
            "message": "Network error checking Gemini API",
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }
        r.setex(cache_key, 300, json.dumps(status))
        return status

def get_ai_usage_stats() -> Dict[str, any]:
    """Get AI usage statistics from Redis metrics"""
    try:
        # Get today's AI request count using hash structure (same as MetricsTracker)
        from utils.redis_key_builder import redis_keys
        today = datetime.now().strftime("%Y-%m-%d")
        ai_requests_key = redis_keys.get_ai_requests_key(today)
        
        # Sum all model types from the hash
        ai_requests_today = 0
        if r.exists(ai_requests_key):
            model_types = r.hkeys(ai_requests_key)
            for model_type in model_types:
                count = r.hget(ai_requests_key, model_type)
                if count:
                    ai_requests_today += int(count.decode('utf-8') if isinstance(count, bytes) else count)
        
        # Get recent error count (last hour)
        error_count = 0
        error_keys = r.keys("meta-glasses:ai:errors:*")
        for key in error_keys:
            try:
                error_data = r.get(key)
                if error_data:
                    error_info = json.loads(error_data.decode('utf-8'))
                    error_time = datetime.fromisoformat(error_info.get('timestamp', ''))
                    if datetime.now() - error_time < timedelta(hours=1):
                        error_count += 1
            except Exception:
                continue
        
        # Import current models from gemini config
        from utils.gemini import GEMINI_VISION_MODEL, GEMINI_CHAT_MODEL
        
        return {
            "requests_today": ai_requests_today,
            "errors_last_hour": error_count,
            "models_configured": {
                "vision_model": GEMINI_VISION_MODEL,
                "chat_model": GEMINI_CHAT_MODEL
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting AI usage stats: {e}")
        return {
            "requests_today": 0,
            "errors_last_hour": 0,
            "models_configured": {}
        }

def check_gemini_api_status_sync() -> Dict[str, any]:
    """Synchronous wrapper for async Gemini status check"""
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
                    return new_loop.run_until_complete(check_gemini_api_status())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=10)  # 10 second timeout
        else:
            return loop.run_until_complete(check_gemini_api_status())
    except RuntimeError:
        # No event loop running, create one
        return asyncio.run(check_gemini_api_status())
    except Exception as e:
        logger.error(f"Error in sync wrapper: {e}")
        # Return cached status or error status
        cache_key = "meta-glasses:ai:gemini_status_cache"
        cached = r.get(cache_key)
        if cached:
            try:
                return json.loads(cached.decode('utf-8'))
            except Exception:
                pass
        
        return {
            "status": "error",
            "is_available": False,
            "message": "Failed to check Gemini status",
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }

def record_ai_error(error_type: str, error_message: str, model: str = "unknown"):
    """Record AI API error for monitoring"""
    try:
        error_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        error_key = f"meta-glasses:ai:errors:{error_id}"
        
        error_data = {
            "type": error_type,
            "message": error_message,
            "model": model,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store error for 24 hours
        r.setex(error_key, 86400, json.dumps(error_data))
        
    except Exception as e:
        logger.error(f"Failed to record AI error: {e}")