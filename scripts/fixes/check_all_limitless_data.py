#!/usr/bin/env python3
"""
Check ALL Limitless-related data in Redis to find where Unknown speakers might be hiding.
"""

import json
import logging
from utils.redis_utils import r as redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_all_limitless_data():
    """Check all possible Limitless data locations."""
    
    # Possible key patterns where Limitless data might be stored
    patterns = [
        "meta-glasses:limitless:*",
        "*limitless*",
        "*lifelog*",
        "*speaker*",
        "*recording*"
    ]
    
    all_keys = set()
    
    logger.info("🔍 Scanning ALL possible Limitless data locations...")
    
    for pattern in patterns:
        logger.info(f"\nChecking pattern: {pattern}")
        count = 0
        
        for key in redis_client.scan_iter(match=pattern):
            all_keys.add(key)
            count += 1
            
            # Decode key if it's bytes
            key_str = key.decode() if isinstance(key, bytes) else key
            
            # Special check for lifelog keys
            if 'lifelog' in key_str:
                data = redis_client.get(key)
                if data:
                    try:
                        log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                        
                        # Quick check for Unknown speakers
                        extracted = log_data.get('extracted', {})
                        people = extracted.get('people', [])
                        
                        for person in people:
                            name = person.get('name', '')
                            if name.lower() in ['unknown', 'unknown speaker']:
                                logger.warning(f"  ⚠️  FOUND Unknown speaker in key: {key_str}")
                                logger.info(f"     ID: {log_data.get('id', 'NO ID')}")
                                logger.info(f"     Title: {log_data.get('title', 'NO TITLE')}")
                                logger.info(f"     Person: {person}")
                                
                    except:
                        pass
        
        logger.info(f"  Found {count} keys matching '{pattern}'")
    
    logger.info(f"\n📊 Total unique keys found: {len(all_keys)}")
    
    # Group keys by type
    key_types = {}
    for key in all_keys:
        key_str = key.decode() if isinstance(key, bytes) else key
        parts = key_str.split(':')
        if len(parts) >= 3:
            key_type = ':'.join(parts[:3])
            key_types[key_type] = key_types.get(key_type, 0) + 1
    
    logger.info("\n📋 Key types found:")
    for key_type, count in sorted(key_types.items()):
        logger.info(f"  {key_type}: {count} keys")

if __name__ == "__main__":
    check_all_limitless_data()