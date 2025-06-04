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
from utils.gemini import simple_prompt_request
from utils.whatsapp import send_whatsapp_threaded
from functionality.task import create_task, get_task_lists
from functionality.calendar import create_google_calendar_event
from utils.redis_key_builder import RedisKeyBuilder
from functionality.calendar import get_event_color

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


async def sync_recent_lifelogs(phone_number: str, hours: Optional[int] = 24) -> str:
    """
    Sync recent Lifelog entries from Limitless.
    
    Args:
        phone_number: User's phone number
        hours: Number of hours to sync (default 24, None for all recordings)
    """
    try:
        # For initial sync, get all recordings without date filtering
        # to ensure we capture all available recordings
        logger.info(f"Starting Limitless sync for user {phone_number}")
        if hours is None:
            logger.info("Fetching ALL recordings without date filtering for initial sync")
        else:
            logger.info(f"Fetching recordings from last {hours} hours")
        
        # Fetch Lifelogs without date restrictions for initial sync
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=None,
            end_time=None,
            max_entries=10,  # Reduced limit to avoid API quota issues
            include_markdown=True,  # Include full transcript for processing
            include_headings=True
        )
        
        logger.info(f"Fetched {len(lifelogs)} recordings from Limitless API")
        
        if not lifelogs:
            return "No new recordings found in the specified time range."
            
        # Process each Lifelog
        processed_count = 0
        memories_created = 0
        tasks_created = 0
        
        for i, log in enumerate(lifelogs, 1):
            try:
                log_id = log.get('id', 'unknown')
                log_title = log.get('title', 'Untitled')
                logger.info(f"Processing recording {i}/{len(lifelogs)}: {log_title} (ID: {log_id})")
                
                # Check if already processed
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
                if redis_client.exists(processed_key):
                    logger.info(f"Recording {log_id} already processed, skipping")
                    continue
                    
                # Process the Lifelog
                results = await process_single_lifelog(log, phone_number)
                
                memories_created += results['memories_created']
                tasks_created += results['tasks_created']
                processed_count += 1
                
                logger.info(f"Recording {log_id} processed: {results['memories_created']} memories, {results['tasks_created']} tasks created")
                
                # Mark as processed
                redis_client.setex(
                    processed_key,
                    86400 * 30,  # Keep for 30 days
                    "1"
                )
                
                # Delay between processing to respect API rate limits
                await asyncio.sleep(2.0)  # Increased delay to avoid quota issues
                
            except Exception as e:
                logger.error(f"Error processing Lifelog {log.get('id')}: {str(e)}")
                continue
                
        # Update last sync timestamp
        last_sync_key = RedisKeyBuilder.build_limitless_sync_key(phone_number)
        redis_client.set(last_sync_key, datetime.now(timezone.utc).isoformat())
        
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
        
        # Extract transcript from contents array
        transcript = ''
        contents = log.get('contents', [])
        if contents and len(contents) > 0:
            transcript = contents[0].get('content', '')
            
        summary = log.get('summary', '')
        start_time = log.get('start_time')  # API uses start_time not startTime
        end_time = log.get('end_time')      # API uses end_time not endTime
        
        # Always cache the recording, even if no transcript
        # Process transcript only if available
        has_transcript = bool(transcript and transcript.strip())
        
        # Initialize extracted data structure
        extracted = {
            'facts': [],
            'tasks': [],
            'events': [],
            'people': []
        }
        
        # Only process transcript if available
        if has_transcript:
            # First, extract natural language tasks and reminders
            natural_tasks_created = extract_natural_language_tasks(transcript, log_id, phone_number)
            results['tasks_created'] += natural_tasks_created
            
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

            response = simple_prompt_request(extraction_prompt, phone_number)
            
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
                # Continue with empty extracted data rather than returning
                
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
                            
                    success = create_task_from_limitless(task_data, phone_number)
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
        
        redis_client.setex(
            cache_key,
            86400 * 7,  # Cache for 7 days
            json.dumps(cache_data)
        )
        
    except Exception as e:
        logger.error(f"Error processing Lifelog {log.get('id')}: {str(e)}")
        
    return results


def create_task_from_limitless(task_data: Dict, phone_number: str) -> bool:
    """Create a Google Task from Limitless data."""
    try:
        # Get task lists
        lists = get_task_lists()
        if not lists:
            return False
            
        # Use first list or default
        task_list_id = lists[0]['id']
        
        # Create the task
        result = create_task(
            title=task_data.get('title', ''),
            notes=task_data.get('notes', ''),
            due_date=task_data.get('due'),
            list_id=task_list_id
        )
        return result is not None
        
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return False


