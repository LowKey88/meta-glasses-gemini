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
from utils.gemini import simple_prompt_request, limitless_extraction_request
from utils.whatsapp import send_whatsapp_threaded
from functionality.task import create_task, get_task_lists
from functionality.calendar import create_google_calendar_event
from utils.redis_key_builder import RedisKeyBuilder
from functionality.calendar import get_event_color
from utils.limitless_logger import limitless_logger
from utils.limitless_config import limitless_config

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
    elif command == "force reprocess" or command == "reprocess":
        return await force_reprocess_recent_tasks(phone_number)
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
• *limitless reprocess* - Force reprocess recent recordings
• *limitless today* - Today's recordings
• *limitless yesterday* - Yesterday's recordings  
• *limitless search [query]* - Search transcripts
• *limitless person [name]* - Find discussions with person
• *limitless summary [date]* - Daily summary

_Example: "limitless search project deadline"_"""


async def force_reprocess_recent_tasks(phone_number: str, hours: int = 24) -> str:
    """
    Force reprocessing of recent recordings to fix task counting issues.
    Clears processed flags for recent recordings to ensure they get reprocessed.
    """
    try:
        logger.info(f"🔄 Force reprocessing recent tasks for last {hours} hours")
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Get recent recordings
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=start_time,
            end_time=end_time,
            timezone_str="Asia/Kuala_Lumpur",
            max_entries=None,
            include_markdown=False,
            include_headings=False
        )
        
        cleared_count = 0
        
        # Clear processed flags for recent recordings
        for log in lifelogs:
            log_id = log.get('id')
            if log_id:
                # Clear processed flag
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
                if redis_client.exists(processed_key):
                    redis_client.delete(processed_key)
                    cleared_count += 1
                
                # Clear AI task processed flag  
                ai_task_key = f"meta-glasses:limitless:ai_tasks_processed:{log_id}"
                if redis_client.exists(ai_task_key):
                    redis_client.delete(ai_task_key)
                
                # Clear natural language task flag
                task_key = RedisKeyBuilder.build_limitless_task_created_key(log_id)
                if redis_client.exists(task_key):
                    redis_client.delete(task_key)
        
        logger.info(f"🧹 Cleared processed flags for {cleared_count} recordings")
        
        # Now run normal sync to reprocess
        return await sync_recent_lifelogs(phone_number, hours)
        
    except Exception as e:
        logger.error(f"Error in force reprocessing: {str(e)}")
        return f"❌ Error force reprocessing: {str(e)}"


async def sync_recent_lifelogs(phone_number: str, hours: Optional[int] = 24) -> str:
    """
    Sync recent Lifelog entries from Limitless.
    
    Args:
        phone_number: User's phone number
        hours: Number of hours to sync (default 24, None for all recordings)
    """
    try:
        # Calculate time range based on hours parameter
        logger.info(f"Starting Limitless sync for user {phone_number}")
        start_time = None
        end_time = None
        
        if hours is not None:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            logger.info(f"Fetching recordings from last {hours} hours ({start_time} to {end_time})")
        else:
            logger.info("Fetching ALL recordings without date filtering for initial sync")
        
        # Fetch ALL Lifelogs with time restrictions if specified (no max_entries limit)
        lifelogs = await limitless_client.get_all_lifelogs(
            start_time=start_time,
            end_time=end_time,
            timezone_str="Asia/Kuala_Lumpur", # Set Malaysia Timezone
            max_entries=None,  # Remove limit to fetch ALL recordings using cursor pagination
            include_markdown=True,  # Include full transcript for processing
            include_headings=True
        )
        
        logger.info(f"Fetched {len(lifelogs)} recordings from Limitless API")
        
        # Debug: Log the timestamps of fetched recordings
        if lifelogs:
            latest_times = []
            for log in lifelogs[-5:]:  # Last 5 recordings
                start_time = log.get('start_time') or log.get('startTime') or log.get('createdAt')
                latest_times.append(f"ID: {log.get('id', 'unknown')[:8]}... Time: {start_time}")
            logger.debug(f"📅 Latest 5 recordings from API: {latest_times}")
        
        if not lifelogs:
            return "No new recordings found in the specified time range."
            
        # Process each Lifelog
        processed_count = 0
        skipped_count = 0
        memories_created = 0
        tasks_created = 0
        
        for i, log in enumerate(lifelogs, 1):
            try:
                log_id = log.get('id', 'unknown')
                log_title = log.get('title', 'Untitled')
                
                # Check if already processed
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
                if redis_client.exists(processed_key):
                    skipped_count += 1
                    logger.debug(f"Recording {log_id} already processed, skipping")
                    continue
                    
                logger.info(f"Processing recording {i}/{len(lifelogs)}: {log_title} (ID: {log_id})")
                    
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
                await asyncio.sleep(limitless_config.BATCH_PROCESSING_DELAY)
                
            except Exception as e:
                logger.error(f"Error processing Lifelog {log.get('id')}: {str(e)}")
                continue
                
        # Update last sync timestamp
        last_sync_key = RedisKeyBuilder.build_limitless_sync_key(phone_number)
        redis_client.set(last_sync_key, datetime.now(timezone.utc).isoformat())
        
        # Log summary
        if processed_count > 0 or skipped_count > 0:
            logger.info(f"🔄 Sync summary: {processed_count} processed, {skipped_count} skipped from {len(lifelogs)} total recordings")
        
        # Update pending sync cache (avoid unnecessary API calls on dashboard load)
        try:
            # Count remaining unprocessed recordings from current fetch
            remaining_pending = 0
            for log in lifelogs:
                log_id = log.get('id', 'unknown')
                processed_key = RedisKeyBuilder.build_limitless_processed_key(log_id)
                if not redis_client.exists(processed_key):
                    remaining_pending += 1
            
            # Cache the result for 5 minutes
            pending_sync_key = "meta-glasses:limitless:pending_sync_cache"
            redis_client.setex(pending_sync_key, 300, str(remaining_pending))  # 5 minute cache
            logger.info(f"📊 Updated pending sync cache from sync: {remaining_pending} recordings still pending")
        except Exception as e:
            logger.error(f"Error updating pending sync cache from sync: {str(e)}")
        
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
    Enhanced with speaker identification and robust fallbacks.
    
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
        
        # ✅ NEW: Extract speakers from Limitless API data with fallbacks
        speakers_identified = extract_speakers_from_contents(log)
        logger.info(f"Identified speakers for log {log_id}: {[s['name'] for s in speakers_identified]}")
        
        # Extract transcript from contents array with speaker attribution
        transcript = ''
        contents = log.get('contents', [])
        if contents and len(contents) > 0:
            # Get speaker mapping from previous extraction
            speaker_id_mapping = log.get('_speaker_mapping', {})
            
            # Build transcript with speaker attribution using Speaker N names
            transcript_parts = []
            for content in contents:
                speaker_name = content.get('speakerName', '').strip()
                speaker_id = content.get('speakerIdentifier', '').strip()
                content_text = content.get('content', '').strip()
                
                if content_text:  # Only add non-empty content
                    # Determine the speaker label - NEVER use "Unknown"
                    speaker_label = None
                    
                    if speaker_id == 'user':
                        speaker_label = "You"
                    elif speaker_name and speaker_name.lower() not in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker', '']:
                        # Valid speaker name from API
                        speaker_label = speaker_name
                    elif speaker_id and speaker_id in speaker_id_mapping:
                        # Use mapped Speaker N name for problematic speakers
                        speaker_label = speaker_id_mapping[speaker_id]
                    elif speaker_id:
                        # Unmapped speaker ID - assign next available Speaker N number
                        # Find the highest existing Speaker N in mapping
                        existing_numbers = []
                        for mapped_name in speaker_id_mapping.values():
                            if mapped_name.startswith('Speaker '):
                                try:
                                    num = int(mapped_name.split(' ')[1])
                                    existing_numbers.append(num)
                                except (IndexError, ValueError):
                                    pass
                        next_speaker_num = max(existing_numbers) + 1 if existing_numbers else 0
                        speaker_label = f"Speaker {next_speaker_num}"
                        speaker_id_mapping[speaker_id] = speaker_label  # Cache for consistency
                        logger.debug(f"Assigned unmapped speaker ID '{speaker_id}' to '{speaker_label}'")
                    else:
                        # No speaker info at all - assign next available Speaker N number
                        existing_numbers = []
                        for mapped_name in speaker_id_mapping.values():
                            if mapped_name.startswith('Speaker '):
                                try:
                                    num = int(mapped_name.split(' ')[1])
                                    existing_numbers.append(num)
                                except (IndexError, ValueError):
                                    pass
                        next_speaker_num = max(existing_numbers) + 1 if existing_numbers else 0
                        speaker_label = f"Speaker {next_speaker_num}"
                    
                    transcript_parts.append(f"{speaker_label}: {content_text}")
            
            transcript = '\n'.join(transcript_parts)
        
        # Fallback: try to get transcript from first content if speaker attribution fails
        if not transcript and contents and len(contents) > 0:
            transcript = contents[0].get('content', '')
            logger.debug(f"Using fallback transcript for {log_id[:8]}...")
            
        summary = log.get('summary', '')
        
        # Try different timestamp field names from API response
        start_time = (log.get('start_time') or 
                     log.get('startTime') or 
                     log.get('createdAt') or 
                     log.get('created_at'))
        end_time = (log.get('end_time') or 
                   log.get('endTime') or 
                   log.get('updatedAt') or 
                   log.get('updated_at'))
        
        # Always cache the recording, even if no transcript
        # Process transcript only if available
        has_transcript = bool(transcript and transcript.strip())
        
        # Initialize extracted data structure
        extracted = {
            'facts': [],
            'tasks': [],
            'events': [],
            'people': [],
            'speakers': speakers_identified  # ✅ NEW: Include speaker info
        }
        
        # Initialize natural tasks data
        natural_tasks_data = []
        
        # Only process transcript if available
        if has_transcript:
            # First, extract natural language tasks and reminders
            natural_tasks_created, natural_tasks_data = extract_natural_language_tasks(transcript, log_id, phone_number, title)
            results['tasks_created'] += natural_tasks_created
            
            # ✅ ENHANCED: Use speaker-aware Gemini prompt with fallback
            extraction_prompt = get_enhanced_extraction_prompt(title, summary, transcript)

            response = limitless_extraction_request(extraction_prompt, phone_number)
            
            # Parse the response
            try:
                # Clean and extract JSON from response
                cleaned_response = response.strip()
                
                # Handle markdown-wrapped JSON
                if "```json" in cleaned_response:
                    json_match = re.search(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                    if json_match:
                        cleaned_response = json_match.group(1).strip()
                elif "```" in cleaned_response:
                    json_match = re.search(r'```\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                    if json_match:
                        cleaned_response = json_match.group(1).strip()
                
                # Try to find JSON object if no code blocks
                if not cleaned_response.startswith('{'):
                    json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                    if json_match:
                        cleaned_response = json_match.group(0)
                    else:
                        raise json.JSONDecodeError("No JSON object found in response", cleaned_response, 0)
                
                # Additional cleaning for common issues
                cleaned_response = cleaned_response.replace('\n', ' ')  # Remove newlines that might break parsing
                cleaned_response = re.sub(r',\s*}', '}', cleaned_response)  # Remove trailing commas
                cleaned_response = re.sub(r',\s*]', ']', cleaned_response)  # Remove trailing commas in arrays
                        
                extracted_ai = json.loads(cleaned_response)
                
                # ✅ ENHANCED: Merge AI extraction with speaker data
                extracted['facts'] = extracted_ai.get('facts', [])
                
                # Mark AI-extracted tasks with source before storing
                ai_tasks = extracted_ai.get('tasks', [])
                for task in ai_tasks:
                    if isinstance(task, dict):
                        task['source'] = 'ai_extracted'
                        
                extracted['tasks'] = ai_tasks
                extracted['events'] = extracted_ai.get('events', [])
                
                # Combine AI-extracted people with API speakers
                all_people = []
                
                # Get speaker mapping for standardization
                speaker_id_mapping = log.get('_speaker_mapping', {})
                
                # Add speakers identified from API first (these have correct Speaker N names)
                for speaker in speakers_identified:
                    all_people.append({
                        'name': speaker['name'],
                        'context': speaker['context'],
                        'is_speaker': True,
                        'role': speaker['role']
                    })
                
                # Add AI-extracted people, but filter out and fix any inconsistent naming
                ai_people = extracted_ai.get('people', [])
                existing_names = [p.get('name', '').lower() for p in all_people]
                
                for person in ai_people:
                    person_name = person.get('name', '')
                    
                    # Skip if we already have this person from API speakers
                    if person_name.lower() in existing_names:
                        continue
                    
                    # CRITICAL FIX: Replace any "Unknown" speakers with proper Speaker N naming
                    if person_name.lower() in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker']:
                        # Convert to proper Speaker N naming using current counter
                        current_speaker_numbers = []
                        for existing_person in all_people:
                            existing_name = existing_person.get('name', '')
                            if existing_name.startswith('Speaker ') and existing_person.get('is_speaker'):
                                try:
                                    num = int(existing_name.split(' ')[1])
                                    current_speaker_numbers.append(num)
                                except (IndexError, ValueError):
                                    pass
                        
                        # Find next available Speaker N number
                        next_speaker_number = max(current_speaker_numbers) + 1 if current_speaker_numbers else 0
                        person['name'] = f'Speaker {next_speaker_number}'
                        person['context'] = 'Unrecognized speaker in conversation'
                        person['is_speaker'] = True
                        logger.warning(f"AI generated Unknown speaker, converted to 'Speaker {next_speaker_number}' for {log_id[:8]}...")
                    
                    # Add valid AI-extracted people (named individuals)
                    if person_name and len(person_name.strip()) > 0:
                        all_people.append(person)
                
                extracted['people'] = all_people
                
                # ✅ POST-PROCESSING CLEANUP: Standardize any remaining inconsistent speaker names
                standardized_people = []
                unknown_speaker_counter = 0
                
                for person in extracted['people']:
                    person_name = person.get('name', '')
                    
                    # Fix any "Unknown" speakers that might come from cached data or AI extraction
                    if person_name.lower() in ['unknown', 'unknown speaker'] and person.get('is_speaker'):
                        # Replace with proper Speaker N naming
                        new_speaker_name = f"Speaker {unknown_speaker_counter}"
                        person['name'] = new_speaker_name
                        person['context'] = 'Unrecognized speaker in conversation'
                        logger.info(f"Standardized 'Unknown' speaker to '{new_speaker_name}' for {log_id[:8]}...")
                        unknown_speaker_counter += 1
                    
                    standardized_people.append(person)
                
                extracted['people'] = standardized_people
                
                # ✅ ENHANCED FALLBACK: Ensure tasks have attribution
                for task in extracted.get('tasks', []):
                    if not task.get('assigned_to'):
                        task['assigned_to'] = 'You'  # Default to user
                    if not task.get('assigned_by'):
                        task['assigned_by'] = 'You'  # Default to user
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response for Lifelog {log_id}")
                logger.error(f"JSON Decode Error: {str(e)}")
                logger.error(f"Raw Gemini response (first 500 chars): {response[:500]}")
                logger.debug(f"Full Gemini response for {log_id[:8]}: {response}")
                # Continue with speaker data only
                extracted['people'] = speakers_identified
            
            # ✅ ENHANCED FALLBACK: Always ensure we have at least the primary user in people list
            if not extracted.get('people'):
                logger.debug(f"No people extracted for {log_id[:8]}..., adding user")
                extracted['people'] = [{
                    'name': 'You',
                    'context': 'Primary user (default)',
                    'is_speaker': True,
                    'role': 'primary_user'
                }]
                
            # Store facts as memories
            for fact in extracted.get('facts', []):
                if fact and len(fact) > 10:  # Skip very short facts
                    memory_text = f"From {title}: {fact}"
                    
                    # Check if memory already exists for this log_id and fact
                    existing_memories = memory_manager.get_all_memories(phone_number)
                    duplicate_found = False
                    
                    for existing_mem in existing_memories:
                        metadata = existing_mem.get('metadata', {})
                        # Check if same log_id and similar content
                        if (metadata.get('source') == 'limitless' and 
                            metadata.get('log_id') == log_id and
                            fact.lower() in existing_mem.get('content', '').lower()):
                            logger.debug(f"Skipping duplicate fact for {log_id[:8]}...")
                            duplicate_found = True
                            break
                    
                    if duplicate_found:
                        logger.debug(f"Skipping duplicate memory for log {log_id[:8]}...")
                        continue
                    
                    # Create memory and manually add metadata for tracking
                    memory_id = memory_manager.create_memory(
                        user_id=phone_number,
                        content=memory_text,
                        memory_type='fact'
                    )
                    
                    # Add Limitless source metadata for dashboard stats
                    if memory_id:
                        memory_key = RedisKeyBuilder.get_user_memory_key(phone_number, memory_id)
                        memory_data = redis_client.get(memory_key)
                        if memory_data:
                            memory_obj = json.loads(memory_data.decode() if isinstance(memory_data, bytes) else memory_data)
                            memory_obj['metadata'] = memory_obj.get('metadata', {})
                            memory_obj['metadata']['source'] = 'limitless'
                            memory_obj['metadata']['log_id'] = log_id
                            redis_client.set(memory_key, json.dumps(memory_obj))
                        
                        results['memories_created'] += 1
                        
            # ✅ ENHANCED: Create tasks with speaker attribution and success validation
            validated_tasks = []  # Track only successfully created tasks
            
            # Check if AI tasks were already processed for this log
            ai_task_key = f"meta-glasses:limitless:ai_tasks_processed:{log_id}"
            ai_tasks_already_processed = redis_client.exists(ai_task_key)
            
            if not ai_tasks_already_processed:
                for task in extracted.get('tasks', []):
                    if task.get('description'):
                        # Create Google Task with enhanced metadata
                        task_title = task['description']
                        task_notes = f"From Limitless recording: {title}"
                        
                        # ✅ NEW: Add speaker attribution to task notes
                        if task.get('assigned_to'):
                            task_notes += f"\nAssigned to: {task['assigned_to']}"
                        if task.get('assigned_by'):
                            task_notes += f"\nMentioned by: {task['assigned_by']}"
                        
                        task_data = {
                            'title': task_title,
                            'notes': task_notes
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
                            # FIXED: Only store successfully created tasks
                            task_with_success = task.copy()
                            task_with_success['created_successfully'] = True
                            task_with_success['google_task_created'] = True
                            task_with_success['source'] = 'ai_extracted'
                            validated_tasks.append(task_with_success)
                        else:
                            # Mark as failed but still log for debugging
                            logger.warning(f"Failed to create Google Task: {task_title}")
                            # Don't add to validated_tasks - this excludes it from counts
                
                # Mark AI tasks as processed to prevent duplicate creation
                redis_client.setex(ai_task_key, 86400 * 7, "1")  # 7 days TTL
            else:
                logger.debug(f"AI tasks already processed for {log_id[:8]}..., skipping task creation")
                # Preserve existing successful tasks from cache (both AI and natural language)
                for task in extracted.get('tasks', []):
                    if isinstance(task, dict) and task.get('created_successfully') is True:
                        # Include both ai_extracted and natural_language tasks
                        if task.get('source') in ['ai_extracted', 'natural_language']:
                            validated_tasks.append(task)
                        
            # Merge natural language tasks with AI-extracted tasks
            if natural_tasks_data:
                validated_tasks.extend(natural_tasks_data)
            
            # CRITICAL FIX: Also preserve natural language tasks from previous cache
            # This handles cases where natural language tasks were skipped due to deduplication
            for task in extracted.get('tasks', []):
                if isinstance(task, dict) and task.get('source') == 'natural_language':
                    # Only add if not already in validated_tasks
                    task_desc = task.get('description', '')
                    if not any(t.get('description') == task_desc for t in validated_tasks):
                        validated_tasks.append(task)
            
            # Update extracted data with only successful tasks
            extracted['tasks'] = validated_tasks
            
            # DIAGNOSTIC: Log final task count for this recording
            if validated_tasks:
                task_sources = [t.get('source', 'unknown') for t in validated_tasks]
                logger.debug(f"Lifelog {log_id[:8]}... final task count: {len(validated_tasks)} "
                           f"(sources: {task_sources})")
                        
            # ✅ ENHANCED: Store people with speaker attribution (preserving Speaker N names)
            for person in extracted.get('people', []):
                if person.get('name') and person.get('context'):
                    # Enhanced memory text with speaker info (preserving Speaker N naming)
                    person_name = person['name']
                    memory_text = f"{person_name}: {person['context']}"
                    if person.get('is_speaker'):
                        # Preserve Speaker N naming in memory text
                        if person_name.startswith('Speaker '):
                            memory_text += f" ({person_name} in conversation)"
                        else:
                            memory_text += " (Speaker in conversation)"
                    
                    # Check if memory already exists for this log_id and person
                    existing_memories = memory_manager.get_all_memories(phone_number)
                    duplicate_found = False
                    
                    for existing_mem in existing_memories:
                        metadata = existing_mem.get('metadata', {})
                        # Check if same log_id and same person
                        if (metadata.get('source') == 'limitless' and 
                            metadata.get('log_id') == log_id and
                            person['name'].lower() in existing_mem.get('content', '').lower()):
                            logger.debug(f"Skipping duplicate person {person['name']} for {log_id[:8]}...")
                            duplicate_found = True
                            break
                    
                    if duplicate_found:
                        logger.debug(f"Skipping duplicate memory for log {log_id[:8]}...")
                        continue
                    
                    memory_id = memory_manager.create_memory(
                        user_id=phone_number,
                        content=memory_text,
                        memory_type='relationship'
                    )
                    
                    # Add Limitless source metadata for dashboard stats
                    if memory_id:
                        memory_key = RedisKeyBuilder.get_user_memory_key(phone_number, memory_id)
                        memory_data = redis_client.get(memory_key)
                        if memory_data:
                            memory_obj = json.loads(memory_data.decode() if isinstance(memory_data, bytes) else memory_data)
                            memory_obj['metadata'] = memory_obj.get('metadata', {})
                            memory_obj['metadata']['source'] = 'limitless'
                            memory_obj['metadata']['log_id'] = log_id
                            memory_obj['metadata']['is_speaker'] = person.get('is_speaker', False)
                            redis_client.set(memory_key, json.dumps(memory_obj))
                            results['memories_created'] += 1
        else:
            # ✅ FALLBACK: Even without transcript, ensure user appears in people
            extracted['people'] = speakers_identified if speakers_identified else [{
                'name': 'You',
                'context': 'Primary user (no transcript)',
                'is_speaker': True,
                'role': 'primary_user'
            }]
                
        # ✅ FINAL VALIDATION: Ensure no "Unknown" speakers slip through
        extracted = validate_speaker_names(extracted, log_id)
        
        # Cache the processed Lifelog with enhanced data
        cache_key = RedisKeyBuilder.build_limitless_lifelog_key(log_id)
        cache_data = {
            'id': log_id,
            'title': title,
            'summary': summary,
            'start_time': start_time,
            'end_time': end_time,
            'created_at': log.get('createdAt') or log.get('created_at'),
            'extracted': extracted,  # Now includes speaker info and fallbacks
            'speaker_mapping': log.get('_speaker_mapping', {}),  # Store Speaker N mapping
            'processed_at': datetime.now().isoformat()
        }
        
        logger.info(f"Caching Lifelog {log_id} with start_time: {start_time} and {len(speakers_identified)} speakers to key: {cache_key}")
        redis_client.setex(
            cache_key,
            86400 * 7,  # Cache for 7 days
            json.dumps(cache_data)
        )
        
    except Exception as e:
        logger.error(f"Error processing Lifelog {log.get('id')}: {str(e)}")
        
    return results


def validate_speaker_names(extracted_data: Dict, log_id: str = "unknown") -> Dict:
    """
    Final validation to ensure no "Unknown" speakers exist in the data.
    This is the last line of defense against any remaining Unknown speakers.
    """
    if not isinstance(extracted_data, dict):
        return extracted_data
    
    people = extracted_data.get('people', [])
    if not people:
        return extracted_data
    
    # Get all existing Speaker N numbers
    existing_speaker_numbers = set()
    for person in people:
        person_name = person.get('name', '')
        if person_name.startswith('Speaker ') and person.get('is_speaker'):
            try:
                num = int(person_name.split(' ')[1])
                existing_speaker_numbers.add(num)
            except (IndexError, ValueError):
                pass
    
    # Find any remaining problematic speakers and fix them
    next_speaker_number = max(existing_speaker_numbers) + 1 if existing_speaker_numbers else 0
    
    for person in people:
        person_name = person.get('name', '')
        
        # Check for any remaining Unknown speakers
        if (person_name.lower() in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker', ''] or
            not person_name or person_name.isspace()):
            
            if person.get('is_speaker'):
                # Replace with proper Speaker N naming
                person['name'] = f'Speaker {next_speaker_number}'
                person['context'] = 'Unrecognized speaker in conversation'
                logger.error(f"🚨 CRITICAL: Found {person_name or 'empty'} speaker in final validation for {log_id[:8]}..., fixed to Speaker {next_speaker_number}")
                next_speaker_number += 1
            else:
                # For non-speakers, we can be more lenient but still log
                logger.warning(f"Found empty/unknown non-speaker for {log_id[:8]}...: {person}")
    
    return extracted_data


def standardize_cached_speakers(extracted_data: Dict) -> Dict:
    """
    Standardize speaker names in cached data to ensure consistency.
    Converts any "Unknown" speakers to proper "Speaker N" naming.
    """
    if not isinstance(extracted_data, dict):
        return extracted_data
    
    people = extracted_data.get('people', [])
    if not people:
        return extracted_data
    
    unknown_speaker_counter = 0
    # Count existing Speaker N names to continue numbering
    for person in people:
        person_name = person.get('name', '')
        if person_name.startswith('Speaker ') and person.get('is_speaker'):
            try:
                speaker_num = int(person_name.split(' ')[1])
                unknown_speaker_counter = max(unknown_speaker_counter, speaker_num + 1)
            except (IndexError, ValueError):
                pass
    
    # Fix any "Unknown" speakers with more comprehensive detection
    for person in people:
        person_name = person.get('name', '')
        if (person_name.lower() in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker', ''] and 
            person.get('is_speaker')):
            new_speaker_name = f"Speaker {unknown_speaker_counter}"
            person['name'] = new_speaker_name
            person['context'] = 'Unrecognized speaker in conversation'
            logger.info(f"Standardized cached '{person_name or 'empty'}' speaker to '{new_speaker_name}'")
            unknown_speaker_counter += 1
        # Also fix any malformed Speaker N names
        elif person_name.startswith('Speaker ') and person.get('is_speaker'):
            try:
                # Validate the Speaker N format
                parts = person_name.split(' ')
                if len(parts) != 2 or not parts[1].isdigit():
                    # Fix malformed Speaker N name
                    new_speaker_name = f"Speaker {unknown_speaker_counter}"
                    person['name'] = new_speaker_name
                    logger.info(f"Fixed malformed Speaker name '{person_name}' to '{new_speaker_name}'")
                    unknown_speaker_counter += 1
            except (IndexError, ValueError):
                # Fix invalid Speaker N name
                new_speaker_name = f"Speaker {unknown_speaker_counter}"
                person['name'] = new_speaker_name
                logger.info(f"Fixed invalid Speaker name '{person_name}' to '{new_speaker_name}'")
                unknown_speaker_counter += 1
    
    return extracted_data


def extract_speakers_from_contents(log: Dict) -> List[Dict[str, str]]:
    """
    Extract speaker information directly from Limitless API contents.
    Uses dynamic "Speaker N" naming for unrecognized speakers.
    Properly handles multiple speakers with same name (e.g., "Unknown").
    
    Returns:
        List of speakers with their roles
    """
    speakers = []
    contents = log.get('contents', [])
    
    speaker_id_mapping = {}  # Map speaker IDs to Speaker N names
    speaker_id_to_info = {}  # Track all info about each speaker ID
    unrecognized_speaker_counter = 0
    user_detected = False
    
    # First pass: collect all unique speaker IDs and their names
    for content in contents:
        speaker_name = content.get('speakerName', '').strip()
        speaker_id = content.get('speakerIdentifier', '').strip()
        
        if not speaker_id:
            continue
            
        # Store speaker info by ID
        if speaker_id not in speaker_id_to_info:
            speaker_id_to_info[speaker_id] = {
                'names': set(),
                'is_user': speaker_id == 'user'
            }
        
        if speaker_name:
            speaker_id_to_info[speaker_id]['names'].add(speaker_name)
    
    # Second pass: create speaker entries based on unique IDs
    for speaker_id, info in speaker_id_to_info.items():
        names = info['names']
        is_user = info['is_user']
        
        if is_user:
            # Handle primary user
            speakers.append({
                'name': 'You',
                'context': 'Primary user (speaker)',
                'role': 'primary_user',
                'speaker_id': speaker_id
            })
            user_detected = True
        elif names:
            # Check if any of the names are problematic
            valid_names = [n for n in names if n and 
                          n.lower() not in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker', '']]
            
            if valid_names:
                # Use the first valid name (sorted for consistency)
                speaker_name = sorted(valid_names)[0]
                speakers.append({
                    'name': speaker_name,
                    'context': 'Identified speaker in conversation',
                    'role': 'participant',
                    'speaker_id': speaker_id
                })
            else:
                # All names are problematic (e.g., "Unknown") - assign Speaker N
                speaker_n_name = f"Speaker {unrecognized_speaker_counter}"
                speaker_id_mapping[speaker_id] = speaker_n_name
                
                speakers.append({
                    'name': speaker_n_name,
                    'context': 'Unrecognized speaker in conversation',
                    'role': 'participant',
                    'speaker_id': speaker_id
                })
                unrecognized_speaker_counter += 1
                logger.info(f"Converted problematic speaker name '{list(names)}' to '{speaker_n_name}' for {log.get('id', 'unknown')[:8]}...")
        else:
            # No name at all - assign Speaker N
            speaker_n_name = f"Speaker {unrecognized_speaker_counter}"
            speaker_id_mapping[speaker_id] = speaker_n_name
            
            speakers.append({
                'name': speaker_n_name,
                'context': 'Unrecognized speaker in conversation',
                'role': 'participant',
                'speaker_id': speaker_id
            })
            unrecognized_speaker_counter += 1
    
    # Handle contents without any speaker ID (edge case)
    has_unattributed_content = any(
        not content.get('speakerIdentifier', '').strip() 
        for content in contents 
        if content.get('content', '').strip()
    )
    
    if has_unattributed_content and not speakers:
        # Add a generic speaker for unattributed content
        speakers.append({
            'name': f"Speaker {unrecognized_speaker_counter}",
            'context': 'Unattributed content in conversation',
            'role': 'participant'
        })
    
    # ✅ ENHANCED FALLBACK: If no speakers detected, assume user is speaking
    if not speakers:
        logger.warning(f"No speakers detected in log {log.get('id')}, assuming primary user")
        speakers.append({
            'name': 'You',
            'context': 'Primary user (assumed speaker)',
            'role': 'primary_user'
        })
    
    # Store speaker mapping for consistent naming throughout transcript
    log['_speaker_mapping'] = speaker_id_mapping
    
    return speakers


def get_enhanced_extraction_prompt(title: str, summary: str, transcript: str) -> str:
    """Enhanced prompt with Speaker N naming support and fallback for when speaker info is missing."""
    
    # Check if transcript has speaker attribution (including any Speaker N naming)
    has_speaker_info = (
        'You:' in transcript or 
        any(f'Speaker {i}:' in transcript for i in range(0, 20)) or
        ':' in transcript  # Fallback for any speaker attribution
    )
    
    if has_speaker_info:
        # Use speaker-aware prompt with Speaker N support
        logger.debug("Using speaker-aware prompt with Speaker N naming for AI extraction")
        prompt = f"""Analyze this conversation transcript and extract:

