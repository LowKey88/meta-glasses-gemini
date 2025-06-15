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

from api.dashboard.config import get_secure_jwt_secret
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder
from functionality.limitless import sync_recent_lifelogs, limitless_client, standardize_cached_speakers, get_last_sync_timestamp, process_pending_recordings
from utils.limitless_logger import limitless_routes_logger

def verify_dashboard_token(authorization: Optional[str] = Header(None)):
    """Verify JWT token for dashboard access"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    try:
        secret = get_secure_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload.get("user", "admin")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/limitless", tags=["limitless"])


async def run_sync_in_background(task_id: str, phone_number: str, sync_mode: str = "today"):
    """Run Limitless sync in background and update status in Redis."""
    try:
        # Update status to running
        status_key = f"meta-glasses:limitless:sync_status:{task_id}"
        redis_client.setex(status_key, 3600, json.dumps({
            "status": "running",
            "progress": 0,
            "message": f"Starting sync ({sync_mode})...",
            "started_at": datetime.now().isoformat()
        }))
        
        # Run the actual sync with new daily window
        result = await sync_recent_lifelogs(phone_number, sync_mode=sync_mode)
        
        # Update status to completed
        redis_client.setex(status_key, 3600, json.dumps({
            "status": "completed",
            "progress": 100,
            "message": "Sync completed successfully",
            "result": result,
            "completed_at": datetime.now().isoformat()
        }))
        
        logger.info(f"✅ Background sync {task_id} completed successfully")
        
        # Process pending recordings after main sync completion
        try:
            await process_pending_recordings(phone_number)
        except Exception as e:
            logger.error(f"Error processing pending recordings: {str(e)}")
            
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
                    
                    # ✅ CRITICAL FIX: Standardize speaker names in cached data
                    extracted_data = log_data.get('extracted', {})
                    extracted_data = standardize_cached_speakers(extracted_data)
                    
                    formatted_log = {
                        'id': log_data.get('id'),
                        'title': log_data.get('title', 'Untitled'),
                        'summary': log_data.get('summary', ''),
                        'start_time': start_time,
                        'end_time': log_data.get('end_time'),
                        'duration_minutes': 0,
                        'has_transcript': True,
                        'processed': True,
                        'extracted_data': extracted_data
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
                # ✅ CRITICAL FIX: Standardize speaker names in cached data for search
                extracted = standardize_cached_speakers(extracted)
                
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
        
        # Start sync in background with today's window (much more efficient)
        background_tasks.add_task(run_sync_in_background, task_id, phone_number, "today")
        
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


@router.get("/sync-efficiency")
async def get_sync_efficiency(
    user: str = Depends(verify_dashboard_token)
) -> Dict[str, Any]:
    """Get sync efficiency metrics and last sync information."""
    try:
        phone_number = "60122873632"
        
        # Get last sync info
        last_sync_timestamp = get_last_sync_timestamp(phone_number)
        
        # Count total processed recordings
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        total_recordings = 0
        for key in redis_client.scan_iter(match=pattern):
            total_recordings += 1
        
        # Calculate next sync prediction
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Determine sync mode for next sync
        next_sync_mode = "incremental"
        next_sync_description = "only new recordings"
        estimated_fetch_count = "2-5 recordings"
        
        if not last_sync_timestamp:
            next_sync_mode = "full"
            next_sync_description = "all recordings for time period"
            estimated_fetch_count = "20-50+ recordings"
        elif last_sync_timestamp < today_start:
            next_sync_mode = "full_day"
            next_sync_description = "all recordings since midnight"
            estimated_fetch_count = "10-30 recordings"
        
        # Get efficiency from last sync (if available)
        last_efficiency = None
        efficiency_key = f"meta-glasses:limitless:last_efficiency:{phone_number}"
        efficiency_data = redis_client.get(efficiency_key)
        if efficiency_data:
            try:
                last_efficiency = float(efficiency_data.decode() if isinstance(efficiency_data, bytes) else efficiency_data)
            except:
                pass
        
        # Check if incremental sync is active
        incremental_active = last_sync_timestamp is not None
        
        sync_info = {
            'last_sync_timestamp': last_sync_timestamp.isoformat() if last_sync_timestamp else None,
            'last_sync_age_hours': (now - last_sync_timestamp).total_seconds() / 3600 if last_sync_timestamp else None,
            'total_processed_recordings': total_recordings,
            'incremental_sync_active': incremental_active,
            'next_sync_mode': next_sync_mode,
            'next_sync_will_fetch': next_sync_description,
            'estimated_fetch_count': estimated_fetch_count,
            'last_sync_efficiency_percent': last_efficiency,
            'efficiency_status': 'optimal' if incremental_active else 'needs_initial_sync'
        }
        
        return sync_info
        
    except Exception as e:
        logger.error(f"Error getting sync efficiency: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance-metrics")
async def get_performance_metrics(
    limit: int = Query(10, description="Number of recent performance records to return"),
    range: str = Query("24h", description="Time range for metrics (24h, 7d)"),
    user: str = Depends(verify_dashboard_token)
) -> Dict[str, Any]:
    """Get performance metrics for Limitless processing operations."""
    try:
        # Parse time range
        if range == "24h":
            hours_back = 24
        elif range == "7d":
            hours_back = 24 * 7
        else:
            hours_back = 24  # Default to 24 hours
            
        # Calculate time window
        now = datetime.now()
        start_time = now - timedelta(hours=hours_back)
        
        # Get recent performance data from Redis
        pattern = "meta-glasses:limitless:performance:*"
        performance_records = []
        
        for key in redis_client.scan_iter(match=pattern):
            data = redis_client.get(key)
            if data:
                try:
                    record = json.loads(data.decode() if isinstance(data, bytes) else data)
                    # Filter by time range
                    record_time = datetime.fromisoformat(record.get('processed_at', '').replace('Z', '+00:00'))
                    if record_time >= start_time:
                        performance_records.append(record)
                except (json.JSONDecodeError, ValueError):
                    continue
        
        # Sort by processed_at timestamp (most recent first)
        performance_records.sort(key=lambda x: x.get('processed_at', ''), reverse=True)
        
        # Limit results
        recent_records = performance_records[:limit]
        
        # Calculate summary statistics
        if performance_records:
            total_times = [r.get('total_time', 0) for r in performance_records]
            avg_total_time = sum(total_times) / len(total_times)
            min_total_time = min(total_times)
            max_total_time = max(total_times)
            
            # Get timing breakdown averages
            timing_breakdowns = [r.get('timing_breakdown', {}) for r in performance_records if r.get('timing_breakdown')]
            avg_breakdown = {}
            
            if timing_breakdowns:
                # Calculate average for each operation
                # Note: natural_language_tasks is kept for backward compatibility but will be 0 for new records
                for operation in ['speaker_identification', 'natural_language_tasks', 'gemini_extraction', 'memory_creation', 'tasks_creation', 'redis_caching']:
                    times = [breakdown.get(operation, 0) for breakdown in timing_breakdowns if breakdown.get(operation, 0) > 0]
                    if times:
                        avg_breakdown[operation] = sum(times) / len(times)
                        avg_breakdown[f"{operation}_count"] = len(times)
            
            # Identify bottlenecks
            bottleneck_analysis = {}
            if avg_breakdown:
                total_avg = sum(avg_breakdown.get(op, 0) for op in ['speaker_identification', 'natural_language_tasks', 'gemini_extraction', 'memory_creation', 'tasks_creation', 'redis_caching'])
                if total_avg > 0:
                    for operation in ['speaker_identification', 'natural_language_tasks', 'gemini_extraction', 'memory_creation', 'tasks_creation', 'redis_caching']:
                        if operation in avg_breakdown:
                            percentage = (avg_breakdown[operation] / total_avg) * 100
                            bottleneck_analysis[operation] = {
                                'avg_time': avg_breakdown[operation],
                                'percentage': percentage,
                                'is_bottleneck': percentage > 30  # Mark as bottleneck if >30% of total time
                            }
            
            # Check for performance issues
            performance_issues = []
            if avg_total_time > 60:  # Over 1 minute average
                performance_issues.append(f"High average processing time: {avg_total_time:.1f}s")
            if max_total_time > 300:  # Over 5 minutes max
                performance_issues.append(f"Very slow processing detected: {max_total_time:.1f}s max")
            
            # Check for specific operation bottlenecks
            for operation, analysis in bottleneck_analysis.items():
                if analysis['is_bottleneck'] and analysis['avg_time'] > 30:
                    performance_issues.append(f"{operation.replace('_', ' ').title()} is a bottleneck: {analysis['avg_time']:.1f}s ({analysis['percentage']:.1f}%)")
            
            # Get processing trends (last 24 hours)
            twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
            recent_performance = [
                r for r in performance_records 
                if datetime.fromisoformat(r.get('processed_at', '').replace('Z', '+00:00')) > twenty_four_hours_ago
            ]
            
            current_status = "optimal"
            if performance_issues:
                current_status = "issues_detected"
            elif avg_total_time > 30:
                current_status = "suboptimal"
            
            summary = {
                'total_records': len(performance_records),
                'records_last_24h': len(recent_performance),
                'avg_processing_time': avg_total_time,
                'min_processing_time': min_total_time,
                'max_processing_time': max_total_time,
                'current_status': current_status,
                'performance_issues': performance_issues,
                'timing_breakdown_avg': avg_breakdown,
                'bottleneck_analysis': bottleneck_analysis
            }
        else:
            summary = {
                'total_records': 0,
                'records_last_24h': 0,
                'avg_processing_time': 0,
                'min_processing_time': 0,
                'max_processing_time': 0,
                'current_status': 'no_data',
                'performance_issues': [],
                'timing_breakdown_avg': {},
                'bottleneck_analysis': {}
            }
        
        # Generate hourly data for time-based charts
        hourly_data = []
        category_breakdown = []
        
        if performance_records:
            # Create hourly buckets
            hourly_buckets = {}
            category_stats = {}
            
            # Define operation categories for breakdown
            operation_categories = [
                'speaker_identification',
                'natural_language_tasks', 
                'gemini_extraction',
                'memory_creation',
                'tasks_creation',
                'redis_caching'
            ]
            
            # Initialize category stats
            for category in operation_categories:
                category_stats[category] = {
                    'times': [],
                    'count': 0
                }
            
            # Process each performance record
            for record in performance_records:
                try:
                    record_time = datetime.fromisoformat(record.get('processed_at', '').replace('Z', '+00:00'))
                    timing_breakdown = record.get('timing_breakdown', {})
                    total_time = record.get('total_time', 0)
                    
                    # Create hour bucket key
                    if range == "7d":
                        # For 7 days, group by day
                        hour_key = record_time.strftime('%Y-%m-%d')
                        hour_label = record_time.strftime('%a %m/%d')
                    else:
                        # For 24h, group by hour
                        hour_key = record_time.strftime('%Y-%m-%d %H')
                        if record_time.date() == now.date():
                            hour_label = record_time.strftime('%H:00')
                        else:
                            hour_label = f"Y-{record_time.strftime('%H:00')}"
                    
                    # Add to hourly bucket
                    if hour_key not in hourly_buckets:
                        hourly_buckets[hour_key] = {
                            'label': hour_label,
                            'times': [],
                            'count': 0
                        }
                    
                    hourly_buckets[hour_key]['times'].append(total_time)
                    hourly_buckets[hour_key]['count'] += 1
                    
                    # Add to category stats
                    for category in operation_categories:
                        if category in timing_breakdown:
                            category_stats[category]['times'].append(timing_breakdown[category])
                            category_stats[category]['count'] += 1
                            
                except (ValueError, KeyError):
                    continue
            
            # Generate hourly data points
            for hour_key in sorted(hourly_buckets.keys()):
                bucket = hourly_buckets[hour_key]
                if bucket['times']:
                    avg_latency = sum(bucket['times']) / len(bucket['times'])
                else:
                    avg_latency = 0
                    
                hourly_data.append({
                    'hour': bucket['label'],
                    'avgLatency': round(avg_latency, 2),
                    'requestCount': bucket['count']
                })
            
            # Generate category breakdown
            for category in operation_categories:
                stats = category_stats[category]
                if stats['times']:
                    avg_time = sum(stats['times']) / len(stats['times'])
                    
                    # Convert category name to display format
                    display_name = category.replace('_', ' ').title()
                    if category == 'gemini_extraction':
                        display_name = 'Combined AI Extraction'  # Updated to reflect it includes tasks
                    elif category == 'speaker_identification':
                        display_name = 'Speaker Identification'
                    elif category == 'natural_language_tasks':
                        display_name = 'Natural Language Tasks (Legacy)'  # Mark as legacy
                    elif category == 'memory_creation':
                        display_name = 'Memory Creation'
                    elif category == 'tasks_creation':
                        display_name = 'Task Creation'
                    elif category == 'redis_caching':
                        display_name = 'Redis Caching'
                    
                    category_breakdown.append({
                        'category': display_name,
                        'avgLatency': round(avg_time, 2),
                        'count': stats['count'],
                        'errorRate': 0  # For future use
                    })
            
            # Sort category breakdown by average latency (highest first)
            category_breakdown.sort(key=lambda x: x['avgLatency'], reverse=True)
        
        return {
            'summary': summary,
            'recent_records': recent_records,
            'hourlyData': hourly_data,
            'categoryBreakdown': category_breakdown,
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def count_total_processed_recordings() -> int:
    """Count total processed recordings in cache."""
    try:
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        count = 0
        for key in redis_client.scan_iter(match=pattern):
            count += 1
        return count
    except Exception as e:
        logger.error(f"Error counting recordings: {str(e)}")
        return 0
