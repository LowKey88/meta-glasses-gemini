import os
import re
import logging
import google.ai.generativelanguage as glm
import google.generativeai as genai
import requests
from PIL import Image
from pydub import AudioSegment
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger("uvicorn")

def initialize_gemini_api():
    """Initialize the Gemini API configuration."""
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {e}")
        raise

# Model constants
GEMINI_VISION_MODEL = 'gemini-2.0-flash-exp'
GEMINI_CHAT_MODEL = 'gemini-1.5-flash'

retrieve_message_type_from_message_description = '''
Based on the message type, execute some different requests to APIs or other tools.

- calendar: types are related to:
  * Checking schedule/meetings/appointments (e.g. "check my meeting", "check my meetings", "what's my schedule", "do I have any meetings")
  * Creating events/meetings/reminders
  * Anything with scheduling, calendar events, or time management

- task: types are related to:
  * Creating, checking, or managing tasks/to-dos
  * Task lists and task completion
  * Due dates and deadlines
  * Task priorities and status
  * Examples: "add task", "create todo", "check my tasks", "mark task complete"

- image: types are related to:
  * Images, pictures, what's the user looking at
  * What's in front of the user
  * Counting objects in images
  * Questions about visual elements or quantities in images (how many, count, number of)
  * All follow-up questions about previously shown images

- notion: anything related to storing a note, save an idea, notion, etc.
- search: types are related to anything with searching, finding, looking for, and it's about a recent event, or news etc.
- automation: types are related to querying states, checking status, or sending commands to home automation devices like gates, lights, doors, alarm, etc.
- other: types are related to anything else.

Make sure to always return the message type, or default to `other` even if it doesn't match any of the types.
'''.replace('    ', '')

determine_calendar_event_inputs_description = f'''
First determine if the user wants to:
1. Check their schedule/meetings/appointments
2. Create a new event/meeting/appointment

For checking schedule (examples: "check my meeting", "what meetings do I have", "show my schedule"):
- intent: Must be "check_schedule"
- date_type: One of ["today", "tomorrow", "this_week", "next_week"]
- target_date: The date to check in YYYY-MM-DD format. Today is time_now.

For creating events (examples: "add meeting", "schedule appointment", "create event"):
- intent: Must be "create_event"
- title: The title of the event
- description: The description of the event, if any, if not return an empty string
- date: The date in YYYY-MM-DD format. Today is time_now.
- time: The time in HH:MM format
- duration: The duration in hours
- type: One of ["reminder", "event", "time-block"]

Make sure to return all required fields based on the intent.
'''.replace('    ', '')

determine_task_inputs_description = f'''
First determine if the user wants to:
1. Check their tasks/to-dos
2. Create a new task
3. Update task status (complete/incomplete)
4. Delete a task

For checking tasks (examples: "show my tasks", "what tasks do I have", "list todos"):
- intent: Must be "check_tasks"
- include_completed: boolean, whether to include completed tasks
- days_ahead: number of days to look ahead for upcoming tasks (default 7)

For creating tasks (examples: "add task", "create todo", "new task"):
- intent: Must be "create_task"
- title: The title/description of the task
- notes: Additional notes about the task, if any (optional)
- due_date: The due date in YYYY-MM-DD format, if specified (optional)

For updating task status (examples: "mark task complete", "finish task", "complete todo"):
- intent: Must be "update_task"
- task_id: The ID of the task to update (will be provided in task list)
- completed: boolean, whether to mark as completed or not

For deleting tasks (examples: "delete task", "remove todo"):
- intent: Must be "delete_task"
- task_id: The ID of the task to delete (will be provided in task list)

Make sure to return all required fields based on the intent.
'''.replace('    ', '')

determine_notion_page_inputs_description = f'''Based on the message, create a new page in your Notion database.
- title: The title of the page
- category: The category of the page, default to `Note`
- content: The content of the message in the user words (without more detail, just in user words)

Make sure to return all the required inputs for the page creation.
'''.replace('    ', '')

