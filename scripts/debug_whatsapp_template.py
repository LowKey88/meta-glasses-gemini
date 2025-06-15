#!/usr/bin/env python3
"""
Debug WhatsApp template sending step by step.
This script tests different parameter structures to find what works.
"""

import sys
import os
import requests
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.whatsapp import headers, get_whatsapp_url

def test_template_structure(template_name, test_data, description):
    """Test a specific template structure."""
    print(f"\n🧪 Testing: {description}")
    print(f"Template: {template_name}")
    print(f"Data: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(get_whatsapp_url(), headers=headers, json=test_data)
        response_data = response.json()
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            print(f"Response: {response_data}")
            return True
        else:
            print("❌ FAILED")
            print(f"Error: {response_data}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

def main():
    """Test different WhatsApp template structures."""
    print("🔧 WhatsApp Template Structure Debugger")
    print("=" * 60)
    
    # Test 1: Basic template without parameters
    test1 = {
        'messaging_product': 'whatsapp',
        'to': os.getenv('WHATSAPP_PHONE_NUMBER'),
        'type': 'template',
        'template': {
            'name': 'ha_status',
            'language': {'code': 'en'}
        }
    }
    
    success1 = test_template_structure('ha_status', test1, "Basic template without parameters")
    
    if not success1:
        print("\n❌ Basic template failed - template might not be fully approved")
        return
    
    # Test 2: Template with single parameter (current approach)
    test2 = {
        'messaging_product': 'whatsapp',
        'to': os.getenv('WHATSAPP_PHONE_NUMBER'),
        'type': 'template',
        'template': {
            'name': 'ha_status',
            'language': {'code': 'en'},
            'components': [
                {
                    'type': 'body',
                    'parameters': [
                        {
                            'type': 'text',
                            'text': 'Test message from debug script'
                        }
                    ]
                }
            ]
        }
    }
    
    success2 = test_template_structure('ha_status', test2, "Template with body parameter")
    
    # Test 3: Template with header and body components
    test3 = {
        'messaging_product': 'whatsapp',
        'to': os.getenv('WHATSAPP_PHONE_NUMBER'),
        'type': 'template',
        'template': {
            'name': 'ha_status',
            'language': {'code': 'en'},
            'components': [
                {
                    'type': 'header',
                    'parameters': []
                },
                {
                    'type': 'body',
                    'parameters': [
                        {
                            'type': 'text',
                            'text': 'Test message with header component'
                        }
                    ]
                }
            ]
        }
    }
    
    success3 = test_template_structure('ha_status', test3, "Template with header + body components")
    
    # Test 4: Different parameter structure
    test4 = {
        'messaging_product': 'whatsapp',
        'to': os.getenv('WHATSAPP_PHONE_NUMBER'),
        'type': 'template',
        'template': {
            'name': 'ha_status',
            'language': {'code': 'en'},
            'components': [
                {
                    'type': 'body',
                    'parameters': [
                        'Test message with simple parameter format'
                    ]
                }
            ]
        }
    }
    
    success4 = test_template_structure('ha_status', test4, "Template with simple parameter format")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"Test 1 (No parameters): {'✅' if success1 else '❌'}")
    print(f"Test 2 (Body parameter): {'✅' if success2 else '❌'}")
    print(f"Test 3 (Header + Body): {'✅' if success3 else '❌'}")
    print(f"Test 4 (Simple format): {'✅' if success4 else '❌'}")
    
    if any([success2, success3, success4]):
        print("\n✅ Found working parameter structure!")
    else:
        print("\n❌ No parameter structure worked - need to investigate further")

if __name__ == "__main__":
    main()