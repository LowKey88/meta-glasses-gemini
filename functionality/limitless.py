"""
Limitless AI integration for syncing Pendant recordings with the assistant.
"""
import re
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import asyncio

from utils.limitless_api import LimitlessAPIClient
from utils.redis_utils import r as redis_client
from utils.memory_manager import MemoryManager
from utils.gemini import get_response
from utils.whatsapp import send_message
from utils.google_api import (
    create_event,
    search_events,
    create_task,
    get_task_lists
)
from utils.redis_key_builder import RedisKeyBuilder
from functionality.calendar import generate_color_id

logger = logging.getLogger(__name__)

# Initialize clients
limitless_client = LimitlessAPIClient()
memory_manager = MemoryManager()


async def process_limitless_command(command: str, phone_number: str) -> str:
    """
    Process Limitless-related commands from WhatsApp.
    
    Commands:
    - sync limitless: Sync recent recordings
    - limitless today: Show today's recordings
    - limitless yesterday: Show yesterday's recordings
    - limitless search [query]: Search transcripts
    - limitless person [name]: Find discussions with person
    - limitless summary [date]: Get daily summary
    """
    command = command.lower().strip()
    
    # Remove 'limitless' prefix if present
    if command.startswith("limitless "):
        command = command[10:]
    elif command == "limitless":
        return await get_limitless_help()
        
    # Route to appropriate handler
    if command == "sync" or command == "sync limitless":
        return await sync_recent_lifelogs(phone_number)
    elif command == "today":
        return await get_today_lifelogs(phone_number)
    elif command == "yesterday":
        return await get_yesterday_lifelogs(phone_number)
    elif command.startswith("search "):
        query = command[7:]
        return await search_lifelogs(query, phone_number)
    elif command.startswith("person "):
        person_name = command[7:]
        return await find_person_discussions(person_name, phone_number)
    elif command.startswith("summary"):
        # Extract date if provided
        parts = command.split()
        date_str = parts[1] if len(parts) > 1 else None
        return await get_daily_summary(date_str, phone_number)
    else:
        return await get_limitless_help()


async def get_limitless_help() -> str:
    """Return help text for Limitless commands."""
    return """🎙️ *Limitless Commands:*

• *sync limitless* - Sync recent recordings
• *limitless today* - Today's recordings
• *limitless yesterday* - Yesterday's recordings  
• *limitless search [query]* - Search transcripts
• *limitless person [name]* - Find discussions with person
• *limitless summary [date]* - Daily summary

_Example: "limitless search project deadline"_"""


async def sync_recent_lifelogs(phone_number: str, hours: int = 24) -> str:
    """
    Sync recent Lifelog entries from Limitless.
    
    Args:
        phone_number: User's phone number
        hours: Number of hours to sync (default 24)
    """
    try:
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        # Get last sync timestamp
        last_sync_key = RedisKeyBuilder.build_limitless_sync_key(phone_number)
        last_sync = await redis_client.get(last_sync_key)
        
        if last_sync:
            last_sync_time = datetime.fromisoformat(last_sync)
            start_time = max(start_time, last_sync_time)
            
        # Fetch Lifelogs
        await send_message(phone_number, "🔄 Syncing your Limitless recordings...")
        
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=start_time,
            end_time=end_time,
            include_transcript=True,
            include_summary=True
        )
        
        if not lifelogs:
            return "No new recordings found in the specified time range."
            
        # Process each Lifelog
        processed_count = 0
        memories_created = 0
        tasks_created = 0
        
        for log in lifelogs:
            try:
                # Check if already processed
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log['id'])
                if await redis_client.exists(processed_key):
                    continue
                    
                # Process the Lifelog
                results = await process_single_lifelog(log, phone_number)
                
                memories_created += results['memories_created']
                tasks_created += results['tasks_created']
                processed_count += 1
                
                # Mark as processed
                await redis_client.setex(
                    processed_key,
                    86400 * 30,  # Keep for 30 days
                    "1"
                )
                
                # Small delay between processing
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing Lifelog {log.get('id')}: {str(e)}")
                continue
                
        # Update last sync timestamp
        await redis_client.set(last_sync_key, end_time.isoformat())
        
        # Build response
        response = f"""✅ *Limitless Sync Complete*

📝 Recordings processed: {processed_count}
🧠 Memories created: {memories_created}
✅ Tasks extracted: {tasks_created}

_Use "limitless today" to see today's recordings_"""
        
        return response
        
    except Exception as e:
        logger.error(f"Error syncing Limitless: {str(e)}")
        return "❌ Error syncing Limitless recordings. Please check your API key."