def simple_prompt_request(message: str) -> str:
    """
    Send a simple prompt request to Gemini API with current time context.
    
    Args:
        message (str): The prompt message to send
        
    Returns:
        str: Generated response text or error message
        
    Raises:
        ValueError: If message is empty
    """
    try:
        if not message:
            raise ValueError("Message cannot be empty")
            
        model = genai.GenerativeModel(GEMINI_CHAT_MODEL)  # Use chat model for text
        actual_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Add time context to message
        contextualized_message = f'''The current time is {actual_time}. {message}'''
        logger.debug(f"Sending prompt: {contextualized_message}")
        
        response = model.generate_content(
            contextualized_message,
            generation_config={
                'temperature': 0.2,
                'max_output_tokens': 150,
                'candidate_count': 1
            }
        )
        
        if not response.text:
            raise ValueError("Empty response from Gemini API")
            
        result = response.text.strip()
        logger.debug(f"Received response: {result}")
        return result
        
    except ValueError as e:
        logger.error(f"Invalid input error: {e}")
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Error in prompt request: {e}")
        return f"Failed to process request: {e}"

def generate_google_search_query(user_input: str) -> str:
    """
    Generate an optimized search query from user input.
    
    Args:
        user_input (str): The user's search request
        
    Returns:
        str: Optimized search query terms
    """
    return simple_prompt_request(
        f'''Create a simple search query for: "{user_input}".
        Return only the search terms, no formatting or explanation.'''
    )

def retrieve_scraped_data_short_answer(news_content: str, user_query: str) -> str:
    """
    Generate a concise answer from scraped content based on user query.
    
    Args:
        news_content (str): The scraped content to analyze
        user_query (str): The user's question about the content
        
    Returns:
        str: Concise answer (10-15 words) based on the content
    """
    if not news_content or not user_query:
        raise ValueError("Both news content and user query are required")
        
    prompt = f"""
    You are a helpful assistant. Analyze the provided content and answer the user's query
    in a concise way (10-15 words).
    
    Context: {news_content}
    User Query: {user_query}
    
    Return only the answer, no additional explanation.
    """
    
    return simple_prompt_request(prompt)

def _get_func_arg_parameter(description: str, param_type: str = 'string', enum_options: list = None):
    if enum_options:
        return glm.Schema(
            type=glm.Type.STRING,
            enum=enum_options,
            description=description
        )
    return glm.Schema(
        type=glm.Type.STRING if param_type == 'string' else glm.Type.NUMBER,
        description=description
    )

def _get_tool(tool_name: str, description: str, parameters: dict, required: list = None):
    if not required:
        required = list(parameters.keys())
    return glm.Tool(
        function_declarations=[
            glm.FunctionDeclaration(
                name=tool_name,
                description=description,
                parameters=glm.Schema(
                    type=glm.Type.OBJECT,
                    properties=parameters,
                    required=required
                )
            )
        ])

def analyze_image(img_url: str, question: str = None) -> str:
    """
    Analyze an image using Gemini Vision API.
    
    Args:
        img_url (str): URL or path to the image
        question (str, optional): Specific question about the image
        
    Returns:
        str: Analysis result or error message
        
    Raises:
        FileNotFoundError: If image file doesn't exist
        PIL.UnidentifiedImageError: If image format is invalid
    """
    try:
        # Normalize image path
        if img_url.startswith('media/'):
            image_path = img_url
        else:
            image_path = 'media/' + img_url.split('/')[-1]
        logger.info(f"Processing image: {image_path}")

        # Validate file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Load and validate image
        try:
            img = Image.open(image_path)
            img.verify()  # Verify image integrity
            img = Image.open(image_path)  # Reopen after verify
        except Exception as e:
            logger.error(f"Invalid image format: {e}")
            raise ValueError(f"Invalid image format: {e}")

        # Prepare prompt and generate content
        prompt = f"{question or 'Describe what you see in this image'} using 25 words maximum."
        logger.debug(f"Using prompt: {prompt}")
        
        model = genai.GenerativeModel(GEMINI_VISION_MODEL)
        response = model.generate_content(
            [prompt, img],
            generation_config={
                'temperature': 0.2,
                'max_output_tokens': 100
            }
        )

        # Process response
        response_text = response.text.strip()
        if response_text.startswith('```'):
            response_text = response_text.replace('```json\n', '').replace('\n```', '')
        
        logger.info("Image analysis completed successfully")
        return response_text.strip()
        
    except FileNotFoundError as e:
        logger.error(f"File not found error: {e}")
        return f"Image not found: {e}"
    except ValueError as e:
        logger.error(f"Image validation error: {e}")
        return f"Invalid image: {e}"
    except Exception as e:
        logger.error(f"Unexpected error in image analysis: {e}")
        return f"Error analyzing image: {e}"

