# Changelog

All notable changes to this project will be documented in this file.

## [1.1.8] - 2025-06-08

### Critical Bug Fix: Limitless Speaker Identification System

#### Major Issue Resolution
- **Problem**: Dashboard displaying "Unknown" speakers and generic "Speaker" labels instead of proper "Speaker 0", "Speaker 1", "Speaker 2" naming convention
- **Impact**: Poor user experience with confusing speaker identification across all Limitless recordings
- **Root Cause**: Multiple code paths in the system creating inconsistent speaker names from Limitless API responses

#### Comprehensive Speaker Standardization System
- **Enhanced API Processing**:
  * Upgraded `extract_speakers_from_contents()` to handle Limitless API returning "Unknown" as actual speaker names
  * Implemented dynamic "Speaker N" mapping with sequential numbering (Speaker 0, Speaker 1, Speaker 2, etc.)
  * Added proper speaker ID to Speaker N name mapping for consistent transcript building

- **Cache Data Standardization**:
  * Created `standardize_cached_speakers()` function to fix existing cached recordings
  * Applied standardization to all cache loading endpoints in dashboard
  * Ensured backward compatibility with existing data structures

- **Bulletproof Validation Pipeline**:
  * Added `validate_speaker_names()` as final validation before caching
  * Fixed transcript building logic to assign proper Speaker N numbers for unmapped speakers
  * Eliminated generic "Speaker" labels without numbers

#### Historical Data Fixes
- **Targeted Fix Scripts** (preserved in `scripts/fixes/`):
  * `fix_limitless_speakers.py` - Initial fix for Unknown speakers
  * `fix_false_speakers.py` - Fixed 86 recordings with `is_speaker=False` Unknown speakers
  * `fix_speaker_naming_bug.py` - Fixed 1 recording with generic "Speaker" label
  * Multiple debug and diagnostic scripts for troubleshooting

#### Script Organization & Documentation
- **Professional Script Management**:
  * Moved all temporary fix scripts to organized `scripts/fixes/` directory
  * Created comprehensive `scripts/README.md` with categorized documentation
  * Moved `cleanup_fix_scripts.py` and `LIMITLESS_SPEAKER_FIX_SUMMARY.md` to scripts folder
  * Preserved historical context and usage guidelines for future reference

### Technical Implementation Details

#### Core Speaker Processing Enhancements
```python
# Enhanced speaker extraction with Unknown detection
def extract_speakers_from_contents(log: Dict) -> List[Dict[str, str]]:
    # Converts problematic speaker names to proper Speaker N format
    if valid_names:
        speaker_name = sorted(valid_names)[0]
    else:
        # All names are problematic - assign Speaker N
        speaker_n_name = f"Speaker {unrecognized_speaker_counter}"
        speaker_id_mapping[speaker_id] = speaker_n_name
```

#### Cache Standardization System
```python
def standardize_cached_speakers(extracted_data: Dict) -> Dict:
    # Fix any "Unknown" speakers with comprehensive detection
    if (person_name.lower() in ['unknown', 'unknown speaker'] and 
        person.get('is_speaker')):
        new_speaker_name = f"Speaker {unknown_speaker_counter}"
        person['name'] = new_speaker_name
```

#### Final Validation Pipeline
```python
def validate_speaker_names(extracted_data: Dict, log_id: str) -> Dict:
    # Last line of defense against any remaining Unknown speakers
    if person_name.lower() in ['unknown', 'unknown speaker']:
        person['name'] = f'Speaker {next_speaker_number}'
        logger.error(f"CRITICAL: Found Unknown speaker in final validation")
```

### Files Modified
- `functionality/limitless.py`: Complete speaker identification system overhaul
- `api/dashboard/limitless_routes.py`: Applied standardization to all cache loading endpoints
- `scripts/README.md`: Comprehensive script documentation (NEW)
- `scripts/cleanup_fix_scripts.py`: Updated to organize rather than delete scripts
- Multiple fix scripts preserved in `scripts/fixes/` directory

### Results & Impact
- **Eliminated Unknown Speakers**: Fixed 86+ recordings showing "Unknown" speakers
- **Consistent Naming**: All speakers now use proper "Speaker N" format (Speaker 0, Speaker 1, Speaker 2)
- **Bulletproof System**: Multiple validation layers prevent future Unknown speaker issues
- **Professional Organization**: All scripts properly documented and organized
- **Historical Preservation**: Complete fix history preserved for future reference

### Development Standards Established
- **Speaker Naming Convention**: Always use "Speaker N" format, never "Unknown"
- **Script Organization**: Use `scripts/` folder with proper categorization
- **Documentation Requirements**: Comprehensive README files for complex fixes
- **Validation Pipeline**: Multiple layers of speaker name validation

