"""
Meta Glasses Gemini API
A WhatsApp-based assistant using Google's Gemini API for various functionalities.
"""

__version__ = '1.1.2'

# Standard library imports
import json
import logging
import os
import re as regex_module
import threading
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional

# Third-party imports
from fastapi import FastAPI, Request, HTTPException, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse

# Local imports - functionality
from functionality.audio import retrieve_transcript_from_audio
from functionality.automation import automation_command
from functionality.calendar import create_google_calendar_event
from functionality.image import logic_for_prompt_before_image, retrieve_calories_from_image
from functionality.notion_ import add_new_page
from functionality.task import create_task, get_tasks, update_task_status, delete_task, format_task_for_display
from functionality.nutrition import get_cals_from_image
from functionality.search import google_search_pipeline

# Local imports - utils
from utils.gemini import *
from utils.google_auth import GoogleAuth
from utils.whatsapp import send_whatsapp_threaded, send_whatsapp_image, download_file
from utils.context_manager import ContextManager
from utils.memory_manager import MemoryManager
from utils.metrics import MetricsTracker
from api.dashboard import dashboard_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

app = FastAPI()
ok = {'status': 'Ok'}

class ImageContext:
   last_image_path = None

COMMON_RESPONSES = {
   "thank you": "You're welcome!",
   "thanks": "You're welcome!",
   "bye": "Goodbye!",
   "ok": "Got it! Let me know if you need anything.",
   "okay": "Got it! Let me know if you need anything."
}

app.add_middleware(
   CORSMiddleware,
   allow_origins=[
       "https://www.messenger.com",
       "https://www.facebook.com",
       "http://localhost:3000",  # Dashboard development
       "http://localhost:8111",  # Production dashboard
       "http://rayban.gbhome.my:3000",  # Production dashboard frontend
       "https://rayban.gbhome.my:3000",  # Production dashboard frontend HTTPS
       os.getenv('HOME_ASSISTANT_URL')
   ],
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)

# Include dashboard routes
app.include_router(dashboard_router)

@app.get('/')
def home():
   return f'API {__version__} OK'

@app.get('/auth/google')
async def google_auth_endpoint(x_api_key: Optional[str] = Header(None)):
   return await GoogleAuth.get_instance().get_auth_url(x_api_key)

@app.get("/auth/callback")
async def auth_callback(code: str, state: str = None, x_api_key: Optional[str] = Header(None)):
   return await GoogleAuth.get_instance().handle_callback(code, state, x_api_key)

@app.get('/webhook', response_class=PlainTextResponse)
def webhook_verification(request: Request):
   if request.query_params.get('hub.mode') == 'subscribe' and request.query_params.get(
           'hub.verify_token') == os.getenv('WHATSAPP_WEBHOOK_VERIFICATION_TOKEN'):
       return request.query_params.get('hub.challenge')
   raise HTTPException(status_code=400, detail="Bad Request")

@app.post('/webhook')
def receive_whatsapp_message(request: Request, data: dict):
   message = data['entry'][0]['changes'][0]['value'].get('messages', [{}])[0]
   threading.Thread(target=logic, args=(message,)).start()
   return ok

@app.post('/send-notification')
async def send_notification(request: Request):
   try:
       data = json.loads(await request.body())
       message = data.get('message')
       image_url = data.get('image_url')
       
       if not message:
           raise HTTPException(status_code=400, detail="Missing message")
           
       send_whatsapp_threaded(message)
       logger.info(f"Notification sent: {message}")

       if image_url:
           send_whatsapp_image(image_url)
           logger.info(f"Image sent from URL: {image_url}")

       return {'status': 'sent'}
   except Exception as e:
       logger.error(f"Error: {e}")
       raise HTTPException(status_code=500)

def send_response_with_context(user_id: str, message: str, response: str, msg_type: str = 'other'):
    """Send WhatsApp response and track in conversation history."""
    send_whatsapp_threaded(response)
    ContextManager.add_to_conversation_history(user_id, message, response, msg_type)