1. Key facts and decisions (for memory storage)
2. Action items and tasks with deadlines - INCLUDE WHO said each task
3. Important dates or events mentioned
4. People mentioned and their roles/context - INCLUDE speaker identification

IMPORTANT: Pay attention to speaker attribution in the transcript. When extracting tasks:
- If "You:" said something, it's the user's task
- If "Speaker 0:", "Speaker 1:", "Speaker 2:", etc. mentioned tasks, note who assigned them
- Preserve the exact "Speaker N" names (Speaker 0, Speaker 1, Speaker 2, etc.) when referencing unrecognized speakers
- NEVER use "Unknown" or "Unknown Speaker" - always use the specific "Speaker N" format found in the transcript
- Use consistent "Speaker N" numbering throughout all extractions

Title: {title}
Summary: {summary}
Transcript: {transcript[:3000]}

Return a JSON object with:
{{
    "facts": ["fact1", "fact2"],
    "tasks": [{{
        "description": "task description", 
        "due_date": "YYYY-MM-DD or null",
        "assigned_to": "You" or "Speaker 0" or "Speaker 1" or "Speaker 2" or "exact_speaker_name_from_transcript",
        "assigned_by": "exact_speaker_name_from_transcript or Speaker N who mentioned it"
    }}],
    "events": [{{"title": "event", "date": "YYYY-MM-DD", "time": "HH:MM or null"}}],
    "people": [{{
        "name": "exact_name_from_transcript or Speaker 0 or Speaker 1 or Speaker 2 etc", 
        "context": "their role or relationship",
        "is_speaker": true/false
    }}]
}}