async def process_single_lifelog(log: Dict, phone_number: str) -> Dict[str, int]:
    """
    Process a single Lifelog entry to extract memories and tasks.
    
    Returns:
        Dict with counts of created items
    """
    results = {
        'memories_created': 0,
        'tasks_created': 0,
        'events_created': 0
    }
    
    try:
        # Extract basic info
        log_id = log.get('id')
        title = log.get('title', 'Untitled Recording')
        transcript = log.get('transcript', '')
        summary = log.get('summary', '')
        start_time = log.get('startTime')
        end_time = log.get('endTime')
        
        if not transcript:
            return results
            
        # Use Gemini to extract structured information
        extraction_prompt = f"""Analyze this meeting transcript and extract:

1. Key facts and decisions (for memory storage)
2. Action items and tasks with deadlines
3. Important dates or events mentioned
4. People mentioned and their roles/context

Title: {title}
Summary: {summary}
Transcript: {transcript[:3000]}  # Limit for token size

Return a JSON object with:
{{
    "facts": ["fact1", "fact2"],
    "tasks": [{{"description": "task", "due_date": "YYYY-MM-DD or null"}}],
    "events": [{{"title": "event", "date": "YYYY-MM-DD", "time": "HH:MM or null"}}],
    "people": [{{"name": "person", "context": "their role or relationship"}}]
}}

Be specific and extract only clearly stated information."""

        response = await get_response(extraction_prompt, phone_number)
        
        # Parse the response
        try:
            # Handle markdown-wrapped JSON
            if "```json" in response:
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    response = json_match.group(1)
            elif "```" in response:
                json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    response = json_match.group(1)
                    
            extracted = json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Gemini response for Lifelog {log_id}")
            return results
            
        # Store facts as memories
        for fact in extracted.get('facts', []):
            if fact and len(fact) > 10:  # Skip very short facts
                memory_text = f"From {title}: {fact}"
                success = await memory_manager.create_memory(
                    user_id=phone_number,
                    text=memory_text,
                    memory_type='fact',
                    metadata={'source': 'limitless', 'log_id': log_id}
                )
                if success:
                    results['memories_created'] += 1
                    
        # Create tasks
        for task in extracted.get('tasks', []):
            if task.get('description'):
                # Create Google Task
                task_data = {
                    'title': task['description'],
                    'notes': f"From Limitless recording: {title}"
                }
                
                if task.get('due_date'):
                    try:
                        due = datetime.strptime(task['due_date'], '%Y-%m-%d')
                        task_data['due'] = due.isoformat() + 'Z'
                    except:
                        pass
                        
                success = await create_task_from_limitless(task_data, phone_number)
                if success:
                    results['tasks_created'] += 1
                    
        # Store people as relationship memories
        for person in extracted.get('people', []):
            if person.get('name') and person.get('context'):
                memory_text = f"{person['name']}: {person['context']}"
                await memory_manager.create_memory(
                    user_id=phone_number,
                    text=memory_text,
                    memory_type='relationship',
                    metadata={'source': 'limitless', 'log_id': log_id}
                )
                
        # Cache the processed Lifelog
        cache_key = RedisKeyBuilder.build_limitless_lifelog_key(log_id)
        cache_data = {
            'id': log_id,
            'title': title,
            'summary': summary,
            'start_time': start_time,
            'end_time': end_time,
            'extracted': extracted,
            'processed_at': datetime.now().isoformat()
        }
        
        await redis_client.setex(
            cache_key,
            86400 * 7,  # Cache for 7 days
            json.dumps(cache_data)
        )
        
    except Exception as e:
        logger.error(f"Error processing Lifelog {log.get('id')}: {str(e)}")
        
    return results