def analyze_audio(audio_path: str, prompt: str) -> str:
    """
    Analyze audio content using Gemini API.
    
    Args:
        audio_path (str): Path to the audio file
        prompt (str): Question or instruction for audio analysis
        
    Returns:
        str: Analysis result or error message
        
    Raises:
        FileNotFoundError: If audio file doesn't exist
        ValueError: If audio format is invalid
    """
    try:
        # Validate file exists
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        logger.info(f"Processing audio: {audio_path}")
        
        # Load and validate audio
        try:
            audio = AudioSegment.from_ogg(audio_path)
        except Exception as e:
            logger.error(f"Invalid audio format: {e}")
            raise ValueError(f"Invalid audio format: {e}")
            
        # Prepare audio data
        source = {
            "mime_type": "audio/ogg",
            "data": audio.export().read()
        }
        
        # Generate content
        model = genai.GenerativeModel(GEMINI_CHAT_MODEL)
        response = model.generate_content(
            [prompt, source],
            generation_config={
                'temperature': 0.2,
                'max_output_tokens': 150
            }
        )
        
        logger.info("Audio analysis completed successfully")
        return response.text.strip()
        
    except FileNotFoundError as e:
        logger.error(f"File not found error: {e}")
        return f"Audio file not found: {e}"
    except ValueError as e:
        logger.error(f"Audio validation error: {e}")
        return f"Invalid audio file: {e}"
    except Exception as e:
        logger.error(f"Unexpected error in audio analysis: {e}")
        return f"Error analyzing audio: {e}"

def retrieve_message_type_from_message(message: str, user_id: str = None) -> str:
    """
    Analyzes a message to determine its type using AI-driven intent detection.
    
    Args:
        message: The user's message to analyze
        user_id: Optional user ID to check cancellation state
        
    Returns:
        str: The detected message type (calendar, image, notion, search, automation, other)
    """
    if not message:
        return ''

    # Check if this is a number response during cancellation state
    if user_id and re.match(r'^\s*\d+\s*$', message):
        from utils.redis_utils import get_cancellation_state
        if get_cancellation_state(user_id):
            from functionality.calendar import cancel_event_by_index
            # Handle cancellation number response
            number_match = re.match(r'^\s*(\d+)\s*$', message)
            if number_match:
                index = int(number_match.group(1))
                cancelled_event = cancel_event_by_index(index)
                if cancelled_event:
                    return {
                        'intent': 'cancel_event',
                        'response': f"I've cancelled '{cancelled_event}'"
                    }
                return {
                    'intent': 'cancel_event',
                    'response': "Sorry, I couldn't cancel that event. Please try again."
                }

    # Enhanced calendar intent detection using AI
    calendar_intent_prompt = """
    Analyze if this message is related to calendar operations. Consider:
    1. Event Creation/Scheduling:
       - Creating meetings or appointments
       - Scheduling events
       - Booking time slots
       
    2. Schedule Checking:
       - Viewing calendar
       - Checking availability
       - Looking up meetings
       
    3. Calendar Management:
       - Canceling meetings
       - Modifying events
       - Managing appointments
    
    Message: {message}
    
    Return ONLY 'true' if this is definitely a calendar-related request, or 'false' if not.
    """
    
    try:
        # Enhanced intent detection using a two-stage approach
        model = genai.GenerativeModel(GEMINI_CHAT_MODEL)
        
        # Stage 1: Quick calendar check
        response = model.generate_content(
            calendar_intent_prompt.format(message=message),
            generation_config={
                'temperature': 0,
                'candidate_count': 1
            }
        )
        
        if not response.text:
            raise ValueError("Empty response from Gemini API")
            
        is_calendar = response.text.strip().lower() == 'true'
        
        if is_calendar:
            return 'calendar'
            
        # Stage 2: Detailed intent analysis for other types
        intent_prompt = """
        Analyze this message and determine its primary intent category:
        
        Message: {message}
        
        Categories:
        1. image - Visual analysis, object detection, or image-related queries
        2. notion - Note-taking, saving ideas, or documentation
        3. search - Information retrieval, news, or search queries
        4. automation - Home automation, device control, or status checks
        5. other - General queries or conversations
        
        Return ONLY the category name in lowercase, no explanation.
        """
        
        response = model.generate_content(
            intent_prompt.format(message=message),
            generation_config={
                'temperature': 0,
                'candidate_count': 1,
                'max_output_tokens': 10
            }
        )
        
        intent_type = response.text.strip().lower()
        if intent_type in ['image', 'notion', 'search', 'automation', 'other']:
            return intent_type
        return 'other'
        
    except Exception as e:
        logger.error(f"Error in intent detection: {e}")
        return 'other'  # Fallback to general conversation