## [1.1.7] - 2025-06-08

### Major Fixes & Improvements

#### Limitless Task Counting Issue Resolution
- **Critical Bug Fix**:
  * Resolved severe under-counting issue where dashboard showed 4 tasks but Google Tasks showed 11+ 
  * Root cause: Natural language tasks weren't being preserved in cache when recordings were reprocessed
  * Tasks were being lost due to separate deduplication preventing proper cache storage

- **Enhanced Task Validation System**:
  * Added task success validation with `created_successfully` field tracking
  * Implemented unified task storage for both AI-extracted and natural language tasks
  * Fixed task preservation logic to maintain all task types across sync cycles
  * Added backward compatibility for legacy task format

- **Force Reprocess Command**:
  * Added `limitless reprocess` WhatsApp command for maintenance
  * Clears processed flags to force reprocessing of recent recordings
  * Applies updated task counting logic to existing cached data
  * Available as maintenance tool for future debugging

#### Sync Status Bar UI/UX Enhancement
- **Compact & Enhanced Design**:
  * Reduced padding and margins for more space-efficient layout
  * Added "All synced • X tasks" green status indicator when everything is up to date
  * Quick stats summary showing recordings/tasks/memories count (hidden on mobile)
  * Consistent pill design for all status indicators
  * Enhanced visual hierarchy and spacing

- **Smart State Management**:
  * Shows relevant information based on sync status
  * No more awkward empty space - always displays useful information
  * Responsive design for mobile optimization

#### Logging System Optimization
- **Reduced Sync Noise**:
  * Changed "already processed, skipping" messages from INFO to DEBUG level
  * Added summary logging: "X processed, Y skipped from Z total recordings"
  * Moved debug information to appropriate log levels
  * Eliminated log spam during scheduled background syncs (every 5 minutes)

- **Enhanced Logging Configuration**:
  * Created custom logging system with batch processing
  * Centralized configuration for Limitless logging levels
  * Better structured logging with progress tracking

#### Code Quality & Maintenance
- **Git Configuration Standardization**:
  * Standardized commit author: LowKey88 <hisyamnasir@gmail.com>
  * Removed Claude signatures from commit messages per user preference
  * Consistent authoring across all commits

- **Debug Log Cleanup**:
  * Reverted hardcoded debug logs from INFO back to DEBUG level
  * Cleaner production logs while preserving debugging capability
  * Maintained diagnostic information for troubleshooting

### Technical Implementation Details

#### Task Counting Logic Fixes
```python
# CRITICAL FIX: Preserve natural language tasks from previous cache
for task in extracted.get('tasks', []):
    if isinstance(task, dict) and task.get('source') == 'natural_language':
        if not any(t.get('description') == task.get('description') for t in validated_tasks):
            validated_tasks.append(task)
```

#### Emergency Backward Compatibility
```python
# Handle both new format (with created_successfully) and legacy format
if task.get('created_successfully') is True:
    validated_count += 1
elif 'created_successfully' not in task:
    # Legacy format: assume successful if has description
    if task.get('description') and len(str(task.get('description')).strip()) > 0:
        legacy_count += 1
```

### Files Modified
- `functionality/limitless.py`: Enhanced task validation and preservation logic
- `api/dashboard/limitless_routes.py`: Fixed double counting and added backward compatibility
- `dashboard/app/dashboard/limitless/page.tsx`: Improved sync status bar design
- `utils/limitless_logger.py`: Created custom logging system (NEW)
- `utils/limitless_config.py`: Centralized Limitless configuration (NEW)

### Results
- **Task Count Accuracy**: Fixed from 4 to 23 tasks (correctly matching Google Tasks)
- **UI Polish**: Professional, space-efficient sync status bar
- **Log Cleanliness**: Eliminated sync noise while preserving important information
- **Maintenance Tools**: Force reprocess command available for future debugging
- **System Stability**: All core functionality preserved and improved

### Experimental Features (Reverted)
- Attempted media speaker detection for YouTube/TV watching scenarios
- Meeting speaker handling for team meetings with unknown participants
- Unknown speaker filtering system

**Note**: Media and meeting speaker detection features were reverted due to Limitless Pendant's inherent limitation of not being able to distinguish between real conversations and media audio sources.

## [1.1.6] - 2025-06-05

### Major Improvements

#### Limitless Integration Optimization
- **Performance Enhancements**:
  * Implemented Redis caching for pending sync counts (5-minute TTL)
  * Eliminated unnecessary Limitless API calls on dashboard page load
  * Fixed gateway timeout errors (504) from excessive API requests
  * Reduced API rate limiting issues significantly