def process_text_message(text: str, message_data: dict):
    text_lower = text.lower().strip()
    user_id = message_data.get('from', 'unknown')
    
    # Track message
    MetricsTracker.track_message(user_id, "text")
    
    # Extract user name and preferences if mentioned
    ContextManager.extract_user_name(text, user_id)
    ContextManager.extract_preferences(text, user_id)
    
    # Skip memory extraction for system commands
    if not any(text_lower.startswith(cmd) for cmd in ['remember that', 'remember:', 'show my memories', 'what do you remember', 'forget about', 'forget that', 'cleanup memories', 'delete memory', 'debug memories']):
        # Auto-extract memories from conversation
        potential_memories = MemoryManager.extract_memories_from_text(text, user_id)
        for memory_type, content, source in potential_memories:
            # Only auto-save important memories (not general chat)
            if memory_type in ['allergy', 'relationship', 'important_date', 'personal_info']:
                MemoryManager.create_memory(
                    user_id=user_id,
                    content=content,
                    memory_type=memory_type,
                    extracted_from=source,
                    importance=8
                )
                logger.info(f"Auto-extracted {memory_type} memory: {content}")
    
    # Handle special "do you know me?" type questions
    if any(phrase in text_lower for phrase in ['do you know me', 'who am i', 'what is my name', 'remember me']):
        profile = ContextManager.get_user_profile(user_id)
        history = ContextManager.get_conversation_history(user_id, limit=5)
        
        # Check profile first
        name = None
        if profile and profile.get('name'):
            name = profile['name']
        
        # If no name in profile, check memories for personal information
        if not name:
            all_memories = MemoryManager.get_all_memories(user_id)
            for memory in all_memories:
                content = memory['content']
                content_lower = content.lower()
                
                # Look for explicit name patterns
                if any(pattern in content_lower for pattern in ['my name is', 'i am', 'call me']):
                    for pattern in ['my name is ', 'i am ', 'call me ']:
                        if pattern in content_lower:
                            name_part = content[content_lower.index(pattern) + len(pattern):].strip()
                            name = name_part.split()[0] if name_part else None
                            break
                    if name:
                        break
                
                # Look for names in relationship or personal contexts
                # Check if content mentions a name that could be the user's name
                # Look for patterns like "Hisyam work at", "Hisyam partner", "Hisyam and"
                name_match = regex_module.search(r'\b([A-Z][a-z]+)\s+(?:work|partner|and|lives|is)', content)
                if name_match:
                    potential_name = name_match.group(1)
                    # Verify this isn't someone else's name by checking context
                    if not any(word in content_lower for word in ['his ', 'her ', 'their ', "'s "]):
                        name = potential_name
                        break
        
        if name:
            response = f"Yes! You're {name}. "
            
            # Add relevant memories
            all_memories = MemoryManager.get_all_memories(user_id)
            if all_memories:
                memory_info = []
                for memory in all_memories[:3]:  # Show top 3 memories
                    if memory['type'] in ['personal_info', 'preference', 'relationship']:
                        memory_info.append(f"{memory['content']}")
                
                if memory_info:
                    response += f"I also remember: {'; '.join(memory_info[:2])}. "
            
            # Add context about recent interactions
            if history:
                recent_types = set(h['type'] for h in history if h['type'] != 'other')
                if recent_types:
                    response += f"You often ask me about {', '.join(recent_types)}. "
                
                # Add last interaction info
                last_time = datetime.fromisoformat(history[-1]['timestamp'])
                time_diff = datetime.now() - last_time
                if time_diff < timedelta(hours=1):
                    response += "We were just chatting a moment ago!"
                elif time_diff < timedelta(days=1):
                    response += f"We last talked {int(time_diff.total_seconds() / 3600)} hours ago."
            
            send_whatsapp_threaded(response)
            ContextManager.add_to_conversation_history(user_id, text, response, 'other')
            return ok
        else:
            # Check if we have any memories at all about the user
            all_memories = MemoryManager.get_all_memories(user_id)
            if all_memories:
                # Format memories in a natural way
                memory_sentences = []
                for memory in all_memories[:4]:  # Show top 4 memories
                    content = memory['content']
                    memory_type = memory['type']
                    
                    # Make the content more natural
                    if memory_type == 'relationship':
                        if 'partner' in content.lower():
                            memory_sentences.append(content)
                        elif 'and' in content and 'anniversary' not in content.lower():
                            memory_sentences.append(content)
                    elif memory_type == 'personal_info':
                        if 'work' in content.lower():
                            memory_sentences.append(content)
                    elif memory_type == 'important_date':
                        if 'anniversary' in content.lower():
                            memory_sentences.append(content)
                    elif memory_type in ['preference', 'fact', 'note']:
                        memory_sentences.append(content)
                
                if memory_sentences:
                    # Try to extract the name from the first memory
                    first_memory = memory_sentences[0]
                    name_match = regex_module.search(r'\b([A-Z][a-z]+)', first_memory)
                    if name_match:
                        extracted_name = name_match.group(1)
                        response = f"Based on what I remember, you're {extracted_name}! I know that {'. I also remember that '.join(memory_sentences[:3])}."
                    else:
                        response = f"I remember several things about you: {'. '.join(memory_sentences[:3])}. Could you tell me your name?"
                else:
                    response = "I have some memories about you, but I'm not sure of your name. Could you tell me by saying 'I am [your name]'?"
            else:
                response = "I don't know your name yet. You can tell me by saying 'I am [your name]' or 'My name is [your name]'."
            
            send_whatsapp_threaded(response)
            ContextManager.add_to_conversation_history(user_id, text, response, 'other')
            return ok
    
    # Handle conversation summary requests
    if any(phrase in text_lower for phrase in ['what did we talk about', 'what have we discussed', 'conversation history', 'what were we talking']):
        summary = ContextManager.get_conversation_summary(user_id)
        send_response_with_context(user_id, text, summary, 'other')
        return ok
    
    # Handle "what do I usually ask" queries
    if any(phrase in text_lower for phrase in ['what do i usually', 'what do i often', 'my patterns', 'frequently ask']):
        profile = ContextManager.get_user_profile(user_id)
        if profile:
            freq_commands = profile.get('stats', {}).get('frequent_commands', {})
            if freq_commands:
                # Sort by frequency
                sorted_commands = sorted(freq_commands.items(), key=lambda x: x[1], reverse=True)
                top_commands = [f"{cmd} ({count} times)" for cmd, count in sorted_commands[:3]]
                response = f"You frequently ask about: {', '.join(top_commands)}"
            else:
                response = "I haven't tracked enough patterns yet. Keep chatting with me!"
        else:
            response = "I don't have enough conversation history yet."
        send_response_with_context(user_id, text, response, 'other')
        return ok
    
    # Handle "what do you know about me" queries
    if any(phrase in text_lower for phrase in ['what do you know about me', 'tell me about myself', 'my profile', 'my information']):
        profile = ContextManager.get_user_profile(user_id)
        if profile:
            info_parts = []
            
            # Name
            if profile.get('name'):
                info_parts.append(f"Your name is {profile['name']}")
            
            # Job
            if profile.get('context', {}).get('job'):
                job = profile['context']['job']
                info_parts.append(f"You work as {job}")
            
            # Interests
            interests = profile.get('context', {}).get('interests', [])
            if interests:
                # Deduplicate interests by case-insensitive comparison, keeping the best formatted version
                unique_interests = {}
                for interest in interests:
                    key = interest.lower()
                    # Keep the version with more uppercase letters (likely better formatted)
                    if key not in unique_interests or sum(1 for c in interest if c.isupper()) > sum(1 for c in unique_interests[key] if c.isupper()):
                        unique_interests[key] = interest
                
                cleaned_interests = list(unique_interests.values())
                info_parts.append(f"You're interested in {', '.join(cleaned_interests)}")
            
            # Preferences
            prefs = profile.get('preferences', {})
            if prefs.get('preferred_time'):
                info_parts.append(f"You prefer {prefs['preferred_time']} meetings")
            if prefs.get('default_meeting_duration'):
                info_parts.append(f"Your meetings are usually {prefs['default_meeting_duration']} minutes")
            
            response = ". ".join(info_parts) if info_parts else "I'm still learning about you. Tell me more!"
        else:
            response = "I don't know much about you yet. Tell me about yourself!"
        send_response_with_context(user_id, text, response, 'other')
        return ok
    
    # Use AI to detect if this is a personal query (more flexible than hardcoded indicators)
    try:
        personal_detection_prompt = f"""
        Is this query asking about personal information, people, relationships, or memories?
        
        Query: "{text}"
        
        Personal queries include:
        - Questions about specific people ("Who is X?", "Do you know Y?", "Tell me about Z")
        - Questions about personal relationships ("my wife", "my partner", "my family")
        - Questions about personal facts ("when is my birthday", "where was I born", "what do I like")
        - Questions about dates/events ("my anniversary", "when is X's birthday")
        - Questions asking for personal information recall
        
        Non-personal queries include:
        - General greetings ("hi", "hello")
        - Task requests ("schedule meeting", "set reminder")
        - General information questions ("what's the weather", "latest news")
        - System commands
        
        Answer: yes/no
        """
        
        personal_detection = simple_prompt_request(personal_detection_prompt, user_id)
        is_likely_personal_query = personal_detection.lower().strip().startswith('yes')
        logger.info(f"AI personal query detection for '{text}': {personal_detection.strip()} -> {is_likely_personal_query}")
        
    except Exception as e:
        logger.error(f"Error in AI personal query detection: {e}")
        # Fallback to a simple check for very common patterns
        basic_patterns = ['who', 'what', 'when', 'where', 'my ', 'do you know']
        is_likely_personal_query = any(pattern in text.lower() for pattern in basic_patterns)
    
    if not is_likely_personal_query:
        context_ref = ContextManager.understand_context_reference(text, user_id)
        if context_ref:
            if context_ref.startswith('repeat_'):
                command_type = context_ref.replace('repeat_', '')
                response = f"You usually ask about {command_type}. Would you like me to {command_type} now?"
                send_response_with_context(user_id, text, response, 'other')
                return ok
            elif context_ref == 'modify_previous_meeting':
                response = "I understand you want to modify the previous meeting. Please specify the new details."
                send_response_with_context(user_id, text, response, 'other')
                return ok
    

    # Handle explicit memory commands
    if text_lower.startswith('remember that') or text_lower.startswith('remember:'):
        # Extract what to remember
        memory_content = text[13:].strip() if text_lower.startswith('remember that') else text[9:].strip()
        if memory_content:
            memory_id = MemoryManager.create_memory(
                user_id=user_id,
                content=memory_content,
                memory_type='note',
                importance=7
            )
            response = f"I'll remember that for you. You can ask me about it anytime!"
            send_response_with_context(user_id, text, response, 'other')
        else:
            response = "What would you like me to remember?"
            send_response_with_context(user_id, text, response, 'other')
        return ok
    
    # Handle memory queries
    if any(phrase in text_lower for phrase in ['what do you remember about', 'what have you remembered', 'show my memories']):
        # Extract search query
        search_query = ""
        if 'about' in text_lower:
            search_query = text_lower.split('about')[-1].strip()
        
        if search_query:
            memories = MemoryManager.search_memories(user_id, search_query, limit=5)
        else:
            memories = MemoryManager.get_all_memories(user_id)[:10]
        
        if memories:
            logger.info(f"Formatting {len(memories)} memories for display")
            # Use AI to format memories naturally
            try:
                memory_context = "\n".join([f"- {m['content']}" for m in memories])
                logger.debug(f"Memory context: {memory_context}")
                format_prompt = f"""
                Convert these personal memories into a natural, warm response:
                
                {memory_context}
                
                Guidelines:
                - Write as if you're a close friend who remembers important details about them
                - Group related information naturally
                - Use conversational, personal tone
                - Avoid technical formatting or categories
                - Be concise but comprehensive
                """
                
                response = simple_prompt_request(format_prompt, user_id)
                
            except Exception as e:
                logger.error(f"Error formatting memories: {e}")
                # Fallback to simple format without types
                memory_list = [f"• {memory['content']}" for memory in memories]
                response = "Here's what I remember:\n" + "\n".join(memory_list)
        else:
            response = "I don't have any memories about that yet."
        
        send_response_with_context(user_id, text, response, 'other')
        return ok
    
    # Handle forget commands
    if text_lower.startswith('forget about') or text_lower.startswith('forget that'):
        search_term = text_lower.replace('forget about', '').replace('forget that', '').strip()
        if search_term:
            memories = MemoryManager.search_memories(user_id, search_term, limit=1)
            if memories:
                MemoryManager.delete_memory(user_id, memories[0]['id'])
                response = f"I've forgotten about: {memories[0]['content']}"
            else:
                response = "I couldn't find that in my memories."
        else:
            response = "What would you like me to forget?"
        send_response_with_context(user_id, text, response, 'other')
        return ok
    
    # Handle cleanup command
    if text_lower == 'cleanup memories':
        cleaned_count = MemoryManager.cleanup_question_memories(user_id)
        response = f"Cleaned up {cleaned_count} incorrect memories."
        send_response_with_context(user_id, text, response, 'other')
        return ok
    
    # Handle specific memory deletion
    if text_lower.startswith('delete memory '):
        memory_id = text_lower.replace('delete memory ', '').strip()
        if MemoryManager.delete_memory(user_id, memory_id):
            response = f"Deleted memory {memory_id}."
        else:
            response = f"Could not find memory {memory_id}."
        send_response_with_context(user_id, text, response, 'other')
        return ok
    
    # Handle debug command to see raw memories
    if text_lower == 'debug memories':
        memories = MemoryManager.get_all_memories(user_id)
        memory_list = []
        for i, memory in enumerate(memories[:10], 1):
            memory_list.append(f"{i}. [{memory['type']}] {memory['content']} (ID: {memory['id']})")
        response = "Raw memories:\n" + "\n".join(memory_list) if memory_list else "No memories found."
        send_response_with_context(user_id, text, response, 'other')
        return ok
    
    if text_lower in COMMON_RESPONSES:
        response = COMMON_RESPONSES[text_lower]
        send_whatsapp_threaded(response)
        ContextManager.add_to_conversation_history(user_id, text, response, 'other')
        return ok

    if text_lower == 'cals':
        return retrieve_calories_from_image()

    isfoodlog = ' '.join(text_lower.split()[-2:])
    if isfoodlog in ['food log', 'foodlog', 'food log.', 'my diet', 'my diet.']:
        return get_cals_from_image()

    try:
        operation_result = retrieve_message_type_from_message(text.lower(), message_data.get('from'))
        logger.info(f"Detected operation type: {operation_result}")

        # Track command frequency
        ContextManager.track_command_frequency(user_id, operation_result)

        # Normal operation type handling
        operation_type = operation_result if isinstance(operation_result, str) else 'other'
        if operation_type == 'image' and ImageContext.last_image_path:
            analysis = analyze_image(ImageContext.last_image_path, text)
            send_whatsapp_threaded(analysis)
            return ok
        elif operation_type == 'task':
            # Process task operations
            task_input = determine_task_inputs(text.lower())
            
            if task_input['intent'] == 'check_tasks':
                tasks = get_tasks(include_completed=task_input['include_completed'])
                if not tasks:
                    send_whatsapp_threaded("You don't have any tasks.")
                else:
                    # Reverse tasks to maintain creation order
                    formatted_tasks = [format_task_for_display(task, i+1) for i, task in enumerate(reversed(tasks))]
                    send_whatsapp_threaded("Here are your tasks:\n" + "\n".join(formatted_tasks))
            
            elif task_input['intent'] == 'create_task':
                title = task_input.get('title', '').strip()
                # Check for empty title or just "add task"
                if not title or title.lower() == 'add task':
                    send_whatsapp_threaded("Please add what to do. For example: add task buy groceries.")
                    return ok
                
                # Create task with validated title
                task = create_task(
                    title=title,
                    notes=task_input.get('notes', ''),
                    due_date=task_input.get('due_date')
                )
                if task:
                    tasks = get_tasks()  # Get all tasks to determine the new task's index
                    # New task will be the last in the list
                    send_whatsapp_threaded(f"Created task: {format_task_for_display(task, len(tasks))}")
                else:
                    send_whatsapp_threaded("Sorry, I couldn't create the task. Please try again.")
            
            elif task_input['intent'] == 'update_task':
                tasks = get_tasks(include_completed=False)  # Get incomplete tasks
                task_index = int(task_input['task_id'])  # This is actually the index number
                tasks = list(reversed(tasks))  # Reverse to match display order
                logger.info(f"Attempting to complete task {task_index} out of {len(tasks)} tasks")
                if 1 <= task_index <= len(tasks):
                    task = tasks[task_index - 1]  # Convert to 0-based index
                    task_id = task.get('id')
                    logger.info(f"Updating task {task_index} (ID: {task_id}): {task.get('title', '')}")
                    if update_task_status(task['id'], task_input['completed']):
                        send_whatsapp_threaded(f"Task {task_index} ({task.get('title', '')}) completed.")
                    else:
                        send_whatsapp_threaded("Sorry, I couldn't update the task. Please try again.")
                else:
                    send_whatsapp_threaded(f"Task {task_index} not found. Please check the task number and try again.")
            
            elif task_input['intent'] == 'delete_task':
                tasks = get_tasks(include_completed=False)  # Get incomplete tasks
                task_index = int(task_input['task_id'])  # This is actually the index number
                tasks = list(reversed(tasks))  # Reverse to match display order
                logger.info(f"Attempting to delete task {task_index} out of {len(tasks)} tasks")
                if 1 <= task_index <= len(tasks):
                    task = tasks[task_index - 1]  # Convert to 0-based index
                    task_id = task.get('id')
                    logger.info(f"Deleting task {task_index} (ID: {task_id}): {task.get('title', '')}")
                    if delete_task(task['id']):
                        send_whatsapp_threaded(f"Task {task_index} ({task.get('title', '')}) deleted.")
                    else:
                        send_whatsapp_threaded("Sorry, I couldn't delete the task. Please try again.")
                else:
                    send_whatsapp_threaded(f"Task {task_index} not found. Please check the task number and try again.")
            
            else:
                send_whatsapp_threaded("I couldn't understand what you want to do with the task. Please try again.")
            return ok
            
        elif operation_type == 'calendar':
            # Get user's WhatsApp ID from the message data
            phone_number = message_data.get('from') if isinstance(message_data, dict) else 'default'
            calendar_input = determine_calendar_event_inputs(text, phone_number)

            # Handle calendar operations including cancellation
            if calendar_input and calendar_input.get('intent') == 'cancel_event':
                send_whatsapp_threaded(calendar_input['response'])
                return ok

            if calendar_input is None:
                # If calendar processing returns None, fall through to default processing
                response = simple_prompt_request(text + '. Respond like a friendly AI assistant in 10 to 15 words.')
                send_whatsapp_threaded(response)
            elif calendar_input.get('response'):
                # Handle helpful messages for basic commands
                send_whatsapp_threaded(calendar_input['response'])
            elif calendar_input['intent'] in ['check_schedule', 'cancel_event']:
                send_whatsapp_threaded(calendar_input['response'])
            else:  # intent == 'create_event'
                # Use title as both title and description to ensure keywords are checked in both
                title = calendar_input['title']
                create_args = {
                    'title': title,
                    'description': title,  # Use title as description to ensure color keywords are checked
                    'date': calendar_input['date'],
                    'time': calendar_input['time'],
                    'duration': calendar_input.get('duration', 1),  # Default to 1 hour if not specified
                    'user_id': phone_number  # Pass user ID for context-aware duplicate detection
                }
                _, response_message = create_google_calendar_event(**create_args)
                send_whatsapp_threaded(response_message)
            return ok
        elif operation_type == 'notion':
            arguments = determine_notion_page_inputs(text)
            add_new_page(**arguments)
            send_whatsapp_threaded('Notion page created successfully!')
            return ok
        elif operation_type == 'search':
            # For search operation type, proceed directly with web search
            response = google_search_pipeline(text)
            send_whatsapp_threaded(response)
            return ok
        elif operation_type == 'automation':
            response = automation_command(text)
            send_whatsapp_threaded(response)
            return ok
        else:
            # Use AI-first approach for memory retrieval in 'other' operation type
            try:
                logger.info(f"Processing 'other' query with AI intent extraction: {text}")
                
                # Use Gemini to extract intent and subject from the query
                intent_extraction_prompt = f"""
                Analyze this query and extract the intent and subject:
                Query: "{text}"
                
                Respond in JSON format:
                {{
                    "is_personal_query": true/false,
                    "subject": "person_name" or "self" or "unknown",
                    "intent": "specific_intent_category",
                    "keywords": ["relevant", "search", "terms"]
                }}
                
                Important: For queries with "my" (my partner, my wife, my kids, my job), set subject as "self"
                
                Intent categories:
                - "preferences" (likes, dislikes, hobbies, interests)
                - "work" (job, workplace, occupation)
                - "personal_info" (name, contact, address)
                - "relationships" (family, friends, partner)
                - "birthplace" (where born, origin)
                - "dates" (birthday, anniversary)
                - "food" (favorite food, diet, allergies)
                - "other" (general information)
                
                Examples:
                - "What does Hisyam like?" → {{"is_personal_query": true, "subject": "Hisyam", "intent": "preferences", "keywords": ["like", "enjoy", "hobbies"]}}
                - "Where do I work?" → {{"is_personal_query": true, "subject": "self", "intent": "work", "keywords": ["work", "job", "workplace"]}}
                - "When is my anniversary?" → {{"is_personal_query": true, "subject": "self", "intent": "dates", "keywords": ["anniversary", "date"]}}
                - "Tell me about my wife" → {{"is_personal_query": true, "subject": "self", "intent": "relationships", "keywords": ["wife", "partner"]}}
                - "What do you know about my partner?" → {{"is_personal_query": true, "subject": "self", "intent": "relationships", "keywords": ["partner", "know"]}}
                - "Who is Fafa?" → {{"is_personal_query": true, "subject": "Fafa", "intent": "personal_info", "keywords": ["who", "Fafa"]}}
                """
                
                intent_response = simple_prompt_request(intent_extraction_prompt, user_id)
                logger.info(f"AI intent extraction response: {intent_response}")
                
                # Parse the JSON response
                try:
                    # Clean up the response - remove markdown code blocks if present
                    cleaned_response = intent_response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
                    elif cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response.replace('```', '').strip()
                    
                    intent_data = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    logger.error(f"Failed to parse intent JSON: {intent_response}")
                    intent_data = {"is_personal_query": False}
                
                if intent_data.get("is_personal_query", False):
                    subject = intent_data.get("subject", "unknown")
                    intent = intent_data.get("intent", "other")
                    keywords = intent_data.get("keywords", [])
                    
                    logger.info(f"Detected personal query - Subject: {subject}, Intent: {intent}, Keywords: {keywords}")
                    
                    # Search memories based on subject
                    memories = []
                    if subject == "self":
                        # Get all user's memories
                        memories = MemoryManager.get_all_memories(user_id)
                        logger.info(f"Found {len(memories)} memories for self")
                        
                        # For self queries about relationships, also search for partner info
                        if intent == "relationships" and any(word in text.lower() for word in ['wife', 'partner', 'husband']):
                            # Find partner name from memories
                            for memory in memories:
                                if 'partner' in memory['content'].lower():
                                    # Extract partner name
                                    content = memory['content']
                                    if 'partner is' in content.lower():
                                        partner_name = content.split('partner is')[1].strip().split()[0]
                                        logger.info(f"Found partner name: {partner_name}")
                                        # Search for memories about the partner
                                        partner_memories = MemoryManager.search_memories(user_id, partner_name, limit=5)
                                        memories.extend(partner_memories)
                                        logger.info(f"Added {len(partner_memories)} partner memories")
                                        break
                                        
                    elif subject != "unknown":
                        # Search for memories about the specific person
                        memories = MemoryManager.search_memories(user_id, subject, limit=10)
                        logger.info(f"Found {len(memories)} memories for {subject}")
                    
                    if memories:
                        # Filter and rank memories by intent and keywords
                        relevant_memories = []
                        
                        for memory in memories:
                            content_lower = memory['content'].lower()
                            memory_type = memory.get('type', 'other')
                            relevance_score = 0
                            
                            # Score by memory type matching intent
                            type_intent_mapping = {
                                'preferences': ['preference', 'fact'],
                                'work': ['personal_info'],
                                'personal_info': ['personal_info'],
                                'relationships': ['relationship'],
                                'birthplace': ['personal_info', 'fact'],
                                'dates': ['important_date'],
                                'food': ['preference', 'allergy'],
                                'other': ['note', 'fact']
                            }
                            
                            if memory_type in type_intent_mapping.get(intent, []):
                                relevance_score += 5
                            
                            # Score by keyword matching
                            for keyword in keywords:
                                if keyword.lower() in content_lower:
                                    relevance_score += 3
                            
                            # Additional intent-specific scoring
                            intent_keywords = {
                                'preferences': ['like', 'enjoy', 'love', 'hate', 'prefer', 'favorite', 'watch', 'hobby'],
                                'work': ['work', 'job', 'company', 'office', 'employ', 'career'],
                                'birthplace': ['born', 'birth', 'origin', 'from'],
                                'food': ['eat', 'food', 'dish', 'meal', 'cook', 'restaurant'],
                                'relationships': ['partner', 'wife', 'husband', 'family', 'friend', 'anniversary'],
                                'dates': ['anniversary', 'birthday', 'date', 'born']
                            }
                            
                            for intent_keyword in intent_keywords.get(intent, []):
                                if intent_keyword in content_lower:
                                    relevance_score += 2
                            
                            if relevance_score > 0:
                                relevant_memories.append((relevance_score, memory))
                        
                        # Sort by relevance score
                        relevant_memories.sort(key=lambda x: x[0], reverse=True)
                        top_memories = [memory for score, memory in relevant_memories[:3]]
                        
                        logger.info(f"Found {len(top_memories)} relevant memories for intent '{intent}': {[m['content'] for m in top_memories]}")
                        
                        if top_memories:
                            # Generate natural response using AI
                            memory_context = "; ".join([m['content'] for m in top_memories])
                            
                            natural_response_prompt = f"""
                            Question: "{text}"
                            Relevant memories: {memory_context}
                            Subject: {subject}
                            Intent: {intent}
                            
                            Generate a natural, conversational response to their question using the memory information.
                            Guidelines:
                            - If subject is "self", use "you" when referring to the person
                            - If subject is a name, use that name naturally
                            - Be concise and directly answer their question
                            - Use a friendly, personal tone
                            - Don't mention "memories" or "I remember" - just state the facts naturally
                            """
                            
                            response = simple_prompt_request(natural_response_prompt, user_id)
                            send_response_with_context(user_id, text, response, 'other')
                            return ok
                        else:
                            logger.info(f"No relevant memories found for subject '{subject}' and intent '{intent}'")
                
            except Exception as e:
                logger.error(f"Error in AI-powered memory retrieval: {e}")
            
            # Fallback to regular response generation
            # For very short messages like "Hi", use minimal context (name only) to avoid over-mentioning family
            if len(text.split()) <= 2 and len(text) <= 10:
                response = simple_prompt_request(text + '. Respond like a friendly AI assistant in 10 to 15 words.', user_id, minimal_context=True)
            else:
                # For other messages, use full context
                response = simple_prompt_request(text + '. Respond like a friendly AI assistant in 10 to 15 words.', user_id)
            send_response_with_context(user_id, text, response, 'other')
            return ok

    except AssertionError:
        try:
            # For very short messages like "Hi", use minimal context (name only) to avoid over-mentioning family
            if len(text.split()) <= 2 and len(text) <= 10:
                response = simple_prompt_request(text + '. Respond like a friendly AI assistant in 10 to 15 words.', user_id, minimal_context=True)
            else:
                response = simple_prompt_request(text + '. Respond like a friendly AI assistant in 10 to 15 words.', user_id)
            send_response_with_context(user_id, text, response, 'other')
            return ok
        except:
            error_messages = {
                'image': ["image", "picture", "photo", "see"],
                'calendar': ["schedule", "event", "remind", "calendar"],
                'notion': ["note", "save", "store", "write"],
                'search': ["find", "search", "look up", "what is"],
                'automation': ["turn", "check", "status", "device"]
            }
            
            for type_, keywords in error_messages.items():
                if any(word in text_lower for word in keywords):
                    send_whatsapp_threaded(f"For {type_} requests, try including words like: {', '.join(keywords)}")
                    return ok
            
            send_whatsapp_threaded("I'm not sure what you want. Could you rephrase your question?")
            return ok

