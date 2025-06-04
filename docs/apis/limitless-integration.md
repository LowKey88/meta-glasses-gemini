# Limitless AI Integration

This document describes the integration with Limitless AI for syncing and processing Pendant device recordings.

## Overview

The Limitless integration allows the Meta Glasses assistant to:
- Sync recordings from your Limitless Pendant
- Extract actionable insights from meetings
- Create memories and tasks automatically
- Search through past conversations
- Generate daily summaries

## Setup

### Prerequisites
1. A Limitless Pendant device
2. Limitless API key from [limitless.ai/developers](https://www.limitless.ai/developers)

### Configuration

Add these environment variables to your `.env` file:

```bash
# Required
LIMITLESS_API_KEY=your_api_key_here

# Optional (defaults shown)
LIMITLESS_SYNC_INTERVAL=3600  # Sync interval in seconds
```

## WhatsApp Commands

### Basic Commands

- **`sync limitless`** - Manually sync recent recordings (last 24 hours)
- **`limitless`** - Show help menu with all available commands

### View Recordings

- **`limitless today`** - List today's recordings with summaries
- **`limitless yesterday`** - List yesterday's recordings
- **`limitless summary`** - Get AI-generated summary of today's meetings
- **`limitless summary 2025-01-06`** - Get summary for specific date

### Search Features

- **`limitless search project deadline`** - Search recordings for specific topics
- **`limitless person john`** - Find all discussions mentioning John

## Features

### Automatic Sync
- Background worker syncs every hour (configurable)
- Processes new recordings automatically
- Prevents duplicate processing

### Intelligent Extraction
When processing recordings, the system extracts:
- **Facts**: Key decisions and important information
- **Tasks**: Action items with optional due dates
- **Events**: Mentioned dates and meetings
- **People**: Names and their context/roles

### Memory Creation
- Important facts are stored as memories
- Relationship information is captured
- All memories are searchable

### Task Integration
- Extracted tasks are created in Google Tasks
- Due dates are parsed and set automatically
- Tasks include context from the meeting

### Dashboard Features
Access the Limitless dashboard at `/dashboard/limitless` to:
- View sync status and statistics
- Browse all recordings
- Search through transcripts
- See extracted insights
- Trigger manual sync

## Data Flow

1. **Sync Process**:
   ```
   Limitless API → Redis Cache → AI Processing → Memory/Task Creation
   ```

2. **Search Process**:
   ```
   User Query → Redis Cache Search → Formatted Results
   ```

## API Integration

### Endpoints Used
- `GET /v1/lifelogs` - Retrieve recordings with pagination

### Rate Limits
- Maximum 10 entries per request
- Built-in delays between requests
- Graceful error handling

## Privacy & Security

- All data is cached locally in Redis
- API key is never exposed
- Recordings are processed on-device
- User can control what gets synced

## Troubleshooting

### No recordings found
- Verify your Pendant has recordings
- Check API key is correctly set
- Ensure Pendant is syncing to cloud

### Sync errors
- Check API key validity
- Verify network connectivity
- Review logs for specific errors

### Missing extractions
- Some recordings may not have actionable content
- AI extraction is context-dependent
- Manual review via dashboard available

## Examples

### Morning Routine
```
User: sync limitless
Bot: 🔄 Syncing your Limitless recordings...
Bot: ✅ Limitless Sync Complete
     📝 Recordings processed: 3
     🧠 Memories created: 7
     ✅ Tasks extracted: 4

User: limitless today
Bot: 📅 Today's Recordings (3)
     1. Team Standup
        🕐 09:00 AM
        📝 Discussed project timeline and blockers...
     
     2. Client Call - ABC Corp
        🕐 11:30 AM
        📝 Reviewed Q4 deliverables and pricing...
```

### Finding Information
```
User: limitless person sarah
Bot: 👤 Discussions with 'sarah' (2)
     1. Marketing Review
        📅 Jan 5, 02:00 PM
        👤 Context: Marketing lead, discussed campaign

     2. Budget Planning
        📅 Jan 3, 10:00 AM
        👤 Context: Approved Q1 budget allocation
```

### Daily Summary
```
User: limitless summary
Bot: 📊 Daily Summary - January 6, 2025
     Total recordings: 4
     
     Key themes:
     • Product launch preparation
     • Budget finalization for Q1
     • Team resource allocation
     
     Important decisions:
     • Approved hiring 2 engineers
     • Set launch date for Feb 15
     
     Action items:
     • Send proposal to client (Due: Jan 8)
     • Review design mockups
     • Schedule follow-up with Sarah
```

## Best Practices

1. **Regular Syncing**: Let automatic sync run, manual sync for urgent needs
2. **Clear Meeting Titles**: Help AI better categorize content
3. **Review Extractions**: Check dashboard for accuracy
4. **Search Effectively**: Use specific keywords for better results
5. **Privacy First**: Only sync meetings you want processed

## Future Enhancements

- Real-time sync during meetings
- Custom extraction templates
- Team collaboration features
- Export capabilities
- Integration with calendar events