- **Dashboard UX Improvements**:
  * Removed confusing "Force Sync" button - kept only "Sync Now"
  * Eliminated calendar date picker - interface now focuses on current recordings
  * Stopped auto-refresh polling - manual refresh only on sync completion
  * Fixed dark mode text visibility across all UI elements

- **Sync Logic Fixes**:
  * Corrected pending sync calculation time window (was checking wrong timeframe)
  * Aligned manual sync window (24 hours) with pending count calculation
  * Fixed accuracy of pending recordings count display
  * Added detailed logging with emoji indicators for better debugging

### Technical Changes

#### Backend Optimizations
- **API Endpoint Improvements**:
  * `GET /api/dashboard/limitless/stats` now uses cached pending counts
  * `POST /api/dashboard/limitless/sync` updates cache after completion
  * Enhanced error handling and timeout prevention
  * Better logging for sync operations and pending calculations

#### Frontend Refinements
- **React Component Updates**:
  * Simplified `dashboard/app/dashboard/limitless/page.tsx` interface
  * Removed unnecessary state management for date selection
  * Improved button click handlers and API integration
  * Enhanced TypeScript interfaces for better type safety

#### Redis Caching Strategy
- **New Cache Keys**:
  * `meta-glasses:limitless:pending_sync_cache` - Stores pending count with 5-min TTL
  * Automatic cache invalidation and updates after sync operations
  * Prevents redundant API calls while maintaining data accuracy

### Bug Fixes
- Fixed incorrect pending sync count calculation logic
- Resolved manual sync time window mismatch issue
- Eliminated automatic API calls on dashboard page visits
- Fixed dark mode text contrast problems
- Corrected sync button functionality and response handling

## [1.1.5] - 2025-01-06

### Major Features

#### Response Performance Monitoring System
- **New Performance Dashboard Page**:
  * Dedicated `/dashboard/performance` route with comprehensive monitoring
  * Real-time response latency tracking for all 8 operation types
  * Visual performance indicators and status monitoring
  * Time range selection (1h, 24h, 7d) for flexible analysis
  * Mobile-responsive design with dark/light mode support

- **Operation Categories Monitored**:
  * AI Response (3-8s expected) - Memory retrieval and AI generation
  * Calendar (2-5s expected) - Google Calendar operations  
  * Task (1-3s expected) - Google Tasks CRUD operations
  * Automation (1-4s expected) - Home Assistant commands
  * Search (4-10s expected) - Web search pipeline
  * Image (5-12s expected) - Image analysis processing
  * Notion (2-6s expected) - Note creation operations
  * Other (1-3s expected) - Audio transcription and misc operations

- **Performance Analytics**:
  * Overview cards: Average response time, 95th percentile, error rate
  * Response time trend: Hourly latency line chart
  * Category performance: Table with per-operation metrics and status indicators
  * Request distribution: Pie chart showing usage by operation type
  * Expected latency reference: Visual guide for performance thresholds

- **Intelligent Alerting System**:
  * Warning alerts when response time exceeds expected thresholds
  * Error alerts when response time is 50%+ slower than expected
  * Error rate alerts for operations with >10% failure rate
  * Color-coded status indicators (green/yellow/red) for quick assessment

#### Technical Infrastructure
- **Performance Tracking Core**:
  * Created `utils/performance_tracker.py` for centralized metrics collection
  * Redis storage with `meta-glasses:metrics:performance:*` key patterns
  * 7-day data retention with hourly granularity
  * Success/failure tracking for all operations

- **Message Processing Instrumentation**:
  * Added comprehensive timing around all operation types in `main.py`
  * Image, audio, calendar, task, search, automation, notion, and AI response tracking
  * Error handling with performance impact measurement
  * Real-time metrics collection during message processing

- **Dashboard Integration**:
  * React components with Recharts for data visualization
  * TypeScript interfaces for type safety
  * API endpoint `/api/dashboard/performance` with configurable time ranges
  * Enhanced navigation with Performance menu item

#### UI/UX Improvements
- **Fixed Time Range Selector**: Added proper text contrast (`text-gray-900 dark:text-white`) for light mode visibility
- **Enhanced Pie Chart**: Removed overlapping labels, added legend component, improved tooltip styling
- **Better Accessibility**: Improved contrast and WCAG compliance for all performance dashboard elements
- **Responsive Design**: Touch-friendly interface optimized for mobile and tablet devices

#### API Enhancements
- **New Performance API**:
  * `/api/dashboard/performance` endpoint with time range parameters
  * Comprehensive metrics aggregation and analysis
  * Error handling and fallback data structures
  * Added `getPerformanceMetrics()` method to dashboard API client