def logic(message: dict):
    start_time = time.time()
    logger.info(f"Starting message processing at {start_time}")

    try:
        if not message:
            logger.info("Empty message received")
            return ok

        if message['type'] == 'image':
            logger.info("Processing image message")
            user_id = message.get('from', 'unknown')
            MetricsTracker.track_message(user_id, "image")
            logic_for_prompt_before_image(message)
            image_path = download_file(message['image'])
            if image_path:
                try:
                    ImageContext.last_image_path = image_path
                    analysis = analyze_image(image_path)
                    send_whatsapp_threaded(analysis)
                except Exception as e:
                    logger.error(f"Image analysis error: {e}")
                    send_whatsapp_threaded("Sorry, I couldn't analyze that image.")
            return ok
        elif message['type'] == 'audio':
            logger.info("Processing audio message")
            user_id = message.get('from', 'unknown')
            MetricsTracker.track_message(user_id, "audio")
            result = retrieve_transcript_from_audio(message)
        else:
            text = message['text']['body']
            logger.info(f"Processing text message: {text}")
            # Pass the full message object for proper user identification
            result = process_text_message(text, {
                'from': message.get('from'),
                'wa_id': message.get('from'),  # WhatsApp ID is the same as 'from' in this case
                'type': message.get('type'),
                'text': message.get('text')
            })

        processing_time = time.time() - start_time
        logger.info(f"Message processing completed in {processing_time:.2f} seconds")
        return result

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing message after {processing_time:.2f} seconds: {str(e)}")
        raise

