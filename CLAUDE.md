# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Meta Rayban Glasses + WhatsApp Bot Integration that uses Google's Gemini AI to create an intelligent personal assistant. Users interact through voice commands via Meta Rayban smart glasses, processed through WhatsApp and powered by various Google services.

## Development Commands

### Backend (Python/FastAPI)

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server with auto-reload
uvicorn main:app --reload

# Run tests (install pytest first: pip install pytest)
pytest
pytest -v  # verbose output
pytest tests/test_redis_key_builder.py  # specific test file

# Run with Docker
docker-compose up -d
docker-compose logs -f app  # view backend logs
```

### Dashboard (Next.js)

```bash
cd dashboard

# Install dependencies
npm install

# Development server (http://localhost:3000)
npm run dev

# Production build
npm run build
npm start

# Lint code
npm run lint
```

### Docker Development

#### Production Images (from GitHub Container Registry)
```bash
# Uses pre-built images from GitHub Actions
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

#### Local Development (with hot-reload)
```bash
# Uses docker-compose.local.yml for local builds and development
# Backend: http://localhost:8111 (with API docs at /docs)
# Dashboard: http://localhost:3000
# Redis: port 6378

# Start all services with local builds
docker-compose -f docker-compose.local.yml up -d

# View logs
docker-compose -f docker-compose.local.yml logs -f

# Restart specific service
docker-compose -f docker-compose.local.yml restart app

# Rebuild after major changes
docker-compose -f docker-compose.local.yml up -d --build

# Stop all services
docker-compose -f docker-compose.local.yml down
```

**Local Development Setup Requirements:**
1. Copy `.env.example` to `.env` and fill in your API keys
2. Ensure Docker Desktop is running
3. Note: Redis runs on port 6378 (not the default 6379) to match production config

## Architecture Overview

### Service Architecture

1. **Backend API (FastAPI)** - `main.py`
   - Handles WhatsApp webhooks and message processing
   - Manages integrations with Google services, Notion, and Home Assistant
   - Provides REST API for dashboard
   - Uses Redis for session management and caching

2. **Dashboard (Next.js)** - `/dashboard`
   - Admin interface with JWT authentication
   - Real-time monitoring and system metrics
   - Memory management and conversation history
   - Uses Zustand for state, TanStack Query for data fetching

3. **Redis Cache**
   - Session storage with TTL-based cleanup
   - Conversation context and memory management
   - Performance metrics and system state

### Key Integration Points

- **WhatsApp Business API**: Primary user interface via `/webhook` endpoint
- **Google Gemini AI**: Natural language processing and understanding
- **Google Calendar/Tasks**: Event and task management via OAuth2
- **Notion API**: Note-taking and knowledge management
- **Home Assistant**: Smart home automation
- **Limitless API**: Additional memory and context features

### Data Flow

1. User speaks to Meta Rayban Glasses
2. Audio sent to WhatsApp as voice message
3. Backend receives via webhook, processes with Gemini AI
4. AI determines intent and executes appropriate function
5. Response sent back through WhatsApp
6. Dashboard monitors and displays metrics

## Important API Endpoints

### Core Endpoints
- `POST /webhook` - WhatsApp message handler
- `GET /webhook` - WhatsApp verification
- `POST /send-notification` - Send WhatsApp notifications

### Dashboard API (`/api/dashboard/`)
- `POST /api/dashboard/login` - JWT authentication
- `GET /api/dashboard/stats` - System statistics
- `GET /api/dashboard/memories` - Memory management
- `GET /api/dashboard/redis/*` - Redis operations
- `GET /api/dashboard/limitless/*` - Limitless integration

### Google OAuth
- `GET /auth/google` - Initiate OAuth flow
- `GET /auth/google/callback` - OAuth callback

## Code Organization

### Backend Structure
- `functionality/` - Service modules (audio, calendar, tasks, etc.)
- `utils/` - Shared utilities (Redis, API clients, auth)
- `api/dashboard/` - Dashboard-specific API routes

### Dashboard Structure
- `app/` - Next.js app router pages
- `components/` - React components and UI elements
- `hooks/` - Custom React hooks
- `lib/` - API client and utilities
- `store/` - Zustand state management

## Testing Guidelines

Currently, tests use pytest framework. Add new tests in `/tests/` directory following the existing pattern. Note: pytest must be installed separately as it's not in requirements.txt.

## Environment Variables

Required environment variables (see `.env.example` if available):
- WhatsApp API credentials
- Redis connection details
- Google API keys and OAuth credentials
- Notion integration tokens
- Home Assistant configuration
- Dashboard JWT secret and admin credentials

## Environment Variable Handling

- **CRITICAL**: Do not access, read, remember, or reference any `.env` files in this project. Never commit or push `.env` files to GitHub as they contain sensitive API keys and credentials. If you need to understand configuration, refer to `.env.example` instead.
- Always use `.gitignore` to exclude sensitive environment files
- Use `.env.example` as a template for required environment variables

## Redis Key Patterns

The project uses structured Redis keys with the pattern:
`{service}:{identifier}:{data_type}:{timestamp}`

Example: `whatsapp:1234567890:context:1704067200`

Use the `RedisKeyBuilder` utility in `utils/redis_key_builder.py` for consistent key generation.

## Performance Monitoring

The system includes built-in performance tracking:
- Request timing and metrics in `utils/performance_tracker.py`
- Redis monitoring in `utils/redis_monitor.py`
- Dashboard displays real-time metrics

## Common Development Tasks

### Adding a New Integration
1. Create module in `functionality/`
2. Add utility functions in `utils/` if needed
3. Import and use in `main.py`
4. Add dashboard endpoints if UI needed
5. Update environment variables

### Modifying Dashboard
1. Next.js pages in `app/` directory
2. Shared components in `components/`
3. API calls through `lib/api.ts`
4. State management with Zustand in `store/`

#### Working with Redis
Always use `RedisKeyBuilder` for key generation and `utils/redis_utils.py` for operations to maintain consistency.

## Recent Development Work

### Limitless Performance Time-Based Charts Implementation (June 2025)

#### Comprehensive Time-Based Visualization System
**Purpose**: Implemented advanced performance monitoring with time-based charts for Limitless processing, matching Message Processing tab functionality.

**Background**: Enhanced the existing Limitless performance monitoring with professional time-based visualization capabilities including 24-hour and 7-day trend analysis.

#### Key Features Implemented

