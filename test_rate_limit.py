#!/usr/bin/env python3
"""
Test script to trigger Gemini API rate limiting for testing dashboard monitoring.
This will make rapid API calls to intentionally hit rate limits.
"""

import asyncio
import os
import sys
import time
from datetime import datetime
import google.generativeai as genai

async def test_rate_limiting():
    """Make rapid API calls to trigger rate limiting"""
    
    # Initialize Gemini API
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment")
        return
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    print(f"🚀 Starting rate limit test at {datetime.now()}")
    print("📡 Making rapid API calls to trigger rate limiting...")
    
    success_count = 0
    rate_limited_count = 0
    
    # Make rapid sequential requests
    for i in range(50):  # Try 50 rapid requests
        try:
            print(f"📤 Request {i+1}/50...", end=" ")
            
            response = model.generate_content(
                f"Say 'Test message {i+1}' briefly.",
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=10,
                    temperature=0
                )
            )
            
            success_count += 1
            print(f"✅ Success")
            
            # Small delay to avoid overwhelming too quickly
            await asyncio.sleep(0.1)
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "429" in error_msg or "rate limit" in error_msg or "quota" in error_msg:
                rate_limited_count += 1
                print(f"🚫 Rate Limited! ({rate_limited_count})")
                
                if rate_limited_count >= 3:
                    print(f"\n🎯 SUCCESS! Triggered rate limiting after {i+1} requests")
                    print(f"✅ Successful requests: {success_count}")
                    print(f"🚫 Rate limited requests: {rate_limited_count}")
                    break
            else:
                print(f"❌ Other error: {e}")
                
        # Brief pause between requests
        await asyncio.sleep(0.05)
    
    else:
        print(f"\n⚠️  Completed {50} requests without hitting rate limit")
        print(f"✅ Successful requests: {success_count}")
        print(f"🚫 Rate limited requests: {rate_limited_count}")
    
    print(f"\n📊 Check dashboard now - AI Status should show rate limiting!")
    print(f"🔗 Dashboard: http://localhost:3000/dashboard")
    print(f"⏰ Test completed at {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(test_rate_limiting())