#### Files Created/Modified
- **New Files**:
  * `utils/performance_tracker.py`: Core performance tracking utility
  * `dashboard/app/dashboard/performance/page.tsx`: Complete performance dashboard page

- **Enhanced Files**:
  * `main.py`: Added timing instrumentation for all operation types
  * `utils/redis_key_builder.py`: Added performance-specific Redis key patterns
  * `api/dashboard/routes.py`: Added performance metrics API endpoint
  * `dashboard/components/Sidebar.tsx`: Added Performance navigation item
  * `dashboard/lib/api.ts`: Added getPerformanceMetrics API method with proper typing

#### Benefits
- **Proactive Monitoring**: Early detection of performance degradation
- **Operational Visibility**: Clear insights into system bottlenecks and slow operations
- **Data-Driven Optimization**: Historical performance data for tuning and capacity planning
- **User Experience**: Faster issue resolution and improved system reliability
- **Scalability Planning**: Usage patterns and performance trends for infrastructure decisions

## [1.1.4] - 2025-01-06

### Major Infrastructure Update

#### Redis Key Migration & Standardization
- **New Centralized Key Management System**:
  * Created `utils/redis_key_builder.py` for consistent key generation
  * Implemented new naming convention: `meta-glasses:{category}:{subcategory}:{identifier}`
  * Replaced inconsistent patterns like `josancamon:rayban-meta-glasses-api:*`, `memory:*`, `metrics:*`
  
- **Comprehensive Migration Process**:
  * Built `scripts/migrate_redis_keys_enhanced.py` with full data type support
  * Preserves TTL using Redis DUMP/RESTORE operations
  * Handles string, hash, set, list, and zset data types
  * Includes dry-run mode and comprehensive logging
  * Rollback-friendly with verification checks
  
- **Key Pattern Examples**:
  * Old: `memory:user123:abc123` → New: `meta-glasses:user:memory:user123:abc123`
  * Old: `josancamon:rayban-meta-glasses-api:reminder:event123` → New: `meta-glasses:reminder:event:event123`
  * Old: `metrics:messages:2025-01-06-14` → New: `meta-glasses:metrics:messages:2025-01-06:14`

#### Dashboard Redis Monitor Improvements
- **Enhanced Search Functionality**:
  * Updated search placeholder to show new key pattern examples
  * Added quick search pattern buttons for common key types
  * One-click search for `meta-glasses:user:memory:*`, `meta-glasses:reminder:*`, etc.
  * Improved user experience after key migration

- **UI Bug Fixes**:
  * Fixed Cancel button visibility in dark mode delete confirmation dialog
  * Added proper text color classes (`text-gray-900 dark:text-white`)
  * Improved accessibility and contrast compliance

#### Safe Cleanup System
- **Created `scripts/cleanup_old_redis_keys.py`**:
  * Verifies new keys exist before deleting old ones
  * Data integrity checks (type matching)
  * Comprehensive reporting and logging
  * Dry-run mode by default for safety
  * Prevents accidental data loss

#### Benefits
- **Consistent Organization**: All Redis keys follow the same hierarchical pattern
- **Better Maintainability**: Centralized key management prevents future inconsistencies
- **Improved Dashboard**: Real-time monitoring with proper key filtering
- **Enhanced Developer Experience**: Easier to find and manage Redis data

### Updated Module Integration
- **Modified Files**:
  * `utils/memory_manager.py`: Updated to use new key patterns
  * `utils/metrics.py`: Migrated to centralized key builder
  * `api/dashboard/routes.py`: Fixed variable naming conflicts
  * All functionality modules updated to use new patterns

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
    - Full CRUD operations for stored memories (Create, Read, Update, Delete)
    - Standardized memory types: fact, preference, relationship, routine, important_date, personal_info, allergy, note
    - Visual knowledge graph view with force-directed layout
    - Interactive entity relationship mapping
    - Search and filter functionality by content and user
    - Enhanced memory editing with proper validation
    - Mobile-friendly interface with grid/graph view toggle
    - Complete removal of unused tags functionality
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
  * Fixed 405 Method Not Allowed error for creating memories - added missing POST endpoint
  * Completely removed tags functionality (not used in system):
    - Removed tags field from create/edit forms
    - Removed tags display from memory cards
    - Removed tags from search filtering
    - Cleaned up all tag-related code and imports
  * Standardized memory types across frontend and backend
  * Added proper form validation and error handling
  * Fixed memory type badge contrast in dark mode
  * Fixed WhatsApp bot memory retrieval for personal queries:
    - Enhanced pattern detection for work, job, and personal questions
    - Improved name extraction for queries like "where X work" and "do you know X"
    - Ensured personal queries check memories before web search
    - Fixed message type routing to prevent personal info web searches
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