**1. Advanced Performance API Enhancement**
- **File**: `api/dashboard/limitless_routes.py`
- **Enhancement**: Extended `/performance-metrics` endpoint with time range support (`24h`, `7d`)
- **Data Processing**: Implemented hourly data bucketing for trend visualization
- **Category Analysis**: Added operation-level performance breakdown with timing statistics
- **Time Filtering**: Smart time window filtering for performance records within specified ranges

**2. Professional Chart Components**
- **📈 Processing Time Trend Chart**: Line chart showing processing times over selected time range
- **⚙️ Performance by Operation Table**: Breakdown by operation type with bottleneck detection  
- **📊 Processing Volume Distribution**: Pie chart for workload analysis across operations
- **Empty States**: Proper "No data available" messages for all chart sections

**3. Frontend Implementation & User Experience**
- **File**: `dashboard/app/dashboard/performance/page.tsx`
- **Time Range Selector**: Independent dropdown controls for Limitless vs Message Processing tabs
- **Chart Integration**: Professional Recharts implementation with consistent styling
- **Visual Consistency**: Matching design patterns with Message Processing tab charts
- **Responsive Design**: Mobile-optimized chart layouts with proper scaling

**4. Backend Performance Tracking Enhancements**
- **Operation Categories**: Structured tracking for 6 operation types:
  - Speaker Identification
  - Natural Language Tasks  
  - Gemini AI Extraction
  - Memory Creation
  - Task Creation
  - Redis Caching
- **Display Name Mapping**: User-friendly operation names in frontend
- **Time Bucketing**: Hourly (24h) and daily (7d) data aggregation
- **Statistical Analysis**: Average processing times, counts, and performance status calculation

#### Technical Architecture

**API Enhancements (`api/dashboard/limitless_routes.py`):**
```python
# Enhanced endpoint with time range support
@router.get("/performance-metrics")
async def get_performance_metrics(
    limit: int = Query(10),
    range: str = Query("24h", description="Time range (24h, 7d)"),
    user: str = Depends(verify_dashboard_token)
) -> Dict[str, Any]:
    # Time-based data processing with hourly buckets
    # Category breakdown analysis
    # Bottleneck detection logic
```

**Frontend State Management:**
```typescript
// Separate time range states for tab independence
const [timeRange, setTimeRange] = useState('24h');           // General tab
const [limitlessTimeRange, setLimitlessTimeRange] = useState('24h'); // Limitless tab

// Enhanced API client with time range parameter
async getLimitlessPerformanceMetrics(limit: number = 10, range: string = '24h')
```

#### Chart Implementation Details

**Processing Time Trend Chart:**
- Line chart visualization using Recharts
- Time-based X-axis with proper labeling (hourly for 24h, daily for 7d)
- Processing time Y-axis in seconds
- Interactive tooltips with formatting
- Blue color scheme matching dashboard standards

**Performance by Operation Table:**
- Operation breakdown with average time, count, and status
- Color-coded performance indicators:
  - Green: <10s (Good performance)
  - Yellow: 10-30s (Warning)
  - Red: >30s (Bottleneck)
- Badge indicators for bottleneck detection

**Processing Volume Distribution Chart:**
- Pie chart showing workload distribution across operations
- Color-coded segments with interactive tooltips
- Legend with operation details
- Responsive sizing for mobile devices

#### Development Impact
- **Bundle Size**: Added 0.3KB to performance page for advanced chart functionality
- **API Efficiency**: Optimized time-based filtering reduces unnecessary data processing
- **User Experience**: Professional visualization matching industry-standard analytics dashboards
- **Monitoring Capabilities**: Complete visibility into Limitless processing performance bottlenecks

#### Files Modified
- `api/dashboard/limitless_routes.py` - Enhanced performance API with time-based analytics
- `dashboard/app/dashboard/performance/page.tsx` - Complete chart implementation
- `dashboard/lib/api.ts` - Updated TypeScript interfaces and API client methods
- `functionality/limitless.py` - Enhanced performance tracking infrastructure
- `utils/gemini.py` - Performance monitoring improvements

#### Usage & Access
```bash
# Access enhanced performance monitoring
open http://localhost:3000/dashboard/performance

# Features available:
# 1. Switch to "Limitless Processing" tab
# 2. Select time range: "Last 24 Hours" or "Last 7 Days"
# 3. View Processing Time Trend chart
# 4. Analyze Performance by Operation table
# 5. Review Processing Volume Distribution chart
```

### Local Docker Development Setup (January 2025)

#### Created Local Development Environment
- **New File**: `docker-compose.local.yml` for local development with hot-reload
- **Purpose**: Enable local development without affecting production deployment
- **Key Features**:
  - Builds from local Dockerfiles instead of pulling pre-built images
  - Volume mounts for hot-reload (both backend and frontend)
  - Backend runs with `uvicorn --reload`
  - Dashboard runs with `npm run dev`
  - Redis configured on port 6378 to match production

#### Configuration Notes
- **No production code changes** - all modifications isolated to local development
- **Environment Setup**: Copy `.env.example` to `.env` and add API keys
- **Port Configuration**:
  - Backend API: http://localhost:8111
  - Dashboard: http://localhost:3000
  - Redis: port 6378 (matching production config)
- **CORS**: Production code uses `http://localhost:3000` in allowed origins

#### Quick Start for Local Development
```bash
# Start local development environment
docker-compose -f docker-compose.local.yml up -d

# Check logs
docker-compose -f docker-compose.local.yml logs -f

# Access services
# Backend API: http://localhost:8111/docs
# Dashboard: http://localhost:3000 (password: meta-admin-2024)
```

### Dashboard Settings Management Feature (January 2025)

#### Comprehensive Settings Management System Implementation
- **Feature Branch**: `feature/dashboard-settings` 
- **Purpose**: Replace manual `.env` file editing with user-friendly dashboard interface
- **Status**: Core implementation complete, testing/debugging in progress

#### Backend Implementation (✅ Complete)
- **New API Routes**: `/api/dashboard/settings/*` with full CRUD operations
- **Settings Schema**: 16+ configurable settings across 7 categories
- **Security Features**: 
  - JWT authentication required
  - API key masking for sensitive values
  - Audit logging for all changes
  - Environment variable fallback support
- **Connection Testing**: Built-in testing for Gemini, WhatsApp, Notion, Home Assistant APIs
- **Redis Storage**: Encrypted storage for sensitive settings with TTL management

#### Frontend Implementation (✅ Complete)
- **New Settings Page**: `/dashboard/settings` with intuitive category organization
- **UI Features**:
  - Collapsible categories (System, AI Services, Communication, etc.)
  - Masked display of sensitive values (`sk-***abc123`)
  - Real-time connection testing buttons
  - Toast notifications for user feedback
  - Source tracking (Redis vs Environment)
  - Setting reversion to environment variables

