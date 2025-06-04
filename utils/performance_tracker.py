"""Performance tracking utility for response latency monitoring"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from utils.redis_utils import r
from utils.redis_monitor import (
    monitored_hincrby, monitored_expire, monitored_hget, monitored_hset,
    monitored_hkeys, monitored_exists
)
from utils.redis_key_builder import redis_keys

logger = logging.getLogger("uvicorn")

class PerformanceTracker:
    @staticmethod
    def track_response_performance(operation_type: str, latency: float, success: bool = True):
        """Track response performance metrics by operation type"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            hour = datetime.now().strftime('%H')
            
            # Track latency
            latency_key = redis_keys.get_performance_latency_key(today, operation_type)
            existing = monitored_hget(latency_key, hour)
            if existing:
                latencies = json.loads(existing)
                latencies.append(latency)
            else:
                latencies = [latency]
            
            # Keep last 1000 latencies per hour
            monitored_hset(latency_key, hour, json.dumps(latencies[-1000:]))
            monitored_expire(latency_key, 86400 * 7)  # Keep for 7 days
            
            # Track success/error counts
            count_key = redis_keys.get_performance_count_key(today, operation_type)
            if success:
                monitored_hincrby(count_key, f"{hour}_success", 1)
            else:
                monitored_hincrby(count_key, f"{hour}_error", 1)
            monitored_expire(count_key, 86400 * 7)
            
            logger.debug(f"Tracked {operation_type} performance: {latency:.2f}s, success: {success}")
            
        except Exception as e:
            logger.error(f"Error tracking response performance: {e}")
    
    @staticmethod
    def get_performance_metrics(hours: int = 24) -> Dict:
        """Get performance metrics for the specified time window"""
        try:
            now = datetime.now()
            
            # Collect data for the time window
            all_latencies = []
            category_data = {}
            hourly_data = []
            alerts = []
            
            # Operation types to track
            operation_types = ['AI Response', 'Calendar', 'Task', 'Automation', 'Search', 'Image', 'Notion', 'Other']
            
            for i in range(hours):
                hour_time = now - timedelta(hours=i)
                day_str = hour_time.strftime('%Y-%m-%d')
                hour_str = hour_time.strftime('%H')
                
                hour_latencies = []
                hour_requests = 0
                
                for op_type in operation_types:
                    # Get latency data
                    latency_key = redis_keys.get_performance_latency_key(day_str, op_type)
                    latency_data = monitored_hget(latency_key, hour_str)
                    
                    # Get count data
                    count_key = redis_keys.get_performance_count_key(day_str, op_type)
                    success_count = int(monitored_hget(count_key, f"{hour_str}_success") or 0)
                    error_count = int(monitored_hget(count_key, f"{hour_str}_error") or 0)
                    total_count = success_count + error_count
                    
                    if latency_data:
                        latencies = json.loads(latency_data)
                        hour_latencies.extend(latencies)
                        all_latencies.extend(latencies)
                        
                        # Build category data
                        if op_type not in category_data:
                            category_data[op_type] = {
                                'category': op_type,
                                'latencies': [],
                                'success_count': 0,
                                'error_count': 0
                            }
                        
                        category_data[op_type]['latencies'].extend(latencies)
                        category_data[op_type]['success_count'] += success_count
                        category_data[op_type]['error_count'] += error_count
                    
                    hour_requests += total_count
                
                # Add hourly data point
                if hour_latencies:
                    avg_latency = sum(hour_latencies) / len(hour_latencies)
                else:
                    avg_latency = 0
                
                # Format hour label
                if hour_time.date() == now.date():
                    hour_label = hour_time.strftime('%H:00')
                elif hour_time.date() == (now - timedelta(days=1)).date():
                    hour_label = f"Y-{hour_time.strftime('%H:00')}"
                else:
                    hour_label = hour_time.strftime('%a %H:00')
                
                hourly_data.append({
                    'hour': hour_label,
                    'avgLatency': round(avg_latency, 2),
                    'requestCount': hour_requests
                })
            
            # Reverse to show oldest to newest
            hourly_data.reverse()
            
            # Calculate overall metrics
            if all_latencies:
                avg_latency = sum(all_latencies) / len(all_latencies)
                sorted_latencies = sorted(all_latencies)
                p95_index = int(len(sorted_latencies) * 0.95)
                p95_latency = sorted_latencies[p95_index] if sorted_latencies else 0
            else:
                avg_latency = 0
                p95_latency = 0
            
            # Calculate category breakdown and check for alerts
            category_breakdown = []
            total_errors = 0
            total_requests = 0
            
            for op_type, data in category_data.items():
                if data['latencies']:
                    avg_cat_latency = sum(data['latencies']) / len(data['latencies'])
                    total_cat_requests = data['success_count'] + data['error_count']
                    error_rate = data['error_count'] / total_cat_requests if total_cat_requests > 0 else 0
                    
                    category_breakdown.append({
                        'category': op_type,
                        'avgLatency': round(avg_cat_latency, 2),
                        'count': total_cat_requests,
                        'errorRate': round(error_rate, 3)
                    })
                    
                    total_errors += data['error_count']
                    total_requests += total_cat_requests
                    
                    # Check for performance alerts
                    expected_latencies = {
                        'AI Response': 8,
                        'Calendar': 5,
                        'Task': 3,
                        'Automation': 4,
                        'Search': 10,
                        'Image': 12,
                        'Notion': 6,
                        'Other': 3
                    }
                    
                    expected_max = expected_latencies.get(op_type, 5)
                    if avg_cat_latency > expected_max * 1.5:
                        alerts.append({
                            'category': op_type,
                            'message': f'Response time ({avg_cat_latency:.2f}s) is {((avg_cat_latency / expected_max - 1) * 100):.0f}% slower than expected',
                            'severity': 'error'
                        })
                    elif avg_cat_latency > expected_max:
                        alerts.append({
                            'category': op_type,
                            'message': f'Response time ({avg_cat_latency:.2f}s) is above expected threshold ({expected_max}s)',
                            'severity': 'warning'
                        })
                    
                    if error_rate > 0.1:  # More than 10% error rate
                        alerts.append({
                            'category': op_type,
                            'message': f'High error rate: {(error_rate * 100):.1f}%',
                            'severity': 'error' if error_rate > 0.2 else 'warning'
                        })
            
            # Sort category breakdown by count (most used first)
            category_breakdown.sort(key=lambda x: x['count'], reverse=True)
            
            # Calculate overall error rate
            overall_error_rate = total_errors / total_requests if total_requests > 0 else 0
            
            return {
                'responseLatency': {
                    'avg': round(avg_latency, 2),
                    'p95': round(p95_latency, 2),
                    'errorRate': round(overall_error_rate, 3)
                },
                'categoryBreakdown': category_breakdown,
                'hourlyData': hourly_data,
                'alerts': alerts
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {
                'responseLatency': {'avg': 0, 'p95': 0, 'errorRate': 0},
                'categoryBreakdown': [],
                'hourlyData': [],
                'alerts': []
            }