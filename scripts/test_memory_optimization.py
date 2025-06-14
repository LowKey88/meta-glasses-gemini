#!/usr/bin/env python3
"""
Test the memory optimization by triggering a Limitless sync and analyzing results.
"""

import requests
import json
import time
from datetime import datetime

# API configuration
API_BASE = "http://localhost:8111"
PHONE_NUMBER = "+60123456789"  # Replace with your phone number

def trigger_limitless_sync():
    """Trigger a Limitless sync via WhatsApp command simulation."""
    print("\n🔄 Triggering Limitless sync...")
    
    # Send sync command
    response = requests.post(
        f"{API_BASE}/webhook",
        json={
            "from": PHONE_NUMBER,
            "text": "sync limitless today"
        }
    )
    
    if response.status_code == 200:
        print("✅ Sync command sent successfully")
        return True
    else:
        print(f"❌ Failed to send sync command: {response.status_code}")
        return False

def get_memory_stats():
    """Get memory statistics from the dashboard API."""
    try:
        response = requests.get(f"{API_BASE}/api/dashboard/stats")
        if response.status_code == 200:
            data = response.json()
            return {
                'total_memories': data.get('total_memories', 0),
                'memory_breakdown': data.get('memory_breakdown', {})
            }
        else:
            print(f"Failed to get stats: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting stats: {e}")
        return None

def get_recent_memories(limit=10):
    """Get recent memories to analyze content."""
    try:
        response = requests.get(f"{API_BASE}/api/dashboard/memories?limit={limit}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get memories: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error getting memories: {e}")
        return []

def analyze_memory_creation():
    """Analyze memory creation patterns."""
    print("\n📊 Analyzing memory creation...")
    
    # Get initial stats
    initial_stats = get_memory_stats()
    if initial_stats:
        print(f"\nInitial memory count: {initial_stats['total_memories']}")
        print(f"Memory breakdown: {json.dumps(initial_stats['memory_breakdown'], indent=2)}")
    
    # Trigger sync
    if not trigger_limitless_sync():
        return
    
    # Wait for processing
    print("\n⏳ Waiting for sync to complete (30 seconds)...")
    time.sleep(30)
    
    # Get updated stats
    final_stats = get_memory_stats()
    if final_stats and initial_stats:
        new_memories = final_stats['total_memories'] - initial_stats['total_memories']
        print(f"\n📈 Results:")
        print(f"New memories created: {new_memories}")
        print(f"Final memory count: {final_stats['total_memories']}")
        print(f"Updated breakdown: {json.dumps(final_stats['memory_breakdown'], indent=2)}")
        
        # Get and analyze recent memories
        recent_memories = get_recent_memories(new_memories if new_memories > 0 else 5)
        if recent_memories:
            print(f"\n🔍 Recent memories ({len(recent_memories)} shown):")
            for i, memory in enumerate(recent_memories[:5], 1):
                print(f"\n{i}. Type: {memory.get('type')}")
                print(f"   Content: {memory.get('content', '')[:100]}...")
                metadata = memory.get('metadata', {})
                if metadata.get('is_consolidated'):
                    print(f"   ✅ Consolidated memory")
                    print(f"   Facts: {metadata.get('facts_count', 0)}, People: {metadata.get('people_count', 0)}")
                if metadata.get('log_id'):
                    print(f"   Recording ID: {metadata['log_id'][:8]}...")

def count_recordings_vs_memories():
    """Count recordings in cache vs memories created."""
    print("\n📋 Checking recordings vs memories ratio...")
    
    # This would need Redis access to be fully accurate
    # For now, we'll analyze based on recent memories
    recent_memories = get_recent_memories(100)
    
    # Group by recording ID
    recordings = {}
    for memory in recent_memories:
        metadata = memory.get('metadata', {})
        if metadata.get('source') == 'limitless' and metadata.get('log_id'):
            log_id = metadata['log_id']
            if log_id not in recordings:
                recordings[log_id] = []
            recordings[log_id].append(memory)
    
    print(f"\nUnique recordings with memories: {len(recordings)}")
    
    # Analyze memory count per recording
    memory_counts = {}
    for log_id, mems in recordings.items():
        count = len(mems)
        memory_counts[count] = memory_counts.get(count, 0) + 1
    
    print("\nMemories per recording distribution:")
    for count, num_recordings in sorted(memory_counts.items()):
        print(f"  {count} memory/recording: {num_recordings} recordings")
    
    # Calculate average
    total_memories = sum(len(mems) for mems in recordings.values())
    avg_memories = total_memories / len(recordings) if recordings else 0
    print(f"\nAverage memories per recording: {avg_memories:.2f}")

if __name__ == "__main__":
    print("🧪 Testing Memory Creation Optimization")
    print("=" * 50)
    
    # Run analysis
    analyze_memory_creation()
    count_recordings_vs_memories()
    
    print("\n✅ Test complete!")