#### Settings Categories Implemented
1. **System Configuration** - Dashboard password, user ID, log levels
2. **AI Services** - Gemini API, Limitless API keys
3. **Communication** - WhatsApp Business API credentials  
4. **Productivity Tools** - Notion integration tokens
5. **Home Automation** - Home Assistant configuration
6. **External Services** - Search and scraping APIs
7. **Cloud Storage** - Google Cloud Storage settings

#### Technical Architecture
- **Authentication**: Extracted `verify_token` to separate `auth.py` module to avoid circular imports
- **API Client**: Extended with settings-specific methods (`getSettings`, `updateSetting`, etc.)
- **Navigation**: Added Settings link to sidebar with gear icon
- **Error Handling**: Comprehensive error handling with user-friendly messages

#### Testing Status
- **Backend API**: ✅ All endpoints tested and working (GET, PUT, DELETE, POST test)
- **Frontend Compilation**: ✅ Successfully compiling without errors
- **User Testing**: 🔄 In progress - identified potential browser-side bug requiring investigation
- **MCP Testing Setup**: 🔄 Planning to install Puppeteer MCP for comprehensive frontend testing

#### Next Steps (When Resuming)
1. **Install Puppeteer MCP**: Run `claude mcp add puppeteer -s user -- npx -y @modelcontextprotocol/server-puppeteer`
2. **Debug Frontend Issue**: Use Puppeteer to capture console errors and test UI interactions
3. **Complete Testing Phase**: Comprehensive end-to-end testing of all settings functionality
4. **Security Enhancement**: Implement encryption for sensitive data in Redis
5. **Merge to Dev**: Once testing complete, merge feature branch to dev branch

#### Commands for Resuming Work
```bash
# Continue on feature branch
git checkout feature/dashboard-settings

# Start local development environment  
docker-compose -f docker-compose.local.yml up -d

# Access settings page for testing
open http://localhost:3000/dashboard/settings

# Check if Puppeteer MCP installed
# Should see browser automation tools available in Claude Code
```

### Memory Display Issues Resolution (June 2025)

#### Issue Investigation and Root Cause Analysis
- **Problem**: Dashboard showing "No memories found" despite 497+ memories in backend
- **Symptoms**: Manual memories not appearing, corrupted content with "From X:" prefixes, API connection failures
- **Root Causes Identified**:
  1. **API Port Mismatch**: Dashboard connecting to port 8111, API running on port 8080
  2. **Content Corruption**: AI extraction artifacts with "From [context]:" prefixes in memory content
  3. **Memory Limit**: API hardcoded to return only first 50 memories, hiding manual memories
  4. **Source Field Issues**: Manual memories stored with content in wrong field (`extracted_from` vs `content`)

#### Comprehensive Fix Implementation
1. **Memory Content Cleanup** - `scripts/debug_memory_issues.py fix`
   - Cleaned 325+ corrupted memories with AI extraction artifacts
   - Removed "From X:" prefixes from memory content
   - Preserved actual meaningful content

2. **Source Field Correction** - `scripts/fix_manual_memories.py`
   - Fixed 13 manual memories with content stored in wrong field
   - Moved content from `extracted_from` to `content` field
   - Set proper `extracted_from='manual'` source tracking

3. **API Connection Fix** - `dashboard/lib/api.ts`
   - Updated API URL from port 8111 to correct port 8080
   - Restored frontend-backend communication

4. **Memory Limit Resolution** - `api/dashboard/routes.py`
   - Increased API memory limit from 50 to 1000
   - Ensures all memories appear in "All Types" view

#### Debugging Tools Created
- **`scripts/debug_memory_issues.py`** - Main diagnostic and content cleanup tool
- **`scripts/diagnose_missing_memories.py`** - Detailed memory source analysis
- **`scripts/fix_manual_memories.py`** - Fix content field misplacement
- **`scripts/verify_memory_fix.py`** - Verify fix completion
- **`scripts/test_api_ports.py`** - Find correct API port
- **`scripts/test_specific_api.py`** - Test exact dashboard API calls
- **`scripts/debug_manual_memory_ordering.py`** - Analyze memory sorting issues

#### Results Achieved
- ✅ **All 497+ memories now visible** in dashboard
- ✅ **Manual memories properly displayed** with "Manual" source badges
- ✅ **Clean, readable content** without corruption artifacts
- ✅ **Proper source tracking** for Manual, WhatsApp, and Limitless memories
- ✅ **Full API functionality restored** with correct port configuration

#### Technical Lessons Learned
1. **Port Configuration**: Production deployments may use different ports than development
2. **Memory Limits**: Default API limits can hide data that exists in backend
3. **Field Validation**: Content can be stored in wrong fields during data migration
4. **Debugging Tools**: Comprehensive diagnostic scripts essential for complex issues

#### Files Modified for Resolution
- `dashboard/lib/api.ts` - API port configuration fix
- `api/dashboard/routes.py` - Memory limit increase
- `utils/memory_manager.py` - Enhanced memory sorting and cleanup
- Multiple diagnostic scripts in `scripts/` directory

#### Commands for Future Memory Issues
```bash
# Diagnose memory display problems
python3 scripts/debug_memory_issues.py

# Fix corrupted content
python3 scripts/debug_memory_issues.py fix

# Check specific API endpoints
python3 scripts/test_specific_api.py

# Find correct API port
python3 scripts/test_api_ports.py
```

### Memory System Enhancement Plan (June 2025)