def determine_calendar_event_inputs(message: str, user_id: str = 'default') -> dict:
    """
    Determine calendar event inputs from a message using AI-driven analysis.
    
    Args:
        message (str): The user's message to analyze
        user_id (str): The user's ID for state tracking
        
    Returns:
        dict: Calendar event details with the following structure:
            For check_schedule:
                {
                    'intent': 'check_schedule',
                    'response': str (formatted schedule)
                }
            For cancel_event:
                {
                    'intent': 'cancel_event',
                    'response': str (cancellation result)
                }
            For create_event:
                {
                    'intent': 'create_event',
                    'title': str,
                    'description': str,
                    'date': str (YYYY-MM-DD),
                    'time': str (HH:MM),
                    'duration': int,
                    'type': str
                }
    """
    try:
        if not message:
            raise ValueError("Message cannot be empty")
            
        determine_with_date: str = determine_calendar_event_inputs_description.replace(
            'time_now',
            datetime.now().strftime('%Y-%m-%d')
        )
        
        # Use AI to determine calendar intent
        calendar_action_prompt = """
        Analyze this calendar-related message and determine the specific intent:
        
        Message: {message}
        
        Return ONLY one of:
        - 'check_schedule' - For viewing or querying calendar/meetings
        - 'create_event' - For creating new meetings/events
        - 'cancel_event' - For canceling or removing meetings
        """
        
        model = genai.GenerativeModel(GEMINI_CHAT_MODEL)
        response = model.generate_content(
            calendar_action_prompt.format(message=message),
            generation_config={'temperature': 0}
        )
        
        intent = response.text.strip().lower()
        logger.debug(f"Detected calendar intent: {intent}")
        
        if intent == 'cancel_event':
            from functionality.calendar import get_upcoming_events, format_events_for_cancellation
            from utils.redis_utils import set_cancellation_state
            
            # Show list of events to cancel
            events = get_upcoming_events()
            # Set cancellation state with 30-second timeout
            set_cancellation_state(user_id)
            return {
                'intent': 'cancel_event',
                'response': format_events_for_cancellation(events)
            }
            
        elif intent == 'check_schedule':
            from functionality.calendar import (
                get_todays_schedule,
                get_tomorrows_schedule,
                get_this_week_schedule,
                get_next_week_schedule,
                format_schedule_response
            )
            
            # Use AI to determine time frame
            timeframe_prompt = """
            Analyze the message and determine the time frame for schedule check:
            
            Message: {message}
            
            Return ONLY one of:
            - 'next_week'
            - 'this_week'
            - 'tomorrow'
            - 'today'
            - 'both_days' (for general queries about schedule)
            """
            
            response = model.generate_content(
                timeframe_prompt.format(message=message),
                generation_config={'temperature': 0}
            )
            timeframe = response.text.strip().lower()
            logger.debug(f"Detected timeframe: {timeframe}")
            
            if timeframe == 'next_week':
                schedule = get_next_week_schedule()
                target_date = datetime.now() + timedelta(weeks=1)
                response = format_schedule_response(schedule, target_date, show_weekly=True)
            elif timeframe == 'this_week':
                schedule = get_this_week_schedule()
                target_date = datetime.now()
                response = format_schedule_response(schedule, target_date, show_weekly=True)
            elif timeframe == 'tomorrow':
                schedule = get_tomorrows_schedule()
                target_date = datetime.now() + timedelta(days=1)
                response = format_schedule_response(schedule, target_date)
            elif timeframe == 'both_days':
                schedule = get_todays_schedule()
                response = format_schedule_response(schedule, show_both_days=True)
            else:  # today or default
                schedule = get_todays_schedule()
                target_date = datetime.now()
                response = format_schedule_response(schedule, target_date)
                
            return {
                'intent': 'check_schedule',
                'response': response
            }
            
        else:  # create_event
            tool = _get_tool('determine_calendar_event_inputs', determine_with_date, {
                "intent": _get_func_arg_parameter(
                    'The type of calendar operation',
                    'string',
                    ["create_event"]
                ),
                "title": _get_func_arg_parameter(
                    'Extract the meeting title from the message. For example: "Set a meeting with Sales Manager" -> "Meeting with Sales Manager"'
                ),
                "description": _get_func_arg_parameter(
                    'For event creation, the description of the event'
                ),
                "date": _get_func_arg_parameter(
                    'Extract or infer the date in YYYY-MM-DD format. If no date mentioned, use today\'s date'
                ),
                "time": _get_func_arg_parameter(
                    'Extract and convert time to 24-hour HH:MM format. For example: "10AM" -> "10:00", "2pm" -> "14:00"'
                ),
                "duration": _get_func_arg_parameter(
                    'Duration in hours, default to 1 if not specified',
                    'integer'
                ),
                "type": _get_func_arg_parameter(
                    'The type of event',
                    'string',
                    ["reminder", "event", "time-block"]
                )
            }, ['intent', 'title', 'time'])
            
            model = genai.GenerativeModel(model_name=GEMINI_CHAT_MODEL, tools=[tool])
            chat = model.start_chat(enable_automatic_function_calling=True)
            response = chat.send_message(message)
            fc = response.candidates[0].content.parts[0].function_call
            logger.debug(f"Function call response: {fc}")
            
            assert fc.name == 'determine_calendar_event_inputs'
            
            # Set default date to today if not provided
            if 'date' not in fc.args:
                fc.args['date'] = datetime.now().strftime('%Y-%m-%d')
                
            return {
                'intent': 'create_event',
                'title': fc.args['title'],
                'description': fc.args.get('description', ''),
                'date': fc.args['date'],
                'time': fc.args['time'],
                'duration': fc.args.get('duration', 1),
                'type': fc.args.get('type', 'event')
            }
            
    except ValueError as e:
        logger.error(f"Invalid input error: {e}")
        return {'intent': 'error', 'response': str(e)}
    except Exception as e:
        logger.error(f"Error in calendar event processing: {e}")
        return {'intent': 'error', 'response': f"Failed to process calendar request: {e}"}
    

