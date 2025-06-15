# WhatsApp Business Message Templates Setup Guide

## Overview

To fix the 24-hour conversation window issue, your WhatsApp Business API needs **approved message templates**. After 24 hours of no user interaction, WhatsApp only allows template messages to be sent.

## Required Message Templates

Your system needs the following templates to be created and approved in your WhatsApp Business Manager:

### 1. Home Assistant Status Template
- **Template Name**: `ha_status`
- **Category**: Utility
- **Language**: English
- **Template Body**: 
  ```
  New message from HA {{ha_message}}
  ```
- **Usage**: For Home Assistant notifications and general system messages

### 2. Daily Schedule Template
- **Template Name**: `daily_schedule`
- **Category**: Utility  
- **Language**: English
- **Template Body**:
  ```
  Good morning! Here's your schedule for today:
  {{1}}
  ```
- **Usage**: For morning calendar reminders

### 3. Meeting Reminder Template
- **Template Name**: `meeting_reminder`
- **Category**: Utility
- **Language**: English
- **Template Body**:
  ```
  Reminder: "{{1}}" starts in 1 hour at {{2}}
  ```
- **Usage**: For 1-hour before meeting reminders

### 4. Meeting Start Template
- **Template Name**: `meeting_start`
- **Category**: Utility
- **Language**: English
- **Template Body**:
  ```
  "{{1}}" is starting now!
  ```
- **Usage**: For meeting start notifications

## How to Create Templates

### Step 1: Access WhatsApp Business Manager
1. Go to https://business.facebook.com/
2. Select your WhatsApp Business account
3. Navigate to "WhatsApp Manager" → "Message Templates"

### Step 2: Create Each Template
1. Click "Create Template"
2. Fill in the template details as specified above
3. Submit for approval
4. Wait for Meta's approval (usually 24-48 hours)

### Step 3: Template Guidelines
- **Variables**: Use `{{1}}`, `{{2}}`, etc. for dynamic content
- **Category**: Use "Utility" for system notifications
- **Language**: Must match your target audience
- **Approval**: Templates must be approved before use

## Implementation Details

### How It Works
- **Within 24 hours**: System sends regular text messages
- **After 24 hours**: System automatically switches to approved templates
- **User interaction**: Resets the 24-hour window

### Code Integration
The system now includes:
- `send_smart_whatsapp_message()` - Automatically chooses between regular/template messages
- `update_conversation_window()` - Tracks user message timestamps
- `is_within_conversation_window()` - Checks if within 24-hour window

### Monitoring
Check logs for these messages:
```
"Within conversation window - sending regular message"
"Outside conversation window - using template message"
"Template message sent successfully"
```

## Testing Your Setup

### 1. Initial Test (Within 24 hours)
1. Send a message to your bot
2. Trigger a reminder/notification
3. Should see: "Within conversation window - sending regular message"

### 2. Template Test (After 24 hours)
1. Wait 24 hours without messaging the bot
2. Trigger a reminder/notification
3. Should see: "Outside conversation window - using template message"

### 3. Verify Template Functionality
- Check WhatsApp Business Manager for template message statistics
- Monitor bot logs for successful template sends
- Ensure notifications are received on your phone

## Common Issues & Solutions

### Template Not Approved
- **Symptom**: Template messages fail with error
- **Solution**: Check WhatsApp Business Manager for approval status
- **Fix**: Wait for approval or modify template to meet guidelines

### Template Parameters Mismatch
- **Symptom**: Template sends but parameters don't fill correctly
- **Solution**: Ensure parameter count matches template variables
- **Fix**: Verify `{{ha_message}}`, `{{meeting_title}}` variables align with code parameters

### Conversation Window Not Updating
- **Symptom**: System always uses templates even after user messages
- **Solution**: Check webhook is calling `update_conversation_window()`
- **Fix**: Verify webhook handler includes conversation window update

## Fallback Strategy

If templates are not approved yet, you can:
1. Use a single generic template for all notifications
2. Temporarily disable notifications outside 24-hour window
3. Ask users to send a daily message to keep the window open

## Next Steps

1. Create and submit all 4 templates for approval
2. Wait for Meta approval (24-48 hours)
3. Deploy the updated code
4. Test both regular and template message flows
5. Monitor logs to ensure proper switching between message types

## Support

If you encounter issues:
1. Check WhatsApp Business Manager for template status
2. Review bot logs for error messages
3. Verify template names match exactly in code
4. Ensure templates are approved and active

---

**Note**: Template approval can take 24-48 hours. Plan accordingly when deploying this fix.