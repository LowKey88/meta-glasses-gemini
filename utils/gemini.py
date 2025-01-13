import os
import google.ai.generativelanguage as glm
import google.generativeai as genai
import requests
from PIL import Image
from pydub import AudioSegment
from datetime import datetime, timedelta

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

retrieve_message_type_from_message_description = '''
Based on the message type, execute some different requests to APIs or other tools. 

- calendar: types are related to:
  * Checking schedule/meetings/appointments (e.g. "check my meeting", "check my meetings", "what's my schedule", "do I have any meetings")
  * Creating events/meetings/reminders
  * Anything with scheduling, calendar, or time management
  
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

determine_notion_page_inputs_description = f'''Based on the message, create a new page in your Notion database. 
- title: The title of the page
- category: The category of the page, default to `Note`
- content: The content of the message in the user words (without more detail, just in user words)

Make sure to return all the required inputs for the page creation.
'''.replace('    ', '')

def simple_prompt_request(message: str):
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    actual_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    message_2: str = f'''The current time is {actual_time}. {message}'''
    response = model.generate_content(message_2)
    return response.text.strip()

def generate_google_search_query(user_input: str):
    return simple_prompt_request(f'''Create a simple search query for: "{user_input}".
    Return only the search terms, no formatting or explanation.''')

def retrieve_scraped_data_short_answer(news_content: str, user_query: str):
    return simple_prompt_request(f'''You are a helpful assistant, You take the user query and the text from scraped data of articles/news/pages, and return a short condenseated answer to the user query based on the scraped data, use 10 to 15 words.
    Context: {news_content}\nUser Query: {user_query}''')

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

def analyze_image(img_url: str, question: str = None):
    if img_url.startswith('media/'):
        image_path = img_url
    else:
        image_path = 'media/' + img_url.split('/')[-1]
    print('Using image path:', image_path)

    try:
        img = Image.open(image_path)
        prompt = f"{question or 'Describe what you see in this image'} using 25 words maximum."
        response = genai.GenerativeModel('gemini-2.0-flash-exp').generate_content([prompt, img], stream=False)
        response_text = response.text.strip()
        if response_text.startswith('```'):
            response_text = response_text.replace('```json\n', '').replace('\n```', '')
        return response_text.strip()
    except Exception as e:
        return f"Error analyzing image: {e}"

def analyze_audio(audio_path: str, prompt):
    audio = AudioSegment.from_ogg(audio_path)
    model = genai.GenerativeModel('gemini-1.5-flash')
    source = {
        "mime_type": "audio/ogg",
        "data": audio.export().read()
    }
    response = model.generate_content([prompt, source])
    return response.text.strip()

def retrieve_message_type_from_message(message: str):
    print('retrieve_message_type_from_message', message)
    if not message:
        return ''
        
    # Check for explicit calendar commands first
    msg_lower = message.lower()
    calendar_keywords = [
        'set a meeting',
        'schedule a meeting',
        'set an appointment',
        'schedule an appointment',
        'cancel my last meeting',
        'cancel last meeting',
        'cancel the last meeting',
        'cancel my latest meeting',
        'cancel my most recent meeting',
        'remove my last meeting',
        'remove last meeting',
        'delete my last meeting',
        'delete last meeting',
        'check my schedule',
        'what meetings do i have',
        'show my schedule'
    ]
    
    if any(keyword in msg_lower for keyword in calendar_keywords):
        return 'calendar'

    tool = _get_tool(
        'execute_based_on_message_type',
        retrieve_message_type_from_message_description,
        {"message_type": _get_func_arg_parameter(
            'The type of message the user sent', 'string',
            ["calendar", "image", "notion", "search", "automation", "other"])})
    model = genai.GenerativeModel(model_name='gemini-1.5-flash', tools=[tool])
    chat = model.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(message)
    fc = response.candidates[0].content.parts[0].function_call
    assert fc.name == 'execute_based_on_message_type'
    print('retrieve_message_type_from_message response:', fc.args['message_type'])
    return fc.args['message_type']

def determine_calendar_event_inputs(message: str):
    """Determine if the message is checking schedule or creating an event."""
    determine_with_date: str = determine_calendar_event_inputs_description.replace('time_now', datetime.now().strftime('%Y-%m-%d'))
    
    # First check if this is a schedule query and what date it's for
    is_schedule_query = any(q in message.lower() for q in [
        "check", "what", "show me", "tell me about",
        "do i have", "my meeting", "my schedule"
    ])
    
    # Check if this is a cancel command
    is_cancel_command = any(phrase in message.lower() for phrase in [
        "cancel my last meeting",
        "cancel last meeting",
        "delete my last meeting",
        "delete last meeting",
        "remove my last meeting",
        "remove last meeting"
    ])
    
    if is_cancel_command:
        from functionality.calendar import cancel_last_meeting
        cancelled_event = cancel_last_meeting()
        if cancelled_event:
            return {
                'intent': 'cancel_event',
                'response': f"I've cancelled your last meeting: {cancelled_event}"
            }
        return {
            'intent': 'cancel_event',
            'response': "I couldn't find any upcoming meetings to cancel."
        }
        
    if is_schedule_query:
        from functionality.calendar import (
            get_todays_schedule,
            get_tomorrows_schedule,
            get_this_week_schedule,
            get_next_week_schedule,
            format_schedule_response
        )
        
        msg_lower = message.lower()
        
        # Check what type of schedule query this is
        if "next week" in msg_lower:
            schedule = get_next_week_schedule()
            target_date = datetime.now() + timedelta(weeks=1)
            response = format_schedule_response(schedule, target_date, show_weekly=True)
        elif "this week" in msg_lower:
            schedule = get_this_week_schedule()
            target_date = datetime.now()
            response = format_schedule_response(schedule, target_date, show_weekly=True)
        elif "tomorrow" in msg_lower:
            schedule = get_tomorrows_schedule()
            target_date = datetime.now() + timedelta(days=1)
            response = format_schedule_response(schedule, target_date)
        elif any(phrase in msg_lower for phrase in ["what's my schedule", "what is my schedule", "show my schedule", "tell me my schedule"]):
            # For general schedule queries, show both today and tomorrow
            schedule = get_todays_schedule()  # Placeholder since we'll use show_both_days=True
            response = format_schedule_response(schedule, show_both_days=True)
        else:
            # Default to today's schedule only
            schedule = get_todays_schedule()
            target_date = datetime.now()
            response = format_schedule_response(schedule, target_date)
        
        return {
            'intent': 'check_schedule',
            'response': response
        }
    
    # If not a schedule query, it must be event creation
    tool = _get_tool('determine_calendar_event_inputs', determine_with_date, {
        "intent": _get_func_arg_parameter(
            'The type of calendar operation',
            'string',
            ["create_event"]
        ),
        # Event creation parameters
        "title": _get_func_arg_parameter(
            'For event creation, the title of the event'
        ),
        "description": _get_func_arg_parameter(
            'For event creation, the description of the event'
        ),
        "date": _get_func_arg_parameter(
            'For event creation, the date in YYYY-MM-DD format'
        ),
        "time": _get_func_arg_parameter(
            'For event creation, the time in HH:MM format'
        ),
        "duration": _get_func_arg_parameter(
            'For event creation, the duration in hours',
            'integer'
        ),
        "type": _get_func_arg_parameter(
            'For event creation, the type of event',
            'string',
            ["reminder", "event", "time-block"]
        )
    }, ['intent'])

    model = genai.GenerativeModel(model_name='gemini-1.5-flash', tools=[tool])
    chat = model.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(message)
    fc = response.candidates[0].content.parts[0].function_call
    print(fc)
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

def determine_notion_page_inputs(message: str):
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
    model = genai.GenerativeModel(model_name='gemini-1.5-flash', tools=[tool])
    chat = model.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(message)
    fc = response.candidates[0].content.parts[0].function_call
    assert fc.name == 'determine_notion_page_inputs'
    return {
        'title': fc.args['title'],
        'category': fc.args['category'],
        'content': fc.args['content']
    }
