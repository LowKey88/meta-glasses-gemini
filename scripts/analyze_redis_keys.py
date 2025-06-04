#!/usr/bin/env python3
"""
Redis Key Analysis Script

Analyzes existing Redis keys to understand current usage patterns
before running migration. This helps plan the migration strategy.
"""

import sys
import os
import json
import base64
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_utils import r

class RedisAnalyzer:
    """Analyzes Redis keys and data patterns."""
    
    def __init__(self):
        self.old_prefix = "josancamon:rayban-meta-glasses-api"
        self.analysis_results = {
            'total_keys': 0,
            'old_pattern_keys': 0,
            'new_pattern_keys': 0,
            'other_keys': 0,
            'key_types': defaultdict(int),
            'key_sizes': [],
            'ttl_distribution': defaultdict(int),
            'sample_keys': []
        }
    
    def analyze_key_pattern(self, key: str) -> str:
        """Analyze a key and categorize its pattern."""
        if key.startswith(self.old_prefix):
            suffix = key[len(self.old_prefix):].lstrip(":")
            parts = suffix.split(":")
            
            if len(parts) == 1:
                # Likely cache key (base64 encoded)
                try:
                    base64.b64decode(parts[0]).decode('utf-8')
                    return "cache"
                except:
                    return "unknown_old"
            elif len(parts) == 2:
                if parts[0] == "reminder":
                    return "reminder"
                elif parts[0] in ["conversation_history", "user_profile"]:
                    return f"user_{parts[0]}"
                else:
                    return f"user_{parts[0]}"
            elif len(parts) == 3 and parts[0] == "cancellation":
                return "cancellation_state"
            else:
                return "unknown_old"
        elif key.startswith("meta-glasses:"):
            # New pattern key
            parts = key.split(":")
            if len(parts) >= 3:
                return f"new_{parts[1]}_{parts[2]}"
            return "new_unknown"
        elif key.startswith("memory:"):
            return "memory_old"
        elif key.startswith("metrics:"):
            return "metrics_old"
        elif key.startswith("redis_monitor:"):
            return "monitor_old"
        else:
            return "other"
    
    def analyze_all_keys(self) -> None:
        """Analyze all Redis keys."""
        print("🔍 Analyzing Redis keys...")
        
        # Get all keys
        all_keys = []
        for key in r.scan_iter(match="*"):
            key_str = key.decode() if isinstance(key, bytes) else key
            all_keys.append(key_str)
        
        self.analysis_results['total_keys'] = len(all_keys)
        print(f"Found {len(all_keys)} total keys")
        
        # Analyze each key
        for key in all_keys:
            # Categorize key pattern
            pattern = self.analyze_key_pattern(key)
            self.analysis_results['key_types'][pattern] += 1
            
            # Count by prefix
            if key.startswith(self.old_prefix):
                self.analysis_results['old_pattern_keys'] += 1
            elif key.startswith("meta-glasses:"):
                self.analysis_results['new_pattern_keys'] += 1
            else:
                self.analysis_results['other_keys'] += 1
            
            # Analyze key properties
            try:
                # Get key size
                value = r.get(key)
                if value:
                    size = len(value) if isinstance(value, bytes) else len(str(value))
                    self.analysis_results['key_sizes'].append(size)
                
                # Get TTL
                ttl = r.ttl(key)
                if ttl == -1:
                    self.analysis_results['ttl_distribution']['permanent'] += 1
                elif ttl == -2:
                    self.analysis_results['ttl_distribution']['not_exists'] += 1
                elif ttl > 0:
                    if ttl < 60:
                        self.analysis_results['ttl_distribution']['< 1 min'] += 1
                    elif ttl < 3600:
                        self.analysis_results['ttl_distribution']['< 1 hour'] += 1
                    elif ttl < 86400:
                        self.analysis_results['ttl_distribution']['< 1 day'] += 1
                    else:
                        self.analysis_results['ttl_distribution']['> 1 day'] += 1
                
                # Sample keys for each pattern
                if len(self.analysis_results['sample_keys']) < 50:
                    self.analysis_results['sample_keys'].append({
                        'key': key,
                        'pattern': pattern,
                        'size': size if 'size' in locals() else 0,
                        'ttl': ttl
                    })
                    
            except Exception as e:
                print(f"Error analyzing key {key}: {e}")
    
    def generate_report(self) -> None:
        """Generate analysis report."""
        print("\n" + "=" * 80)
        print("REDIS KEY ANALYSIS REPORT")
        print("=" * 80)
        
        # Overall statistics
        print(f"📊 OVERALL STATISTICS:")
        print(f"  Total Keys: {self.analysis_results['total_keys']}")
        print(f"  Old Pattern Keys: {self.analysis_results['old_pattern_keys']}")
        print(f"  New Pattern Keys: {self.analysis_results['new_pattern_keys']}")
        print(f"  Other Keys: {self.analysis_results['other_keys']}")
        
        # Key types breakdown
        print(f"\n🏷️  KEY TYPES:")
        for key_type, count in sorted(self.analysis_results['key_types'].items(), 
                                     key=lambda x: x[1], reverse=True):
            percentage = (count / self.analysis_results['total_keys']) * 100
            print(f"  {key_type}: {count} ({percentage:.1f}%)")
        
        # Size statistics
        if self.analysis_results['key_sizes']:
            sizes = self.analysis_results['key_sizes']
            print(f"\n📦 KEY SIZE STATISTICS:")
            print(f"  Average Size: {sum(sizes) / len(sizes):.1f} bytes")
            print(f"  Min Size: {min(sizes)} bytes")
            print(f"  Max Size: {max(sizes)} bytes")
            print(f"  Total Data: {sum(sizes) / 1024:.1f} KB")
        
        # TTL distribution
        print(f"\n⏰ TTL DISTRIBUTION:")
        for ttl_range, count in self.analysis_results['ttl_distribution'].items():
            percentage = (count / self.analysis_results['total_keys']) * 100
            print(f"  {ttl_range}: {count} ({percentage:.1f}%)")
        
        # Migration impact
        print(f"\n🔄 MIGRATION IMPACT:")
        old_keys = self.analysis_results['old_pattern_keys']
        if old_keys > 0:
            print(f"  Keys requiring migration: {old_keys}")
            print(f"  Keys already in new format: {self.analysis_results['new_pattern_keys']}")
            print(f"  Migration coverage: {(old_keys / self.analysis_results['total_keys']) * 100:.1f}%")
        else:
            print("  ✅ No keys found that require migration!")
        
        # Sample keys
        print(f"\n🔍 SAMPLE KEYS (first 10):")
        for sample in self.analysis_results['sample_keys'][:10]:
            ttl_str = f"TTL:{sample['ttl']}" if sample['ttl'] > 0 else "permanent"
            print(f"  [{sample['pattern']}] {sample['key']} ({sample['size']}b, {ttl_str})")
        
        # Old pattern breakdown
        old_patterns = {k: v for k, v in self.analysis_results['key_types'].items() 
                       if not k.startswith('new_') and k != 'other'}
        if old_patterns:
            print(f"\n🔧 OLD PATTERN BREAKDOWN:")
            for pattern, count in sorted(old_patterns.items(), key=lambda x: x[1], reverse=True):
                print(f"  {pattern}: {count} keys")
        
        print("\n" + "=" * 80)
        
        # Save detailed report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f'redis_analysis_{timestamp}.json'
        
        try:
            with open(report_file, 'w') as f:
                # Convert defaultdict to regular dict for JSON serialization
                report_data = {
                    'analysis_results': {
                        'total_keys': self.analysis_results['total_keys'],
                        'old_pattern_keys': self.analysis_results['old_pattern_keys'],
                        'new_pattern_keys': self.analysis_results['new_pattern_keys'],
                        'other_keys': self.analysis_results['other_keys'],
                        'key_types': dict(self.analysis_results['key_types']),
                        'key_sizes': self.analysis_results['key_sizes'],
                        'ttl_distribution': dict(self.analysis_results['ttl_distribution']),
                        'sample_keys': self.analysis_results['sample_keys']
                    },
                    'timestamp': datetime.now().isoformat()
                }
                json.dump(report_data, f, indent=2)
            print(f"📄 Detailed report saved to: {report_file}")
        except Exception as e:
            print(f"❌ Failed to save report: {e}")


def main():
    """Main analysis function."""
    try:
        analyzer = RedisAnalyzer()
        analyzer.analyze_all_keys()
        analyzer.generate_report()
        
        print(f"\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()