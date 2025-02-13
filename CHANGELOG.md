# Changelog

All notable changes to this project will be documented in this file.

## [1.1.2] - 2025-01-29

### Improvements
- Calendar Sync Enhancements:
  * Added periodic sync with Google Calendar (5-minute intervals)
  * Fixed events not syncing when created directly in Google Calendar
  * Added comprehensive error handling and logging
  * Added sync statistics tracking
  * Improved WhatsApp notification reliability
  * Enhanced sync status monitoring

## [1.1.1] - 2025-01-23

### Improvements
- Calendar Event Enhancements:
  * Added smart time validation for event creation
    - Prevents creating events in the past
    - Auto-schedules for next day if time has passed
    - Clear user feedback about date adjustments
  * New direct meeting cancellation commands
    - Added "cancel meeting X" format
    - Removed Redis state dependency
    - Better error handling
  * Improved timezone handling
    - Consistent Asia/Kuala_Lumpur timezone usage
    - Fixed offset-aware datetime comparisons
    - Fixed Redis reminder cleanup timezone issues

## [1.1.0] - 2025-01-22

### New Features

#### Task Management System
- Complete Task CRUD Operations:
  - Create tasks with titles, notes, and due dates
  - Read/list tasks with flexible filtering
  - Update task completion status
  - Delete tasks
- Smart Task Organization:
  - Automatic task sorting by due date
  - Upcoming tasks view (configurable days ahead)
  - Task list management with default list support
- Enhanced Task Display:
  - Numbered task indexing for easy reference
  - Formatted due dates for better readability
  - Optional notes display
  - Status indicators (completed/pending)

#### Calendar and Meeting Improvements
- Enhanced Meeting Management:
  * Smart color coding for different event types
  * Improved event cancellation system with selection interface
  * Better event formatting for speech/display
  * Support for all-day events
- Schedule View Enhancements:
  * Weekly schedule overview
  * Today/Tomorrow combined view
  * Upcoming events filtering
  * Past event cleanup
- Meeting Reminders:
  * Integration with WhatsApp notifications
  * Automatic reminder scheduling
  * Redis-based reminder management

### System Improvements
- Redis Optimizations:
  - TTL for cached items (1h default)
  - Reminder expiration (1h post-event)
  - Automatic cleanup of old data
  - Birthday event filtering
  - Limited calendar sync to 7-day window
- Enhanced Error Handling and Logging
- Performance Optimizations

## [1.0.0] - 2025-01-01

### Initial Release
- Core WhatsApp API integration
- Basic calendar event creation
- Task management system
- Docker deployment setup
- Image analysis pipeline