def determine_task_inputs(message: str) -> dict:
    """
    Determine task inputs from a message using AI-driven analysis.
    
    Args:
        message (str): The user's message to analyze
        
    Returns:
        dict: Task details with the following structure:
            For check_tasks:
                {
                    'intent': 'check_tasks',
                    'include_completed': bool,
                    'days_ahead': int
                }
            For create_task:
                {
                    'intent': 'create_task',
                    'title': str,
                    'notes': str (optional),
                    'due_date': str (optional, YYYY-MM-DD)
                }
            For update_task:
                {
                    'intent': 'update_task',
                    'task_id': str,
                    'completed': bool
                }
            For delete_task:
                {
                    'intent': 'delete_task',
                    'task_id': str
                }
    """
    try:
        if not message:
            raise ValueError("Message cannot be empty")

        tool = _get_tool('determine_task_inputs', determine_task_inputs_description, {
            "intent": _get_func_arg_parameter(
                'The type of task operation',
                'string',
                ["check_tasks", "create_task", "update_task", "delete_task"]
            ),
            "title": _get_func_arg_parameter(
                'For task creation, the title/description of the task'
            ),
            "notes": _get_func_arg_parameter(
                'For task creation, additional notes about the task'
            ),
            "due_date": _get_func_arg_parameter(
                'For task creation, the due date in YYYY-MM-DD format if specified'
            ),
            "task_id": _get_func_arg_parameter(
                'For update/delete operations, the ID of the task'
            ),
            "completed": _get_func_arg_parameter(
                'For update operations, whether to mark as completed',
                'boolean'
            ),
            "include_completed": _get_func_arg_parameter(
                'For check operations, whether to include completed tasks',
                'boolean'
            ),
            "days_ahead": _get_func_arg_parameter(
                'For check operations, number of days to look ahead',
                'integer'
            )
        })

        model = genai.GenerativeModel(model_name=GEMINI_CHAT_MODEL, tools=[tool])
        chat = model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(message)
        fc = response.candidates[0].content.parts[0].function_call
        logger.debug(f"Function call response: {fc}")

        assert fc.name == 'determine_task_inputs'

        # Process based on intent
        intent = fc.args.get('intent')
        if intent == 'check_tasks':
            return {
                'intent': 'check_tasks',
                'include_completed': fc.args.get('include_completed', False),
                'days_ahead': fc.args.get('days_ahead', 7)
            }
        elif intent == 'create_task':
            return {
                'intent': 'create_task',
                'title': fc.args['title'],
                'notes': fc.args.get('notes', ''),
                'due_date': fc.args.get('due_date')
            }
        elif intent == 'update_task':
            return {
                'intent': 'update_task',
                'task_id': fc.args['task_id'],
                'completed': fc.args['completed']
            }
        elif intent == 'delete_task':
            return {
                'intent': 'delete_task',
                'task_id': fc.args['task_id']
            }
        else:
            raise ValueError(f"Invalid intent: {intent}")

    except ValueError as e:
        logger.error(f"Invalid input error: {e}")
        return {'intent': 'error', 'response': str(e)}
    except Exception as e:
        logger.error(f"Error in task input processing: {e}")
        return {'intent': 'error', 'response': f"Failed to process task request: {e}"}

