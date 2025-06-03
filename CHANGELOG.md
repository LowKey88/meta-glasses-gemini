# Changelog

All notable changes to this project will be documented in this file.

## [1.1.3] - 2025-01-06

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
    - Messages Today metric (replaced rolling 24-hour window)
    - Total memories and active reminders count
    - AI model information display
    - Daily AI request tracking with charts
    - Weekly activity bar chart (7-day view)
    - Today vs Yesterday hourly comparison chart
    - Enhanced message activity visualizations
    - Memory type distribution bar chart
  * WhatsApp API Status Monitoring:
    - Real-time token validation
    - Token status indicators
    - Error reporting and diagnostics
  * Memory Management:
    - CRUD operations for stored memories
    - Visual knowledge graph view with force-directed layout
    - Interactive entity relationship mapping
    - Search and filter functionality
    - Enhanced memory editing with proper validation
    - Mobile-friendly interface with grid/graph view toggle
  * Redis Monitor:
    - Browse and search Redis keys
    - View key values, types, and TTL
    - Delete functionality
    - URL-encoded key support

#### Toast Notification System
- **Comprehensive UI Feedback**:
  * Replaced all browser alerts with modern toast notifications
  * Built using @radix-ui/react-toast for accessibility
  * Success, error, and validation message variants
  * Auto-dismissing notifications with proper styling
  * Dark mode compatible design

#### Visual Knowledge Graph
- **Interactive Memory Visualization**:
  * Force-directed graph layout for memory relationships
  * Entity extraction and connection mapping
  * Color-coded nodes by memory type and entity type
  * Hover tooltips with memory details
  * Zoom, pan, and drag functionality
  * Click-to-edit integration

#### Metrics & Analytics System
- AI request tracking by model type (chat/vision)
- Response time monitoring (last 100 samples)
- Enhanced message activity tracking:
  * Messages Today (midnight reset)
  * Weekly activity summaries
  * Hourly pattern comparisons
- 7-day data retention for analytics
- Improved chart visualizations

### Infrastructure Enhancements
- Three-container Docker architecture (API, Redis, Dashboard)
- New `/api/dashboard/*` endpoints for admin functions
- Enhanced error handling and logging
- Health checks for all services
- CORS configuration for dashboard access
- New UI component library structure

### Bug Fixes
- **Memory Management**:
  * Fixed 422 Unprocessable Entity errors when editing memories
  * Resolved backend schema mismatch (memory_type vs type)
  * Removed non-functional tags editing (backend limitation)
  * Added proper form validation and error handling
- Fixed Redis Monitor URL encoding issues with special characters
- Corrected dashboard stats message count calculation
- Fixed dark mode input field visibility
- Improved mobile responsive layout
- Fixed active reminders always showing 0
- Resolved API endpoint path mismatches
- Enhanced text contrast for accessibility (WCAG compliance)

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
