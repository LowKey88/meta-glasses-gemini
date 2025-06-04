"""
Redis Command Monitoring and Latency Tracking
Wraps Redis operations to track commands and measure execution times.
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional
from collections import deque
from datetime import datetime
from utils.redis_utils import r

logger = logging.getLogger("uvicorn")

class RedisMonitor:
    """Monitor Redis commands and track latency metrics."""
    
    def __init__(self, max_commands: int = 100):
        self.max_commands = max_commands
        self.recent_commands = deque(maxlen=max_commands)
        self.latency_samples = deque(maxlen=max_commands)
        
    def _log_command(self, command: str, key: str, duration_ms: float, success: bool = True):
        """Log a Redis command with its execution time."""
        try:
            # Ensure key is a string (handle bytes objects)
            if isinstance(key, bytes):
                key = key.decode('utf-8', errors='ignore')
            elif not isinstance(key, str):
                key = str(key)
            
            # Truncate long keys for display
            display_key = key
            if len(key) > 30:
                display_key = key[:27] + "..."
            
            command_entry = {
                "command": command.upper(),
                "key": display_key,
                "time": f"{duration_ms:.1f}ms",
                "timestamp": datetime.now().isoformat(),
                "success": success
            }
            
            # Add to recent commands (thread-safe deque)
            self.recent_commands.append(command_entry)
            
            # Add to latency samples
            self.latency_samples.append(duration_ms)
            
            # Also store in Redis for persistence across restarts
            try:
                # Store last 20 commands in Redis
                redis_key = "redis_monitor:recent_commands"
                commands_list = list(self.recent_commands)[-20:]  # Keep last 20
                r.set(redis_key, json.dumps(commands_list), ex=3600)  # Expire in 1 hour
                
                # Store latency samples
                latency_key = "redis_monitor:latency_samples"
                latency_list = list(self.latency_samples)[-50:]  # Keep last 50
                r.set(latency_key, json.dumps(latency_list), ex=3600)
                
            except Exception as e:
                logger.debug(f"Failed to store monitoring data in Redis: {e}")
                
        except Exception as e:
            logger.error(f"Failed to log Redis command: {e}")
    
    def execute_with_monitoring(self, command: str, key: str, operation_func, *args, **kwargs):
        """Execute a Redis operation with monitoring."""
        start_time = time.perf_counter()
        success = True
        result = None
        
        try:
            result = operation_func(*args, **kwargs)
        except Exception as e:
            success = False
            logger.error(f"Redis operation failed: {command} {key} - {e}")
            raise
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self._log_command(command, key, duration_ms, success)
            
        return result
    
    def get_recent_commands(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent Redis commands."""
        try:
            # Try to load from Redis first (for persistence)
            try:
                redis_data = r.get("redis_monitor:recent_commands")
                if redis_data:
                    stored_commands = json.loads(redis_data)
                    # Merge with in-memory commands
                    all_commands = stored_commands + list(self.recent_commands)
                    # Remove duplicates and keep most recent
                    unique_commands = []
                    seen_timestamps = set()
                    for cmd in reversed(all_commands):
                        if cmd.get('timestamp') not in seen_timestamps:
                            unique_commands.append(cmd)
                            seen_timestamps.add(cmd.get('timestamp'))
                        if len(unique_commands) >= limit:
                            break
                    return unique_commands[:limit]
            except Exception:
                pass
            
            # Fallback to in-memory data
            return list(self.recent_commands)[-limit:]
        except Exception as e:
            logger.error(f"Failed to get recent commands: {e}")
            return []
    
    def get_latency_stats(self) -> Dict[str, Any]:
        """Get latency statistics."""
        try:
            # Try to load from Redis first
            try:
                redis_data = r.get("redis_monitor:latency_samples")
                if redis_data:
                    stored_samples = json.loads(redis_data)
                    all_samples = stored_samples + list(self.latency_samples)
                else:
                    all_samples = list(self.latency_samples)
            except Exception:
                all_samples = list(self.latency_samples)
            
            if not all_samples:
                return {
                    "avg_latency": "< 1ms",
                    "min_latency": 0,
                    "max_latency": 0,
                    "sample_count": 0,
                    "latency_data": []
                }
            
            avg_latency = sum(all_samples) / len(all_samples)
            min_latency = min(all_samples)
            max_latency = max(all_samples)
            
            # Format average latency
            if avg_latency < 1:
                avg_latency_str = "< 1ms"
            else:
                avg_latency_str = f"{avg_latency:.1f}ms"
            
            return {
                "avg_latency": avg_latency_str,
                "min_latency": min_latency,
                "max_latency": max_latency,
                "sample_count": len(all_samples),
                "latency_data": all_samples[-20:]  # Last 20 samples for graphing
            }
        except Exception as e:
            logger.error(f"Failed to get latency stats: {e}")
            return {
                "avg_latency": "< 1ms",
                "min_latency": 0,
                "max_latency": 0,
                "sample_count": 0,
                "latency_data": []
            }