def determine_notion_page_inputs(message: str) -> dict:
    """
    Determine Notion page inputs from a message using AI analysis.
    
    Args:
        message (str): The message to analyze for Notion page creation
        
    Returns:
        dict: Notion page details with the following structure:
            {
                'title': str,
                'category': str (one of: Note, Idea, Work, Personal),
                'content': str
            }
            or
            {
                'error': str
            } if an error occurs
            
    Raises:
        ValueError: If message is empty or invalid
    """
    try:
        if not message:
            raise ValueError("Message cannot be empty")
            
        tool = _get_tool('determine_notion_page_inputs', determine_notion_page_inputs_description, {
            "title": _get_func_arg_parameter('The title of the page'),
            "category": _get_func_arg_parameter(
                '''
                The category of the page, default to `Note`.
                If it is a business idea, or something about entrepreneurship, or about making money, use `Idea`.
                If it is about work, or a project, use `Work`.
                If it is about personal stuff, or something about the user, use `Personal`, either money on a personal level, relationships, etc.
                Else, use `Note`.
                ''',
                enum_options=["Note", "Idea", "Work", "Personal"]),
            "content": _get_func_arg_parameter('The content of the message in the user words (more detail)')
        })
        
        model = genai.GenerativeModel(model_name=GEMINI_CHAT_MODEL, tools=[tool])
        chat = model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(message)
        
        try:
            fc = response.candidates[0].content.parts[0].function_call
            logger.debug(f"Function call response: {fc}")
            
            if not fc or not fc.name:
                raise ValueError("Invalid function call response")
                
            assert fc.name == 'determine_notion_page_inputs', f"Unexpected function name: {fc.name}"
            
            # Validate required fields
            if not all(key in fc.args for key in ['title', 'category', 'content']):
                raise ValueError("Missing required fields in response")
                
            return {
                'title': fc.args['title'],
                'category': fc.args['category'],
                'content': fc.args['content']
            }
            
        except (AttributeError, AssertionError, KeyError) as e:
            logger.error(f"Error processing function call response: {e}")
            raise ValueError(f"Failed to process Notion inputs: {e}")
            
    except ValueError as e:
        logger.error(f"Invalid input error: {e}")
        return {'error': str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in Notion input processing: {e}")
        return {'error': f"Failed to process Notion request: {e}"}