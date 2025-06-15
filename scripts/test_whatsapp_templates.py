#!/usr/bin/env python3
"""
Test script for WhatsApp message templates and conversation window functionality.
This script helps verify that the 24-hour conversation window fix is working properly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.whatsapp import (
    send_smart_whatsapp_message, 
    send_whatsapp_template,
    is_within_conversation_window,
    update_conversation_window,
    CONVERSATION_WINDOW_HOURS
)
from datetime import datetime, timedelta
import time

def test_conversation_window_logic():
    """Test the conversation window logic."""
    print("🔍 Testing Conversation Window Logic")
    print("-" * 50)
    
    # Test initial state (no previous messages)
    print(f"1. Initial state (no previous messages):")
    print(f"   Within window: {is_within_conversation_window()}")
    print(f"   Expected: False")
    print()
    
    # Update conversation window
    print(f"2. After updating conversation window:")
    update_conversation_window()
    print(f"   Within window: {is_within_conversation_window()}")
    print(f"   Expected: True")
    print()

def test_template_sending():
    """Test sending WhatsApp templates directly."""
    print("📧 Testing WhatsApp Template Sending")
    print("-" * 50)
    
    templates_to_test = [
        {
            "name": "ha_status",
            "params": {"body": ["This is a test notification from your Meta Glasses bot"]},
            "description": "Home Assistant status template"
        },
        {
            "name": "daily_schedule", 
            "params": {"body": ["Test Meeting at 2:00 PM, Another Meeting at 4:00 PM"]},
            "description": "Daily schedule template"
        },
        {
            "name": "meeting_reminder",
            "params": {"body": ["Test Meeting", "2:00 PM"]},
            "description": "Meeting reminder template"
        },
        {
            "name": "meeting_start",
            "params": {"body": ["Test Meeting"]},
            "description": "Meeting start template"
        }
    ]
    
    for template in templates_to_test:
        print(f"Testing {template['description']}...")
        success = send_whatsapp_template(template["name"], template["params"])
        print(f"   Template: {template['name']}")
        print(f"   Success: {success}")
        print(f"   Status: {'✅ PASSED' if success else '❌ FAILED'}")
        print()
        
        # Wait a bit between tests
        time.sleep(2)

def test_smart_messaging():
    """Test the smart messaging functionality."""
    print("🤖 Testing Smart WhatsApp Messaging")
    print("-" * 50)
    
    # Update conversation window first
    update_conversation_window()
    
    # Test within conversation window
    print("1. Testing within conversation window:")
    success = send_smart_whatsapp_message(
        "Test message sent while within 24-hour conversation window",
        "ha_status"
    )
    print(f"   Success: {success}")
    print(f"   Expected: Regular message sent")
    print()
    
    # Simulate being outside conversation window
    print("2. Simulating outside conversation window:")
    # We can't easily simulate this without changing the timestamp,
    # but we can test the template fallback
    success = send_smart_whatsapp_message(
        "Test notification that should use template when outside window",
        "ha_status",
        {"body": ["Test notification that should use template when outside window"]}
    )
    print(f"   Success: {success}")
    print(f"   Note: Check logs to see if regular or template message was used")
    print()

def test_reminder_system():
    """Test the reminder system integration."""
    print("⏰ Testing Reminder System Integration")
    print("-" * 50)
    
    # Test morning reminder format
    test_schedule = "• Team Meeting at 10:00 AM\n• Lunch at 12:00 PM"
    success = send_smart_whatsapp_message(
        f"Good morning! Here's your schedule for today:\n{test_schedule}",
        "daily_schedule",
        {"body": [test_schedule]}
    )
    print(f"Morning reminder test: {'✅ PASSED' if success else '❌ FAILED'}")
    
    # Test meeting reminder format
    success = send_smart_whatsapp_message(
        "Reminder: 'Team Meeting' starts in 1 hour at 10:00 AM",
        "meeting_reminder", 
        {"body": ["Team Meeting", "10:00 AM"]}
    )
    print(f"Meeting reminder test: {'✅ PASSED' if success else '❌ FAILED'}")
    
    # Test meeting start format
    success = send_smart_whatsapp_message(
        "'Team Meeting' is starting now!",
        "meeting_start",
        {"body": ["Team Meeting"]}
    )
    print(f"Meeting start test: {'✅ PASSED' if success else '❌ FAILED'}")
    print()

def main():
    """Run all tests."""
    print("🚀 WhatsApp Template & Conversation Window Test Suite")
    print("=" * 60)
    print()
    
    try:
        # Test 1: Conversation window logic
        test_conversation_window_logic()
        
        # Test 2: Template sending
        test_template_sending()
        
        # Test 3: Smart messaging
        test_smart_messaging()
        
        # Test 4: Reminder system
        test_reminder_system()
        
        print("✅ All tests completed!")
        print()
        print("📋 Next Steps:")
        print("1. Check your WhatsApp to see if messages were received")
        print("2. Review the logs to verify conversation window logic")
        print("3. If template messages failed, check WhatsApp Business Manager")
        print("4. Ensure all templates are approved and active")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Ensure your .env file has correct WhatsApp API credentials")
        print("2. Verify your WhatsApp Business templates are approved")
        print("3. Check your WhatsApp Business API permissions")

if __name__ == "__main__":
    main()