async def check_reminders_task():
    """Background task to check and send meeting reminders."""
    from utils.reminder import ReminderManager
    sync_interval = 300  # Sync calendar every 5 minutes
    last_sync = time.time()  # Initialize with current time after first sync
    
    # Disable oauth2client cache warning
    import warnings
    warnings.filterwarnings('ignore', message='file_cache is unavailable when using oauth2client >= 4.0.0')
    
    try:
        # Initial sync on startup
        logger.info("Starting calendar sync...")
        ReminderManager.sync_with_calendar()
    except Exception as e:
        logger.error(f"Error during initial calendar sync: {str(e)}")
    
    while True:
        current_time = time.time()
        
        # Attempt calendar sync every 5 minutes
        if current_time - last_sync >= sync_interval:
            try:
                logger.info("Starting periodic calendar sync...")
                if ReminderManager.sync_with_calendar():
                    last_sync = current_time
                    logger.info("Periodic calendar sync completed successfully")
                else:
                    logger.warning("Periodic calendar sync completed with errors")
                    # Don't update last_sync on failure to retry next iteration
            except Exception as e:
                logger.error(f"Error during periodic calendar sync: {str(e)}")
        
        try:
            ReminderManager.check_and_send_pending_reminders()
        except Exception as e:
            logger.error(f"Error checking reminders: {str(e)}")
        await asyncio.sleep(60)  # Check every minute

@app.on_event("startup")
async def startup_event():
    """Start background tasks when the application starts."""
    try:
        # Disable oauth2client cache warning
        import warnings
        warnings.filterwarnings('ignore', message='file_cache is unavailable when using oauth2client >= 4.0.0')
        
        # Initialize APIs and services
        from utils.gemini import initialize_gemini_api
        initialize_gemini_api()
        
        # Verify Google Tasks API access
        from functionality.task import get_task_lists
        try:
            task_lists = get_task_lists()
            logger.info(f"Google Tasks API initialized successfully. Found {len(task_lists)} task list(s).")
        except Exception as e:
            logger.error(f"Failed to initialize Google Tasks API: {e}")
        
        # Start background task
        asyncio.create_task(check_reminders_task())
        logger.info("Started reminder checker background task.")
        
        # Ensure all initializations are complete before marking startup as complete
        await asyncio.sleep(0)  # Allow other async tasks to complete
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