async def create_task_from_limitless(task_data: Dict, phone_number: str) -> bool:
    """Create a Google Task from Limitless data."""
    try:
        # Get task lists
        lists = await get_task_lists(phone_number)
        if not lists:
            return False
            
        # Use first list or default
        task_list_id = lists[0]['id']
        
        # Create the task
        result = await create_task(phone_number, task_list_id, task_data)
        return result is not None
        
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return False


async def get_today_lifelogs(phone_number: str) -> str:
    """Get today's Lifelog recordings."""
    try:
        # Get today's date range
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=today,
            end_time=tomorrow,
            include_transcript=False,  # Just summaries for listing
            include_summary=True
        )
        
        if not lifelogs:
            return "No recordings found for today."
            
        # Format the response
        response = f"📅 *Today's Recordings ({len(lifelogs)})*\n\n"
        
        for i, log in enumerate(lifelogs, 1):
            title = log.get('title', 'Untitled')
            summary = log.get('summary', 'No summary available')
            start_time = log.get('startTime', '')
            
            # Parse and format time
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    time_str = dt.strftime('%I:%M %p')
                except:
                    time_str = ''
            else:
                time_str = ''
                
            response += f"{i}. *{title}*\n"
            response += f"   🕐 {time_str}\n"
            response += f"   📝 {summary[:100]}...\n\n"
            
        response += "_Use 'limitless search [topic]' to search recordings_"
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting today's Lifelogs: {str(e)}")
        return "❌ Error retrieving today's recordings."


async def get_yesterday_lifelogs(phone_number: str) -> str:
    """Get yesterday's Lifelog recordings."""
    try:
        # Get yesterday's date range
        yesterday = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        today = yesterday + timedelta(days=1)
        
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=yesterday,
            end_time=today,
            include_transcript=False,
            include_summary=True
        )
        
        if not lifelogs:
            return "No recordings found for yesterday."
            
        # Format similar to today's response
        response = f"📅 *Yesterday's Recordings ({len(lifelogs)})*\n\n"
        
        for i, log in enumerate(lifelogs, 1):
            title = log.get('title', 'Untitled')
            summary = log.get('summary', 'No summary available')
            start_time = log.get('startTime', '')
            
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    time_str = dt.strftime('%I:%M %p')
                except:
                    time_str = ''
            else:
                time_str = ''
                
            response += f"{i}. *{title}*\n"
            response += f"   🕐 {time_str}\n"
            response += f"   📝 {summary[:100]}...\n\n"
            
        return response
        
    except Exception as e:
        logger.error(f"Error getting yesterday's Lifelogs: {str(e)}")
        return "❌ Error retrieving yesterday's recordings."


async def search_lifelogs(query: str, phone_number: str) -> str:
    """Search through cached Lifelog transcripts."""
    try:
        # Get all cached Lifelogs
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
            
        if not keys:
            return "No cached recordings found. Try 'sync limitless' first."
            
        matches = []
        query_lower = query.lower()
        
        # Search through cached data
        for key in keys:
            data = await redis_client.get(key)
            if not data:
                continue
                
            try:
                log_data = json.loads(data)
                
                # Search in title, summary, and extracted data
                title = log_data.get('title', '').lower()
                summary = log_data.get('summary', '').lower()
                extracted = log_data.get('extracted', {})
                
                # Check if query matches
                if (query_lower in title or 
                    query_lower in summary or
                    any(query_lower in fact.lower() for fact in extracted.get('facts', [])) or
                    any(query_lower in task.get('description', '').lower() for task in extracted.get('tasks', []))):
                    
                    matches.append(log_data)
                    
            except json.JSONDecodeError:
                continue
                
        if not matches:
            return f"No recordings found matching '{query}'."
            
        # Format results
        response = f"🔍 *Search Results for '{query}' ({len(matches)})*\n\n"
        
        for i, log in enumerate(matches[:5], 1):  # Limit to 5 results
            title = log.get('title', 'Untitled')
            summary = log.get('summary', 'No summary')
            start_time = log.get('start_time', '')
            
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    date_str = dt.strftime('%b %d, %I:%M %p')
                except:
                    date_str = ''
            else:
                date_str = ''
                
            response += f"{i}. *{title}*\n"
            response += f"   📅 {date_str}\n"
            response += f"   📝 {summary[:150]}...\n\n"
            
        if len(matches) > 5:
            response += f"_...and {len(matches) - 5} more results_"
            
        return response
        
    except Exception as e:
        logger.error(f"Error searching Lifelogs: {str(e)}")
        return "❌ Error searching recordings."