# Global monitor instance
redis_monitor = RedisMonitor()

# Wrapper functions for common Redis operations
def monitored_get(key: str):
    """Monitored Redis GET operation."""
    return redis_monitor.execute_with_monitoring("GET", key, r.get, key)

def monitored_set(key: str, value: Any, **kwargs):
    """Monitored Redis SET operation."""
    return redis_monitor.execute_with_monitoring("SET", key, r.set, key, value, **kwargs)

def monitored_delete(key: str):
    """Monitored Redis DELETE operation."""
    return redis_monitor.execute_with_monitoring("DEL", key, r.delete, key)

def monitored_hget(name: str, key: str):
    """Monitored Redis HGET operation."""
    return redis_monitor.execute_with_monitoring("HGET", f"{name}:{key}", r.hget, name, key)

def monitored_hset(name: str, key: str, value: Any):
    """Monitored Redis HSET operation."""
    return redis_monitor.execute_with_monitoring("HSET", f"{name}:{key}", r.hset, name, key, value)

def monitored_keys(pattern: str = "*"):
    """Monitored Redis KEYS operation."""
    return redis_monitor.execute_with_monitoring("KEYS", pattern, r.keys, pattern)

def monitored_exists(key: str):
    """Monitored Redis EXISTS operation."""
    return redis_monitor.execute_with_monitoring("EXISTS", key, r.exists, key)

def monitored_ttl(key: str):
    """Monitored Redis TTL operation."""
    return redis_monitor.execute_with_monitoring("TTL", key, r.ttl, key)

def monitored_expire(key: str, time: int):
    """Monitored Redis EXPIRE operation."""
    return redis_monitor.execute_with_monitoring("EXPIRE", key, r.expire, key, time)

def monitored_hincrby(name: str, key: str, amount: int = 1):
    """Monitored Redis HINCRBY operation."""
    return redis_monitor.execute_with_monitoring("HINCRBY", f"{name}:{key}", r.hincrby, name, key, amount)

def monitored_hkeys(name: str):
    """Monitored Redis HKEYS operation."""
    return redis_monitor.execute_with_monitoring("HKEYS", name, r.hkeys, name)

def monitored_expireat(key: str, when: int):
    """Monitored Redis EXPIREAT operation."""
    return redis_monitor.execute_with_monitoring("EXPIREAT", key, r.expireat, key, when)

def monitored_sadd(key: str, *values):
    """Monitored Redis SADD operation."""
    return redis_monitor.execute_with_monitoring("SADD", key, r.sadd, key, *values)

def monitored_smembers(key: str):
    """Monitored Redis SMEMBERS operation."""
    return redis_monitor.execute_with_monitoring("SMEMBERS", key, r.smembers, key)

def monitored_scan_iter(pattern: str = "*"):
    """Monitored Redis SCAN_ITER operation."""
    # For scan_iter, we need to handle it differently since it returns an iterator
    start_time = time.perf_counter()
    try:
        result = r.scan_iter(match=pattern)
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        redis_monitor._log_command("SCAN", pattern, duration_ms, True)
        return result
    except Exception as e:
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        redis_monitor._log_command("SCAN", pattern, duration_ms, False)
        raise