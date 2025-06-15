#!/usr/bin/env python3
"""
Performance test script for AI status monitoring optimizations
Tests both individual API calls and dashboard stats endpoint
"""

import time
import requests
import json
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ai_status import check_gemini_api_status_sync, get_cached_or_check_gemini_status
from utils.whatsapp_status import check_whatsapp_token_status_sync, get_cached_or_check_whatsapp_status

BASE_URL = "http://localhost:8080"
PASSWORD = "syam2020"

def get_auth_token():
    """Get JWT token for API calls"""
    response = requests.post(
        f"{BASE_URL}/api/dashboard/login",
        json={"password": PASSWORD}
    )
    if response.status_code == 200:
        return response.json()["token"]
    else:
        raise Exception(f"Login failed: {response.text}")

def test_individual_api_calls():
    """Test individual API function performance"""
    print("🧪 Testing Individual API Functions")
    print("=" * 50)
    
    # Test Gemini API (original vs optimized)
    print("1. Gemini API Status Check:")
    
    # First call (live API)
    start_time = time.time()
    result = check_gemini_api_status_sync()
    first_call_time = time.time() - start_time
    print(f"   ✅ Live API call: {first_call_time:.2f}s")
    print(f"   📊 Response time: {result.get('response_time_ms', 'N/A')}ms")
    print(f"   🎯 Status: {result.get('status', 'unknown')}")
    
    # Cached call
    start_time = time.time()
    result = get_cached_or_check_gemini_status()
    cached_call_time = time.time() - start_time
    print(f"   ⚡ Cached call: {cached_call_time:.2f}s")
    
    print()
    
    # Test WhatsApp API
    print("2. WhatsApp Status Check:")
    
    # First call (live API)
    start_time = time.time()
    result = check_whatsapp_token_status_sync()
    first_call_time = time.time() - start_time
    print(f"   ✅ Live API call: {first_call_time:.2f}s")
    print(f"   🎯 Status: {result.get('status', 'unknown')}")
    
    # Cached call
    start_time = time.time()
    result = get_cached_or_check_whatsapp_status()
    cached_call_time = time.time() - start_time
    print(f"   ⚡ Cached call: {cached_call_time:.2f}s")
    
    print()

def test_dashboard_endpoint():
    """Test dashboard stats endpoint performance"""
    print("🚀 Testing Dashboard Stats Endpoint")
    print("=" * 50)
    
    try:
        token = get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test multiple calls to see caching effect
        times = []
        for i in range(3):
            start_time = time.time()
            response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
            call_time = time.time() - start_time
            times.append(call_time)
            
            if response.status_code == 200:
                data = response.json()
                ai_response_time = data.get('ai_status', {}).get('response_time_ms', 'N/A')
                whatsapp_status = data.get('whatsapp_status', 'unknown')
                ai_status = data.get('ai_status', {}).get('status', 'unknown')
                
                print(f"   Call {i+1}: {call_time:.2f}s total")
                print(f"     🤖 AI Status: {ai_status} ({ai_response_time}ms)")
                print(f"     📱 WhatsApp: {whatsapp_status}")
            else:
                print(f"   ❌ Call {i+1} failed: {response.status_code}")
            
            time.sleep(0.5)  # Small delay between calls
        
        print()
        print("📈 Performance Summary:")
        print(f"   Average response time: {sum(times)/len(times):.2f}s")
        print(f"   Best time: {min(times):.2f}s")
        print(f"   Worst time: {max(times):.2f}s")
        
        # Performance improvement calculation
        baseline_time = 8.0  # Previous average time before optimization
        current_avg = sum(times) / len(times)
        improvement = ((baseline_time - current_avg) / baseline_time) * 100
        
        print(f"   🎯 Performance improvement: {improvement:.1f}% faster")
        
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")

def main():
    print("🔧 AI Status Monitoring Performance Test")
    print("🎯 Testing optimizations implemented in June 2025")
    print("=" * 60)
    print()
    
    test_individual_api_calls()
    test_dashboard_endpoint()
    
    print()
    print("✅ Performance test completed!")
    print()
    print("💡 Key Optimizations Applied:")
    print("   - Removed expensive Gemini generation test")
    print("   - Increased cache duration to 30 minutes")
    print("   - Implemented concurrent API calls")
    print("   - Added fast-path caching functions")
    print("   - Reduced timeouts for faster responses")

if __name__ == "__main__":
    main()