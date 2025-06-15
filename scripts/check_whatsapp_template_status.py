#!/usr/bin/env python3
"""
Check WhatsApp Business template status and test template sending.
This script helps diagnose template approval issues.
"""

import sys
import os
import requests
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# WhatsApp API configuration
WHATSAPP_API_VERSION = "v21.0"
GRAPH_API_BASE = "https://graph.facebook.com"

headers = {
   'Authorization': f'Bearer {os.getenv("WHATSAPP_AUTH_TOKEN")}',
   'Content-Type': 'application/json',
}

def get_templates():
    """Get all message templates for the WhatsApp Business account."""
    url = f"{GRAPH_API_BASE}/{WHATSAPP_API_VERSION}/{os.getenv('WHATSAPP_PHONE_ID')}/message_templates"
    
    try:
        response = requests.get(url, headers=headers)
        response_data = response.json()
        
        if response.status_code == 200:
            return response_data.get('data', [])
        else:
            print(f"❌ Failed to get templates: {response_data}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting templates: {e}")
        return []

def check_template_status():
    """Check the status of all templates."""
    print("🔍 Checking WhatsApp Business Template Status")
    print("=" * 60)
    
    templates = get_templates()
    
    if not templates:
        print("❌ No templates found or error accessing templates")
        return
        
    our_templates = ['ha_notification', 'daily_schedule', 'meeting_reminder', 'meeting_start']
    
    for template in templates:
        name = template.get('name', 'Unknown')
        status = template.get('status', 'Unknown')
        category = template.get('category', 'Unknown')
        language = template.get('language', 'Unknown')
        
        if name in our_templates:
            status_emoji = "✅" if status == "APPROVED" else "⚠️" if status == "PENDING" else "❌"
            print(f"{status_emoji} {name}")
            print(f"   Status: {status}")
            print(f"   Category: {category}")
            print(f"   Language: {language}")
            
            # Show template components
            if 'components' in template:
                for component in template['components']:
                    comp_type = component.get('type', 'unknown')
                    if comp_type == 'BODY':
                        body_text = component.get('text', '')
                        print(f"   Body: {body_text}")
                    elif comp_type == 'HEADER':
                        header_text = component.get('text', '')
                        print(f"   Header: {header_text}")
            print()
    
    # Summary
    approved_count = sum(1 for t in templates if t.get('name') in our_templates and t.get('status') == 'APPROVED')
    total_our_templates = len(our_templates)
    
    print(f"📊 Summary: {approved_count}/{total_our_templates} templates approved")
    
    if approved_count == 0:
        print("\n⚠️  ISSUE FOUND:")
        print("   None of your templates are approved yet!")
        print("   WhatsApp only allows sending APPROVED templates.")
        print("\n💡 Next Steps:")
        print("   1. Wait for WhatsApp to approve your templates (24-48 hours)")
        print("   2. Check WhatsApp Business Manager for approval status")
        print("   3. Templates must show 'APPROVED' status to work")
        
    elif approved_count < total_our_templates:
        print(f"\n⚠️  PARTIAL APPROVAL:")
        print(f"   {total_our_templates - approved_count} templates still pending")
        print("   Wait for all templates to be approved")
        
    else:
        print("\n✅ ALL TEMPLATES APPROVED!")
        print("   Your WhatsApp templates should work correctly")

def test_simple_template():
    """Test sending a very simple template structure."""
    print("\n🧪 Testing Simple Template Structure")
    print("-" * 40)
    
    # Test the simplest possible template call
    test_data = {
        'messaging_product': 'whatsapp',
        'to': os.getenv('WHATSAPP_PHONE_NUMBER'),
        'type': 'template',
        'template': {
            'name': 'ha_notification',
            'language': {'code': 'en'}
        }
    }
    
    print(f"Testing template without parameters first...")
    url = f"{GRAPH_API_BASE}/{WHATSAPP_API_VERSION}/{os.getenv('WHATSAPP_PHONE_ID')}/messages"
    
    try:
        response = requests.post(url, headers=headers, json=test_data)
        response_data = response.json()
        
        if response.status_code == 200:
            print("✅ Basic template structure works!")
        else:
            print(f"❌ Basic template failed: {response_data}")
            error_message = response_data.get('error', {}).get('message', '')
            if 'template' in error_message.lower() and 'not found' in error_message.lower():
                print("💡 Template not found - likely not approved yet")
                
    except Exception as e:
        print(f"❌ Error testing template: {e}")

if __name__ == "__main__":
    print("🚀 WhatsApp Template Status Checker")
    print("=" * 60)
    print()
    
    # Check if environment variables are set
    if not os.getenv('WHATSAPP_AUTH_TOKEN'):
        print("❌ WHATSAPP_AUTH_TOKEN not set")
        exit(1)
        
    if not os.getenv('WHATSAPP_PHONE_ID'):
        print("❌ WHATSAPP_PHONE_ID not set") 
        exit(1)
        
    if not os.getenv('WHATSAPP_PHONE_NUMBER'):
        print("❌ WHATSAPP_PHONE_NUMBER not set")
        exit(1)
    
    # Run checks
    check_template_status()
    test_simple_template()
    
    print("\n" + "=" * 60)
    print("🔧 If templates are approved but still failing:")
    print("   1. Check template variable names match exactly")
    print("   2. Verify parameter structure in code")
    print("   3. Test with WhatsApp Business API directly")