async def find_person_discussions(person_name: str, phone_number: str) -> str:
    """Find all discussions mentioning a specific person."""
    try:
        # Search for the person in cached Lifelogs
        pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
            
        if not keys:
            return "No cached recordings found. Try 'sync limitless' first."
            
        matches = []
        person_lower = person_name.lower()
        
        for key in keys:
            data = await redis_client.get(key)
            if not data:
                continue
                
            try:
                log_data = json.loads(data)
                extracted = log_data.get('extracted', {})
                
                # Check people mentioned
                people = extracted.get('people', [])
                for person in people:
                    if person_lower in person.get('name', '').lower():
                        matches.append({
                            'log': log_data,
                            'context': person.get('context', 'No context')
                        })
                        break
                        
            except json.JSONDecodeError:
                continue
                
        if not matches:
            return f"No discussions found with '{person_name}'."
            
        # Format results
        response = f"👤 *Discussions with '{person_name}' ({len(matches)})*\n\n"
        
        for i, match in enumerate(matches[:5], 1):
            log = match['log']
            context = match['context']
            title = log.get('title', 'Untitled')
            start_time = log.get('start_time', '')
            
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    date_str = dt.strftime('%b %d, %I:%M %p')
                except:
                    date_str = ''
            else:
                date_str = ''
                
            response += f"{i}. *{title}*\n"
            response += f"   📅 {date_str}\n"
            response += f"   👤 Context: {context}\n\n"
            
        return response
        
    except Exception as e:
        logger.error(f"Error finding person discussions: {str(e)}")
        return "❌ Error searching for person."


async def get_daily_summary(date_str: Optional[str], phone_number: str) -> str:
    """Get a summary of recordings for a specific date."""
    try:
        # Parse date or use today
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                return "Invalid date format. Use YYYY-MM-DD."
        else:
            target_date = datetime.now()
            
        # Set to UTC and get date range
        target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        next_day = target_date + timedelta(days=1)
        
        # Fetch Lifelogs for that day
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=target_date,
            end_time=next_day,
            include_transcript=False,
            include_summary=True
        )
        
        if not lifelogs:
            date_str = target_date.strftime('%B %d, %Y')
            return f"No recordings found for {date_str}."
            
        # Use Gemini to create a cohesive summary
        summaries = []
        for log in lifelogs:
            title = log.get('title', 'Untitled')
            summary = log.get('summary', '')
            if summary:
                summaries.append(f"{title}: {summary}")
                
        combined_text = "\n\n".join(summaries)
        
        summary_prompt = f"""Create a concise daily summary from these meeting recordings:

{combined_text}

Provide:
1. Key themes discussed
2. Important decisions made
3. Action items identified
4. Notable insights

Keep it brief and well-structured."""

        ai_summary = await get_response(summary_prompt, phone_number)
        
        # Format response
        date_str = target_date.strftime('%B %d, %Y')
        response = f"📊 *Daily Summary - {date_str}*\n"
        response += f"_Total recordings: {len(lifelogs)}_\n\n"
        response += ai_summary
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating daily summary: {str(e)}")
        return "❌ Error generating daily summary."