Be specific about WHO said what. Preserve exact "Speaker N" naming for unrecognized speakers. NEVER generate "Unknown" speakers. Extract only clearly stated information."""
    else:
        # ✅ FALLBACK: Use original prompt assuming single speaker
        logger.debug("No speaker attribution detected, using single-user prompt")
        prompt = f"""Analyze this recording transcript and extract:

1. Key facts and decisions (for memory storage)
2. Action items and tasks with deadlines
3. Important dates or events mentioned
4. People mentioned and their roles/context

NOTE: This appears to be a single-speaker recording. Assume all tasks are for the primary user.

Title: {title}
Summary: {summary}
Transcript: {transcript[:3000]}

Return a JSON object with:
{{
    "facts": ["fact1", "fact2"],
    "tasks": [{{
        "description": "task description", 
        "due_date": "YYYY-MM-DD or null",
        "assigned_to": "You",
        "assigned_by": "You"
    }}],
    "events": [{{"title": "event", "date": "YYYY-MM-DD", "time": "HH:MM or null"}}],
    "people": [{{
        "name": "person", 
        "context": "their role or relationship",
        "is_speaker": false
    }}]
}}

Extract clear, actionable information from this single-speaker recording."""
    
    return prompt


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


def extract_natural_language_tasks(transcript: str, log_id: str, phone_number: str, title: str = "") -> tuple[int, List[Dict]]:
    """
    Extract natural language tasks and reminders from transcript.
    
    Detects spoken statements like:
    - "remind me to..."
    - "I need to..."  
    - "my wife told me to buy..."
    - "don't forget to..."
    
    Returns tuple of (number of tasks created, list of task data).
    """
    try:
        # Check if we've already processed this transcript for tasks
        task_key = RedisKeyBuilder.build_limitless_task_created_key(log_id)
        if redis_client.exists(task_key):
            logger.debug(f"Tasks already extracted for {log_id[:8]}...")
            # Return cached data if available
            cached_data = redis_client.get(task_key)
            if cached_data:
                try:
                    cache_info = json.loads(cached_data.decode() if isinstance(cached_data, bytes) else cached_data)
                    cached_tasks = cache_info.get('task_data', [])
                    return cache_info.get('tasks_created', 0), cached_tasks
                except:
                    pass
            return 0, []
        
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
            # Handle mixed responses with explanation and JSON
            cleaned_response = response.strip()
            
            # Extract JSON from response if it contains ```json blocks
            if '```json' in cleaned_response:
                json_match = re.search(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(1).strip()
            elif '```' in cleaned_response:
                json_match = re.search(r'```\s*(.*?)\s*```', cleaned_response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(1).strip()
            
            # Try to find JSON object in the response
            if not cleaned_response.startswith('{'):
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(0)
                else:
                    # No JSON found, return 0 tasks (this is normal for recordings without tasks)
                    logger.debug(f"No JSON structure found in task response for log {log_id}, no tasks extracted")
                    return 0, []
                
            task_data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            logger.debug(f"Failed to parse natural language task response for log {log_id}, no tasks extracted")
            return 0, []
        
        tasks_created = 0
        successful_tasks_data = []  # Track task data for successful tasks
        
        if task_data.get("tasks_found", False):
            natural_tasks = task_data.get("natural_tasks", [])
            
            for task in natural_tasks:
                task_text = task.get("task_text", "").strip()
                urgency = task.get("urgency", "medium")
                context = task.get("context", "")
                
                if task_text and len(task_text) > 5:  # Ensure meaningful task
                    # Create the task
                    task_title = f"{task_text}"
                    task_notes = f"From Limitless recording"
                    if title:
                        task_notes += f": {title}"
                    if context:
                        task_notes += f" - {context}"
                    
                    success = create_task_from_limitless({
                        'title': task_title,
                        'notes': task_notes
                    }, phone_number)
                    
                    if success:
                        tasks_created += 1
                        logger.debug(f"Created task: {task_title[:50]}...")
                        
                        # Store task data for unified storage
                        task_data_item = {
                            'description': task_title,
                            'urgency': urgency,
                            'context': context,
                            'source': 'natural_language',
                            'created_successfully': True,
                            'google_task_created': True,
                            'assigned_to': 'You',
                            'assigned_by': 'You'
                        }
                        successful_tasks_data.append(task_data_item)
                        
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
                "log_id": log_id,
                "task_data": successful_tasks_data  # Store task data for unified counting
            })
        )
        
        if tasks_created > 0:
            logger.debug(f"Extracted {tasks_created} tasks from {log_id[:8]}...")
        
        return tasks_created, successful_tasks_data
        
    except Exception as e:
        logger.error(f"Error extracting natural language tasks from log {log_id}: {str(e)}")
        return 0, []


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
                # ✅ CRITICAL FIX: Standardize speaker names in cached data for search
                extracted = standardize_cached_speakers(extracted)
                
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
                # ✅ CRITICAL FIX: Standardize speaker names in cached data for person search
                extracted = standardize_cached_speakers(extracted)
                
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