#### Background: Mem0.ai Comparison Analysis
After analyzing [Mem0.ai's research](https://mem0.ai/research), identified key architectural differences and improvement opportunities for our memory system.

#### Mem0.ai Key Features vs Current System

**Mem0.ai Advantages:**
- **Dynamic Memory Extraction**: Automatically extracts and consolidates memories
- **Graph-based Storage**: Enhanced variant (Mem0ᵍ) with relationship modeling
- **Performance**: 26% better accuracy, 91% lower latency, 90% token savings
- **Memory Consolidation**: Intelligent merging of related memories

**Current System Strengths:**
- 8 predefined memory types with pattern-based extraction
- AI-powered deduplication using Gemini
- Source tracking (Manual, WhatsApp, Limitless)
- Redis-based storage with dashboard integration

**Identified Gaps:**
1. No memory consolidation (only duplicate detection)
2. Flat storage structure vs graph relationships
3. Limited cross-session context awareness
4. Fixed memory types vs dynamic extraction
5. No performance optimization features

#### Implementation Plan: Enhanced Memory System

##### Phase 1: Memory Consolidation System (2-3 weeks)
**Objective**: Implement intelligent memory merging and updating

**Key Tasks:**
1. **Enhanced Deduplication Logic**
   - Implement memory merging instead of just conflict detection
   - Update existing memories with new information
   - Add confidence scoring for memory updates

2. **Memory Consolidation Engine**
   - AI-powered memory merging strategies
   - Memory versioning system
   - Relationship tracking between memories

3. **Memory Chain Reconstruction**
   - Link related memories
   - Track dependencies and updates
   - Build memory evolution history

##### Phase 2: Graph-based Memory Store (1-2 weeks)
**Objective**: Implement relationship-aware memory storage

**Key Tasks:**
1. **Graph Schema Design**
   - Person-to-person relationships
   - Topic-to-topic connections
   - Temporal relationships

2. **Graph Storage Implementation**
   - Graph database integration (Neo4j or Redis Graph)
   - Relationship APIs
   - Graph traversal algorithms

3. **Context-aware Retrieval**
   - Multi-hop memory exploration
   - Relevance scoring based on graph distance
   - Relationship-based memory suggestions

##### Phase 3: Performance Optimization (1-2 weeks)
**Objective**: Achieve Mem0-like performance improvements

**Key Tasks:**
1. **Memory Ranking System**
   - Importance weighting algorithms
   - Recency-based scoring
   - Context relevance metrics

2. **Token Usage Optimization**
   - Smart memory summarization
   - Efficient memory selection
   - Dynamic context window management

3. **Performance Tuning**
   - Memory retrieval caching
   - Query optimization
   - Batch operations

##### Phase 4: Advanced Features (Future)
**Objective**: Add sophisticated memory capabilities

**Key Tasks:**
1. **Dynamic Memory Types**
   - AI-determined categories
   - Adaptive classification
   - Type evolution tracking

2. **Cross-session Awareness**
   - Long-term conversation memory
   - Behavior pattern recognition
   - Session relationship tracking

3. **Enhanced Dashboard**
   - Graph visualization
   - Consolidation management UI
   - Performance metrics

#### Technical Implementation Notes

**Memory Consolidation Algorithm (Phase 1):**
```python
# Pseudocode for memory consolidation
def consolidate_memory(new_memory, existing_memories):
    related_memories = find_related_memories(new_memory, existing_memories)
    if related_memories:
        confidence_scores = calculate_confidence(new_memory, related_memories)
        if should_merge(confidence_scores):
            merged_memory = merge_memories(new_memory, related_memories)
            update_memory_graph(merged_memory, related_memories)
            return merged_memory
    return create_new_memory(new_memory)
```

**Graph Schema Example (Phase 2):**
```
(User)-[:HAS_MEMORY]->(Memory)
(Memory)-[:RELATES_TO]->(Memory)
(Memory)-[:ABOUT_PERSON]->(Person)
(Memory)-[:OCCURRED_BEFORE]->(Memory)
(Memory)-[:UPDATED_FROM]->(Memory)
```

**Performance Metrics to Track:**
- Memory retrieval latency
- Token usage per conversation
- Memory relevance accuracy
- Deduplication effectiveness
- Graph traversal efficiency

#### Expected Outcomes
- **50% reduction** in duplicate memories
- **30% improvement** in context relevance
- **40% reduction** in token usage
- **Enhanced user experience** with smarter memory management
- **Scalable architecture** for growing memory datasets

#### Next Steps
1. Begin Phase 1 implementation with memory consolidation
2. Set up performance benchmarking
3. Create test cases for memory merging scenarios
4. Design graph schema for Phase 2

### Limitless Integration Optimization (June 2025)

#### Smart Memory Creation & Dashboard Performance Issues Resolution

**Background**: Fixed critical issues with dashboard freezing during Limitless sync operations and implemented quality-based memory filtering to reduce noise while maintaining full recording visibility.

#### Issues Addressed:
1. **Dashboard Freezing During Sync**: Dashboard became unresponsive during OpenAI embedding generation for Limitless recordings
2. **Memory Quality Concerns**: System creating too many low-quality memories from every recording
3. **Speaker Detection Issues**: Dashboard showing only "You" instead of multiple speakers in conversations
4. **Timezone Mismatch**: Docker container using UTC instead of Malaysia time (+8)

#### Solutions Implemented:

##### 1. Background Processing Architecture
- **File**: `functionality/limitless.py:284-340`
- **Implementation**: Added `process_recordings_background()` function for non-blocking processing
- **Benefits**: Dashboard returns immediate response while processing continues in background
- **Fast Mode**: Created `process_single_lifelog_fast()` for immediate recording caching with deferred AI processing

##### 2. Smart Memory Quality Filtering
- **File**: `utils/memory_quality_filter.py`
- **Implementation**: Created `SmartMemoryCreator` class inspired by Omi's quality assessment
- **Logic**: Scores recordings based on content length, quality indicators, and AI assessment
- **Threshold**: Only creates memories for recordings scoring ≥5/10
- **Result**: Show all recordings in dashboard but only create memories for quality content

##### 3. Speaker Detection Enhancement
- **Issue**: Fast processing mode missing speaker extraction, showing only "You" in dashboard
- **Fix**: Added speaker extraction to `process_single_lifelog_fast()` at line 404-406:
```python
# Extract speakers for dashboard display (fast mode)
log['_phone_number'] = phone_number
speakers_identified = extract_speakers_from_contents(log)
```
- **Result**: Recordings now properly show "Speaker 0", "Speaker 1", etc. instead of just "You"

##### 4. Timezone Configuration
- **Files**: `docker-compose.local.yml`, `Dockerfile`
- **Implementation**: Added `TZ=Asia/Kuala_Lumpur` environment variable and `tzdata` package
- **Result**: Docker container now matches local Malaysia time

#### Technical Architecture:

**Fast Sync Mode Flow:**
1. `sync_recent_lifelogs()` immediately returns response to user
2. `process_recordings_background()` handles AI processing asynchronously
3. `process_single_lifelog_fast()` caches recordings for immediate dashboard display
4. Quality filtering prevents memory creation for low-value recordings

**Speaker Detection Pipeline:**
- `extract_speakers_from_contents()` processes Limitless API speaker data
- Converts problematic "Unknown" speakers to "Speaker N" format
- Uses AI-powered context generation for single-speaker recordings
- Maintains consistent speaker mapping throughout transcript

#### Performance Improvements:
- **Dashboard Responsiveness**: Sync operations complete in ~2 seconds instead of 30+ seconds
- **Memory Quality**: Reduced noise while maintaining full recording visibility
- **Speaker Accuracy**: Proper multi-speaker detection and display
- **Time Synchronization**: Accurate timezone handling for Malaysian users

#### Key Files Modified:
- `functionality/limitless.py` - Background processing and fast mode
- `utils/memory_quality_filter.py` - Smart memory creation (new file)
- `docker-compose.local.yml` - Timezone configuration
- `Dockerfile` - tzdata package installation

#### Quality Metrics Achieved:
- **0 memories created** from low-quality recordings (noise reduction)
- **All recordings visible** in dashboard (full transparency)
- **Proper speaker detection** showing conversation participants
- **Fast sync response** (<2 seconds vs 30+ seconds previously)

#### Commands for Monitoring:
```bash
# Check background processing logs
docker-compose -f docker-compose.local.yml logs -f app | grep "Background processing"

# Monitor memory quality filtering
docker-compose -f docker-compose.local.yml logs -f app | grep "SmartMemoryCreator"

# Verify timezone setting
docker exec raybanmeta date
```

### Memory System API Update (June 2025)

#### Increased Memory Retrieval Limit

**Change**: Updated memory retrieval API to return up to 1000 memories instead of 50
- **File**: `api/dashboard/memory_routes.py` 
- **Line**: Changed `limit=50` to `limit=1000` in `get_recent_memories()` call
- **Reason**: Previous limit of 50 was hiding manual memories and recent entries
- **Impact**: Dashboard now shows all memories correctly, including manual entries

This was part of the initial fix for "No memories found" issue, ensuring all memory types are visible in the dashboard's "All Types" view.

### Dashboard Design System Standardization (June 2025)

#### Actions Page Refactoring for Design Consistency

**Background**: Completed comprehensive refactoring of the Actions & Tasks page to align with established design patterns from Limitless and Performance dashboard pages.

**Design System Patterns Implemented:**
- **Container Structure**: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8` for consistent page layouts
- **Card Styling**: `bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700` with `hover:shadow-md transition-shadow`
- **Interactive Elements**: `transition-all duration-200` for smooth animations and hover states
- **Color Theme**: Blue accent (`text-blue-600 dark:text-blue-400`) for Actions page identity
- **Form Controls**: `rounded-lg` borders with enhanced focus states and transitions

**Key Improvements Made:**
- Enhanced stats cards with proper padding (`p-6`) and hover effects
- Improved task list items with better spacing and transitions
- Refined modal design with consistent rounded corners and shadows
- Standardized form input styling with proper border radius and transitions
- Applied consistent hover states throughout the interface

**Files Modified:**
- `dashboard/app/dashboard/actions/page.tsx` - Complete styling refactor for design consistency

**Design System Benefits:**
- **Visual Cohesion**: All dashboard pages now follow identical design patterns
- **User Experience**: Consistent interactions and animations across sections
- **Maintainability**: Standardized styling patterns for future development
- **Professional Appearance**: Unified design language throughout the dashboard

**Color Theme System:**
- **System Overview**: Green theme (`text-green-600 dark:text-green-400`) with Home icon
- **Memory Management**: Purple theme (`text-purple-600 dark:text-purple-400`) with Brain icon  
- **Actions & Tasks**: Blue theme (`text-blue-600 dark:text-blue-400`) with Target icon
- **Performance**: Blue theme (`text-blue-600 dark:text-blue-400`) with Activity icon
- **Limitless**: Blue theme (`text-blue-600 dark:text-blue-400`) with Mic icon

### Visual Graph Memory System Enhancement (June 2025)

#### Consolidated Memory Approach Implementation
**Background**: Transformed memory creation approach from multi-memory to single consolidated memory per recording to enable better visual graph representation.

**Previous Approach (2.8 memories per recording):**
- Separate memories for each person mentioned
- Separate memories for key facts/events
- Fragmented information across multiple nodes
- Complex graph with excessive connections

**New Consolidated Approach (1 memory per recording):**
- Single memory containing all recording content
- People stored in `metadata.people_mentioned` array structure
- Maintains all information while simplifying visualization
- Cleaner graph representation with meaningful connections

**Implementation Details:**
```python
# Consolidated memory structure in functionality/limitless.py
consolidated_memory = {
    "content": full_recording_content,
    "metadata": {
        "people_mentioned": [
            {
                "name": person_name,
                "context": speaker_context,
                "is_speaker": True/False
            }
        ],
        "log_id": recording_id,
        "source": "limitless"
    }
}
```

#### Advanced Visual Graph System
**Purpose**: Create professional force-directed graph visualization for memory relationships with anti-clustering technology.

**Key Features Implemented:**
1. **Anti-Clustering Force Simulation**
   - Significantly stronger repulsion forces (3000 vs 1500)
   - Weaker center force (0.005 vs 0.02) to prevent node clustering
   - Scale-aware force adjustments for consistent behavior at all zoom levels
   - Spiral initial positioning pattern for optimal distribution

2. **Zoom-Stable Visualization**
   - Simulation pause during zoom operations to prevent disruption
   - Scale-adjusted force calculations maintain spacing at all zoom levels (49% to 169% tested)
   - Enhanced label rendering with background boxes for readability
   - Dynamic font sizing based on zoom level

3. **Professional Graph Controls**
   - Zoom In/Out buttons with simulation management
   - "Spread Out" button for manual node redistribution
   - Pause/Resume animation controls
   - Reset view functionality
   - Real-time zoom percentage display

4. **Enhanced Node and Link System**
   - Memory nodes: Color-coded by memory type with appropriate icons
   - Entity nodes: Orange (people), Green (places), Purple (other)
   - Frequency-based node sizing for entities
   - Intelligent entity extraction from consolidated metadata
   - Dynamic link creation based on content and metadata relationships

#### Technical Implementation

**Force Simulation Algorithm (MemoryGraph.tsx:213-324):**
```typescript
// Anti-clustering force parameters
const centerForce = 0.005; // Much weaker to prevent clustering
const linkForce = 0.15; // Weaker link force
const repelForce = 3000; // Much stronger repulsion
const scaleAdjustedAlpha = alpha / Math.max(transform.scale, 0.3);

// Enhanced repulsion with wider zone
if (distance < minDistance * 1.5 && distance > 0) {
    const force = (repelForce / Math.max(distance, 10)) * scaleAdjustedAlpha;
    // Apply stronger repulsion forces
}
```

**Entity Extraction System:**
- Primary: Extract from `metadata.people_mentioned` for Limitless recordings
- Fallback: Pattern-based extraction from content for backward compatibility
- Type classification: Person, Place, Other with appropriate colors
- Frequency tracking for node sizing

**Scale-Aware Rendering:**
- Labels only visible above 40% zoom to reduce clutter
- Dynamic font sizing: `Math.max(10, 12 / Math.sqrt(transform.scale))px`
- Background boxes with scale-adjusted stroke width
- Intelligent label truncation based on zoom level

#### Performance Improvements Achieved
- **Zero node clustering** at all tested zoom levels (49% to 169%)
- **Stable zoom experience** with consistent node spacing
- **Professional visualization** comparable to D3.js force-directed graphs
- **Responsive interactions** with smooth animations and controls
- **Memory efficiency** through consolidated approach (1 vs 2.8 memories per recording)

#### User Experience Enhancements
- **Intuitive Navigation**: Standard zoom controls with visual feedback
- **Manual Control**: "Spread Out" button for user-initiated redistribution
- **Visual Clarity**: Color-coded legend and enhanced tooltips
- **Performance Indicators**: Real-time zoom percentage and simulation status
- **Accessibility**: Touch-friendly controls and keyboard navigation support

#### Files Modified
- `dashboard/components/MemoryGraph.tsx` - Complete visual graph implementation
- `dashboard/lib/api.ts` - Enhanced Memory interface with metadata support
- `functionality/limitless.py` - Consolidated memory creation approach

#### Future Enhancements
1. **Graph Persistence**: Save/load graph layouts for consistent user experience
2. **Advanced Filtering**: Node filtering by memory type, date ranges, or entity frequency
3. **Clustering Algorithm**: Smart grouping of related memories with expansion/collapse
4. **Export Functionality**: Save graph visualizations as images or interactive HTML
5. **Performance Analytics**: Track graph performance metrics and optimization opportunities

### Actions & Tasks Management System (June 2025)

#### Comprehensive Task Management Implementation
**Purpose**: Centralized task management system that consolidates tasks from all sources (AI, Voice, Manual, WhatsApp) into a unified dashboard interface.

**Background**: Previously, tasks were only sent to Google Tasks, requiring users to switch between applications. The new Actions page provides complete task visibility and management within the dashboard.

#### Key Features Implemented

**1. Unified Task Dashboard**
- **Single Source of Truth**: All tasks from different sources displayed in one interface
- **Source Attribution**: Visual badges showing task origin (AI Extracted, Voice Recording, Manual, WhatsApp)
- **Task Statistics**: Real-time dashboard showing total, completed, due today, and overdue tasks
- **Source Distribution Analytics**: Visual breakdown of tasks by creation source

**2. Advanced Search & Filtering System**
- **Enhanced Search Bar**: Full-width search with icon, clear button, and improved placeholder text
- **Professional Filter Layout**: Labeled dropdowns with proper spacing and visual hierarchy
- **Multiple Filter Types**: Source, due date, completion status, and sorting options
- **Responsive Design**: Optimized layout that works across all screen sizes

**3. Task Management Operations**
- **Full CRUD Support**: Create, read, update, delete operations for all tasks
- **Quick Actions**: One-click task completion and deletion with confirmation
- **Completion Toggle**: Easy switching between completed/incomplete status
- **Due Date Management**: Visual priority indicators and overdue detection

**4. Professional UI Design**
- **Blue Color Theme**: Distinct from other pages (Memory: Purple, Overview: Green)
- **Card-Based Layout**: Modern design with proper shadows and rounded corners
- **Enhanced Typography**: Consistent font weights and visual hierarchy
- **Dark Mode Support**: Complete dark/light mode compatibility with proper contrast

#### Technical Implementation

**Backend API (`api/dashboard/task_routes.py`):**
```python
# Comprehensive REST API endpoints
GET    /api/dashboard/tasks/           # Get all tasks with filtering
POST   /api/dashboard/tasks/           # Create new tasks
PUT    /api/dashboard/tasks/{id}       # Update existing tasks
DELETE /api/dashboard/tasks/{id}       # Delete tasks
POST   /api/dashboard/tasks/{id}/complete  # Quick complete action
GET    /api/dashboard/tasks/stats      # Task statistics
GET    /api/dashboard/tasks/upcoming   # Upcoming tasks
```

**Frontend Implementation (`dashboard/app/dashboard/actions/page.tsx`):**
- **State Management**: React hooks for task data, filters, and UI state
- **API Integration**: Comprehensive error handling and loading states
- **Form Validation**: Client-side validation for task creation
- **Real-time Updates**: Automatic refresh after task operations

**Enhanced API Client (`dashboard/lib/api.ts`):**
```typescript
// New TypeScript interfaces for task management
interface Task {
  id: string;
  title: string;
  notes?: string;
  due_date?: string;
  status: 'needsAction' | 'completed';
  source: 'ai_extracted' | 'natural_language' | 'manual' | 'voice_command';
  is_overdue: boolean;
  due_display?: string;
  days_until_due?: number;
}

interface TaskStats {
  total_tasks: number;
  completed_tasks: number;
  due_today: number;
  overdue_tasks: number;
  completion_rate: number;
  source_distribution: Record<string, number>;
}
```

#### Integration Points

**Google Tasks API Integration:**
- **Full Compatibility**: Works with existing Google Tasks infrastructure
- **Bidirectional Sync**: Tasks created in dashboard appear in Google Tasks
- **OAuth Authentication**: Secure access using existing Google credentials
- **Error Handling**: Graceful fallbacks when API is unavailable

**Limitless AI Integration:**
- **Automatic Task Extraction**: AI analyzes recordings and creates relevant tasks
- **Source Attribution**: Tasks marked with 'ai_extracted' or 'natural_language' sources
- **Speaker Context**: Tasks include information about who mentioned them
- **WhatsApp Integration**: Voice commands create tasks with 'voice_command' source

#### Dashboard Consistency Improvements

**Standardized Page Headers:**
- **Icon System**: Each page has distinct color-coded icons (Home: Green, Brain: Purple, Target: Blue)
- **Consistent Layout**: Unified header structure across all pages
- **Typography Standards**: Matching font sizes, weights, and spacing
- **Responsive Behavior**: Mobile-optimized layouts throughout

**Enhanced Navigation:**
- **Actions Menu Item**: Added to sidebar with Target icon
- **Visual Hierarchy**: Clear distinction between different dashboard sections
- **User Experience**: Intuitive navigation patterns across the entire application

#### Performance & User Experience

**Search & Filter Performance:**
- **Client-side Filtering**: Fast response times for search and filter operations
- **Debounced Search**: Optimized search input to prevent excessive API calls
- **Efficient State Management**: Minimal re-renders and optimized component updates
- **Responsive Interactions**: Smooth transitions and hover effects

**Accessibility Features:**
- **Keyboard Navigation**: Full keyboard support for all interactive elements
- **Focus Management**: Proper focus indicators and tab order
- **Screen Reader Support**: Semantic HTML and ARIA labels
- **Color Contrast**: WCAG-compliant contrast ratios in both light and dark modes

#### Development Workflow Enhancements

**Code Organization:**
- **Modular Structure**: Separate API routes, components, and utilities
- **Type Safety**: Comprehensive TypeScript interfaces throughout
- **Error Boundaries**: Proper error handling and user feedback
- **Testing Ready**: Structure supports unit and integration testing

**Documentation Standards:**
- **Code Comments**: Clear documentation for complex functions
- **API Documentation**: Comprehensive endpoint documentation
- **Component Documentation**: PropTypes and usage examples
- **Development Commands**: Updated with Actions page development workflow

#### Future Enhancement Roadmap

1. **Advanced Task Features**: Recurring tasks, task templates, and bulk operations
2. **Integration Expansion**: Additional task sources (Notion, Todoist, etc.)
3. **Analytics Dashboard**: Task completion trends and productivity metrics
4. **Collaboration Features**: Task sharing and team collaboration tools
5. **Mobile App Integration**: Native mobile app with push notifications

### Dashboard UI Consistency Standards (June 2025)

#### Color Theme System
**Established color-coded page themes for visual hierarchy and user navigation:**

- **🏠 System Overview**: Green theme (`text-green-600 dark:text-green-400`)
  - Icon: Home (matches sidebar navigation)
  - Purpose: Dashboard landing page and system monitoring

- **🧠 Memory Management**: Purple theme (`text-purple-600 dark:text-purple-400`)  
  - Icon: Brain
  - Purpose: AI knowledge base and memory operations

- **🎯 Actions & Tasks**: Blue theme (`text-blue-600 dark:text-blue-400`)
  - Icon: Target  
  - Purpose: Task management and action items

#### Page Header Standards
**Consistent header pattern across all dashboard pages:**

```tsx
<h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center space-x-2">
  <Icon className="h-8 w-8 text-{color}-600 dark:text-{color}-400" />
  <span>Page Title</span>
</h1>
<p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
  Page description without dynamic counts
</p>
```

#### Design System Improvements
- **Removed Dynamic Counts**: Cleaned up page descriptions by removing automatic counting
- **Enhanced Dark Mode**: Complete dark/light mode support with proper contrast ratios
- **Consistent Spacing**: Standardized margins, padding, and component spacing
- **Professional Styling**: Rounded corners, shadows, and smooth transitions throughout

### Memory Management Mobile Responsiveness & UI Improvements (June 2025)

#### Comprehensive Mobile Optimization Implementation
**Background**: Addressed critical mobile responsiveness issues in Memory Management dashboard, removed redundant features, and enhanced professional appearance.

#### Major Mobile Responsiveness Fixes
**Issues Resolved:**
1. **Table Layout Cuts Off**: "Created On" column not visible on mobile
2. **Content Overflow**: Elements extending beyond screen width
3. **Poor Touch Targets**: Buttons too small for mobile interaction
4. **Horizontal Scrolling**: Layout forcing unwanted horizontal scroll

**Solutions Implemented:**

**1. Responsive Table-to-Card Layout**
- **Desktop (≥768px)**: Professional table with all columns visible
- **Mobile (<768px)**: Automatic conversion to touch-friendly cards
- **Implementation**: Hidden table on mobile, shown card layout with all memory information
- **File**: `dashboard/app/dashboard/memories/page.tsx`

**2. Mobile-Optimized Search & Filters**
- **Enhanced Search Bar**: Larger touch targets (py-3 on mobile vs py-2.5 on desktop)
- **Clear Button**: Added X button for easy search clearing
- **Responsive Filter Controls**: Full-width on mobile, optimized spacing
- **Better Typography**: Base font size on mobile (text-base) for accessibility

**3. Touch-Friendly Interactions**
- **Larger Button Targets**: Increased from p-1.5 to p-2 on mobile (44px minimum)
- **Enhanced Icons**: Bigger icons on mobile (h-5 w-5 vs h-4 w-4)
- **Improved Hover States**: Optimized for both mouse and touch interactions

**4. Grid View Responsiveness**
- **Responsive Columns**: 1 col mobile → 2 col tablet → 3-4 cols desktop
- **Proper Spacing**: Adjusted gaps (gap-4 mobile, gap-6 desktop)
- **Mobile Padding**: Added horizontal padding for better mobile layout

#### Interface Simplification
**Removed Redundant Grid View:**
- **Rationale**: Grid view was redundant since Table view already provides responsive cards on mobile
- **Benefits**: Reduced bundle size by 4KB, cleaner interface, better UX
- **Maintained Features**: Table view (responsive) + Visual Graph view
- **Code Cleanup**: Removed 200+ lines of duplicate code, unused imports

**Removed Refresh Button:**
- **Rationale**: Data already refreshes automatically on filter/search/pagination changes
- **Benefits**: Cleaner header layout, reduced visual clutter
- **Better Mobile UX**: More space for important "Create Memory" button

#### Professional Header Redesign
**Enhanced Create Memory Button:**
- **Gradient Styling**: `bg-gradient-to-r from-purple-600 to-purple-700`
- **Enhanced Shadows**: `shadow-lg hover:shadow-xl` for depth
- **Smooth Animations**: `transform hover:scale-105` for interaction feedback
- **Consistent Sizing**: Full-width on mobile, optimal sizing on desktop
- **Right Alignment**: All buttons (view toggle + create) aligned to right side

**Improved Layout Structure:**
- **Clear Separation**: Header section vs controls section
- **Better Spacing**: Organized with `space-y-4` and consistent gaps
- **Visual Hierarchy**: Enhanced typography and component organization
- **Mobile-First**: Responsive design that works up from mobile

#### Technical Implementation Details

**Responsive Breakpoints:**
- **Mobile**: 320px - 767px (iPhone SE to large phones)
- **Tablet**: 768px - 1023px (iPad and tablet devices)
- **Desktop**: 1024px+ (laptop and desktop screens)

**Mobile Card Layout Structure:**
```tsx
{/* Mobile Card View - Only visible on screens < 768px */}
<div className="md:hidden space-y-4 p-4">
  {memories.map((memory) => (
    <div key={memory.id} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border p-4">
      {/* Card content with memory info, badges, and actions */}
    </div>
  ))}
</div>
```

**Performance Optimizations:**
- **Reduced Bundle**: Removed grid view components (-4KB)
- **Efficient Rendering**: Mobile cards only render when needed
- **Touch Optimization**: Larger touch targets reduce misclicks
- **Smooth Transitions**: 200ms transitions for professional feel

#### Accessibility Improvements
- **WCAG Compliance**: Proper contrast ratios in light/dark modes
- **Touch Targets**: Minimum 44px tap targets on mobile
- **Keyboard Navigation**: Full keyboard support maintained
- **Screen Reader**: Semantic HTML and proper ARIA labels
- **Focus Management**: Clear focus indicators and logical tab order

#### Testing & Validation
**Puppeteer MCP Testing:**
- **Desktop Views**: Verified table layout and button positioning
- **Mobile Views**: Confirmed card layout and touch interactions
- **Responsive Behavior**: Tested breakpoint transitions
- **Cross-Device**: Validated on multiple screen sizes

**Screen Size Testing:**
- ✅ **iPhone SE (320px)**: Perfect card layout
- ✅ **iPhone 12 (375px)**: Optimal button sizing
- ✅ **iPad (768px)**: Smooth transition to desktop
- ✅ **Desktop (1440px)**: Professional table layout

#### Results Achieved
- **✅ Zero horizontal overflow** on any screen size
- **✅ All memory information accessible** on mobile
- **✅ Professional appearance** across all devices
- **✅ Touch-friendly interactions** with proper feedback
- **✅ Simplified, focused interface** without redundancy
- **✅ Faster loading** with reduced bundle size
- **✅ Better accessibility** with proper touch targets

#### Files Modified
- `dashboard/app/dashboard/memories/page.tsx` - Complete mobile responsiveness overhaul
- Removed unused components: `MemoryCardSkeleton`, Grid view code
- Cleaned imports: `Grid3X3`, `FileText`, `MoreHorizontal`, `RefreshCw`

#### Commands for Testing Mobile Layout
```bash
# Start local development
docker-compose -f docker-compose.local.yml up -d

# Access Memory Management page
open http://localhost:3000/dashboard/memories

# Test mobile view in browser dev tools:
# 1. Open Chrome DevTools (F12)
# 2. Click device toolbar (Ctrl+Shift+M)
# 3. Select mobile device or set custom width (375px)
# 4. Verify card layout and touch interactions
```

### Limitless Performance Breakthrough (June 2025 PM)

#### Major Performance Optimizations - 30x Speed Improvement

**Background**: Achieved breakthrough performance improvements for Limitless processing, reducing average processing time from 60 seconds to 2 seconds per recording.

#### Performance Bottlenecks Identified & Fixed

**1. Speaker Identification Optimization (35.6s → <0.1s)**
- **Issue**: `get_context_from_title_and_summary()` was making Gemini AI API calls for each unrecognized speaker
- **Root Cause**: Using AI to generate simple context descriptions like "Solo recording" or "Participant in conversation"
- **Solution**: Replaced AI-powered context generation with deterministic logic
- **Implementation**: Simple if/else logic instead of `simple_prompt_request()` API call
- **Impact**: 356x speed improvement, eliminated the primary bottleneck

**2. Natural Language Task Extraction Optimization (54.4s → 0s)**
- **Issue**: Separate `extract_natural_language_tasks()` function making additional AI API call
- **Root Cause**: Two separate AI calls - one for task detection, another for general extraction
- **Solution**: Merged task extraction into main AI extraction call
- **Implementation**: 
  - Enhanced `get_enhanced_extraction_prompt()` to include natural language task patterns
  - Skip separate natural language task extraction
  - Handle both task types in single AI response
- **Impact**: Eliminated redundant API call, reduced from 2 to 1 per recording

**3. Memory Creation Optimization (4.3s → <0.5s)**
- **Issue**: `create_consolidated_recording_memory()` calling expensive duplicate check
- **Root Cause**: 
  - `memory_manager.get_all_memories()` loading ALL user memories (500+) just to check duplicates
  - Additional AI deduplication call in `create_memory()`
- **Solution**: 
  - Fast Redis key lookup: `meta-glasses:limitless:memory_created:{log_id}`
  - Added `skip_deduplication=True` parameter to bypass AI deduplication
  - Batch metadata updates into single operation
  - TTL-based tracking keys (30 days) for efficient duplicate prevention
- **Impact**: 8.5x speed improvement in memory creation

#### Technical Implementation Details

**Variable Collision Fix:**
- **Issue**: `start_time` variable used for both timing measurement (float) and lifelog timestamp (string)
- **Solution**: Renamed timing variable to `processing_start_time` to avoid type error

**API Call Reduction:**
- **Before**: 3+ API calls per recording (speaker context + task detection + general extraction)
- **After**: 1 API call per recording (combined extraction)

**Redis Optimization:**
- **Tracking Keys**: `meta-glasses:limitless:memory_created:{log_id}` with 30-day TTL
- **Fast Lookups**: Redis EXISTS instead of loading all memories
- **Batch Operations**: Single metadata update instead of multiple Redis calls

#### Dashboard Professional Refactoring

**Operation Naming:**
- Changed "Combined AI Extraction" → "AI Extraction"
- Removed "(Legacy)" labels from UI
- Silently merge natural language tasks data into AI extraction for old records

**Backend Handling:**
- Filter operations with <0.1s from display
- Merge legacy data without exposing technical details
- Professional operation names in performance metrics

#### Performance Monitoring Commands

```bash
# Monitor Limitless processing performance
docker-compose -f docker-compose.local.yml logs -f app | grep "COMPLETED recording"

# Check specific operation timings
docker-compose -f docker-compose.local.yml logs -f app | grep -E "(Speaker identification|AI extraction|Memory creation):"

# View performance dashboard
open http://localhost:3000/dashboard/performance
# Switch to "Limitless Processing" tab
```

#### Debugging Performance Issues

**If processing is slow, check:**
1. Speaker identification time - should be <0.1s
2. AI extraction time - should be 2-3s (only operation making API call)
3. Memory creation time - should be <0.5s

**Common issues:**
- If speaker identification is slow: Check if `get_context_from_title_and_summary()` is making AI calls
- If memory creation is slow: Check if duplicate checking is loading all memories
- If natural language tasks appear separately: Ensure using latest code with merged extraction

#### Key Files for Performance

- `functionality/limitless.py` - Main processing logic and optimizations
- `utils/memory_manager.py` - Memory creation with skip_deduplication parameter
- `api/dashboard/limitless_routes.py` - Performance metrics and operation naming
- `dashboard/app/dashboard/performance/page.tsx` - Performance visualization

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.