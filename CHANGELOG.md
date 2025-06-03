# Changelog

All notable changes to this project will be documented in this file.

## [1.1.3] - 2025-01-XX

### Major Features

#### Admin Dashboard
- **New Web-Based Administration Interface**:
  * Built with Next.js/React and TypeScript
  * JWT-based authentication system
  * Docker containerized deployment
  * Mobile-responsive design with collapsible sidebar
  * Dark mode support with persistent preferences

- **Dashboard Features**:
  * System Overview:
    - Real-time uptime tracking
    - 24-hour message count tracking
    - Total memories and active reminders count
    - AI model information display
    - Daily AI request tracking with charts
    - Message activity line chart (24-hour view)
    - Memory type distribution bar chart
  * WhatsApp API Status Monitoring:
    - Real-time token validation
    - Token status indicators
    - Error reporting and diagnostics
  * Memory Management:
    - CRUD operations for stored memories
    - Search and filter functionality
    - Edit memory importance and type
    - Mobile-friendly table interface
  * Redis Monitor:
    - Browse and search Redis keys
    - View key values, types, and TTL
    - Delete functionality
    - URL-encoded key support

#### Metrics & Analytics System
- AI request tracking by model type (chat/vision)
- Response time monitoring (last 100 samples)
- 24-hour message activity tracking by type
- 7-day data retention for analytics
- Hourly message count aggregation

### Infrastructure Enhancements
- Three-container Docker architecture (API, Redis, Dashboard)
- New `/api/dashboard/*` endpoints for admin functions
- Improved error handling and logging
- Health checks for all services
- CORS configuration for dashboard access

### Bug Fixes
- Fixed Redis Monitor URL encoding issues with special characters
- Corrected dashboard stats 24-hour message count calculation
- Fixed dark mode input field visibility
- Improved mobile responsive layout
- Fixed active reminders always showing 0
- Resolved API endpoint path mismatches
- Fixed conversation history limit (increased to 100)

### Documentation
- Added comprehensive dashboard setup guide
- Created system architecture documentation
- Added API integration guides
- Updated CLAUDE.md with development instructions

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