def extract_natural_language_tasks(transcript: str, log_id: str, phone_number: str) -> int:
    """
    Extract natural language tasks and reminders from transcript.
    
    Detects spoken statements like:
    - "remind me to..."
    - "I need to..."  
    - "my wife told me to buy..."
    - "don't forget to..."
    
    Returns the number of tasks created.
    """
    try:
        # Check if we've already processed this transcript for tasks
        task_key = RedisKeyBuilder.build_limitless_task_created_key(log_id)
        if redis_client.exists(task_key):
            logger.info(f"Natural language tasks already extracted for log {log_id}")
            return 0
        
        # Use Gemini to detect natural language task instructions
        task_detection_prompt = f"""Analyze this conversation transcript and identify any natural language task or reminder instructions.

Look for phrases like:
- "remind me to..."
- "I need to..."
- "don't forget to..."
- "my wife/husband told me to..."
- "I should..."
- "I have to..."
- "make sure to..."
- "remember to..."

Transcript:
{transcript[:4000]}

Return a JSON object with detected tasks:
{{
    "tasks_found": true/false,
    "natural_tasks": [
        {{
            "task_text": "exact task description",
            "urgency": "high/medium/low",
            "context": "who mentioned it or context"
        }}
    ]
}}

Only extract clear, actionable tasks. Ignore vague statements or general discussions.
Be conservative - only extract when you're confident it's a personal task/reminder."""

        response = simple_prompt_request(task_detection_prompt, phone_number)
        
        # Parse the response
        try:
            # Clean up the response - remove markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response.replace('```', '').strip()
                
            task_data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse natural language task response for log {log_id}: {response}")
            return 0
        
        tasks_created = 0
        
        if task_data.get("tasks_found", False):
            natural_tasks = task_data.get("natural_tasks", [])
            
            for task in natural_tasks:
                task_text = task.get("task_text", "").strip()
                urgency = task.get("urgency", "medium")
                context = task.get("context", "")
                
                if task_text and len(task_text) > 5:  # Ensure meaningful task
                    # Create the task
                    task_title = f"{task_text}"
                    task_notes = f"From Limitless recording - {context}" if context else "From Limitless recording"
                    
                    success = create_task_from_limitless({
                        'title': task_title,
                        'notes': task_notes
                    }, phone_number)
                    
                    if success:
                        tasks_created += 1
                        logger.info(f"Created natural language task: {task_title}")
                        
                        # Send WhatsApp notification
                        notification_msg = f"📝 *Task Created from Recording*\n\n✅ {task_title}\n\n_From your Limitless Pendant recording_"
                        send_whatsapp_threaded(notification_msg)
        
        # Mark this transcript as processed for natural language tasks
        redis_client.setex(
            task_key,
            86400 * 7,  # Keep for 7 days
            json.dumps({
                "processed_at": datetime.now().isoformat(),
                "tasks_created": tasks_created,
                "log_id": log_id
            })
        )
        
        if tasks_created > 0:
            logger.info(f"Extracted {tasks_created} natural language tasks from log {log_id}")
        
        return tasks_created
        
    except Exception as e:
        logger.error(f"Error extracting natural language tasks from log {log_id}: {str(e)}")
        return 0


async def get_today_lifelogs(phone_number: str) -> str:
    """Get today's Lifelog recordings."""
    try:
        # Get today's date in YYYY-MM-DD format
        today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        lifelogs = await limitless_client.get_lifelogs_by_date(
            date=today_date,
            include_markdown=False  # Just summaries for listing
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
        # Get yesterday's date in YYYY-MM-DD format
        yesterday_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
        
        lifelogs = await limitless_client.get_lifelogs_by_date(
            date=yesterday_date,
            include_markdown=False  # Just summaries for listing
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
        for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
            
        if not keys:
            return "No cached recordings found. Try 'sync limitless' first."
            
        matches = []
        query_lower = query.lower()
        
        # Search through cached data
        for key in keys:
            data = redis_client.get(key)
            if not data:
                continue
                
            try:
                log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                
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
        for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
            
        if not keys:
            return "No cached recordings found. Try 'sync limitless' first."
            
        matches = []
        person_lower = person_name.lower()
        
        for key in keys:
            data = redis_client.get(key)
            if not data:
                continue
                
            try:
                log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
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
            
        # Get date in YYYY-MM-DD format
        date_str = target_date.strftime('%Y-%m-%d')
        
        # Fetch Lifelogs for that day
        lifelogs = await limitless_client.get_lifelogs_by_date(
            date=date_str,
            include_markdown=False  # Just summaries for processing
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

        ai_summary = simple_prompt_request(summary_prompt, phone_number)
        
        # Format response
        date_str = target_date.strftime('%B %d, %Y')
        response = f"📊 *Daily Summary - {date_str}*\n"
        response += f"_Total recordings: {len(lifelogs)}_\n\n"
        response += ai_summary
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating daily summary: {str(e)}")
        return "❌ Error generating daily summary."