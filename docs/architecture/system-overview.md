# System Overview

## Architecture Overview
The Meta Glasses AI Assistant is built on a modular service architecture that integrates voice commands from Meta Rayban smart glasses with AI-powered task management through WhatsApp.

## Core Components
1. **Voice Command Processing**
   - Captures audio through Meta Rayban glasses
   - Transmits to WhatsApp API interface
   - Processes through FastAPI backend

2. **Service Architecture**
   - **functionality/**: Domain-specific handlers
     - Audio processing
     - Calendar management
     - Task tracking
     - Image analysis
     - Notion integration
     - Nutrition tracking
     - Search capabilities
   - **utils/**: Shared infrastructure
     - Cloud storage
     - Gemini AI integration
     - Google API services
     - Redis utilities
     - WhatsApp communication

3. **Data Flow**
   ```
   User Voice Command → Glasses Audio Capture
         ↓
   WhatsApp API → FastAPI Backend
         ↓
   Gemini AI Processing
         ↓
   Service Integration
   (Calendar/Tasks/Notion)
   ```

## Key Features
1. **Calendar Management**
   - Bi-directional sync with Google Calendar
   - Smart time validation
   - Timezone-aware operations (Asia/Kuala_Lumpur)
   - Direct event cancellation

2. **Task Management**
   - AI-driven intent detection
   - CRUD operations via Google Tasks API
   - Index-based task referencing
   - Enhanced user feedback

3. **State Management**
   - Redis-backed caching
   - TTL-based cleanup
   - Automatic expired data removal
   - Memory optimization

## Performance Metrics
- Response Time: < 800ms for WhatsApp messages
- Uptime: 99.9% for core services
- Sync Interval: 5-minute periodic sync
- Cache Window: 7-day sync limit
- Memory Limit: 1GB max
- Thread Pool: 50 threads max

## Security
- WhatsApp business account verification
- Google OAuth with HTTPS endpoints
- API key authentication (x-api-key)
- Redis authentication
- Secure credential management

## Deployment
- Dockerized services
- Redis instance
- Volume-mounted credentials
- Health check endpoints
- CORS configuration for Meta domains
