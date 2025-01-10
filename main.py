import json
import logging
import os
import threading
import time
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse

from functionality.audio import retrieve_transcript_from_audio
from functionality.automation import automation_command
from functionality.calendar import create_google_calendar_event
from functionality.image import logic_for_prompt_before_image, retrieve_calories_from_image
from functionality.notion_ import add_new_page
from functionality.nutrition import get_cals_from_image
from functionality.search import google_search_pipeline
from utils.gemini import *
from utils.google_auth import GoogleAuth
from utils.whatsapp import send_whatsapp_threaded, send_whatsapp_image, download_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
       os.getenv('HOME_ASSISTANT_URL')
   ],
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)

@app.get('/')
def home():
   return 'API v1.0 OK'

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

def process_text_message(text: str):
   text_lower = text.lower().strip()
   
   if text_lower in COMMON_RESPONSES:
       send_whatsapp_threaded(COMMON_RESPONSES[text_lower])
       return ok

   if text_lower == 'cals':
       return retrieve_calories_from_image()

   isfoodlog = ' '.join(text_lower.split()[-2:])
   if isfoodlog in ['food log', 'foodlog', 'food log.', 'my diet', 'my diet.']:
       return get_cals_from_image()

   try:
       operation_type = retrieve_message_type_from_message(text)
       logger.info(f"Detected operation type: {operation_type}")

       if operation_type == 'image' and ImageContext.last_image_path:
           analysis = analyze_image(ImageContext.last_image_path, text)
           send_whatsapp_threaded(analysis)
           return ok
       elif operation_type == 'calendar':
           calendar_input = determine_calendar_event_inputs(text)
           
           if calendar_input['intent'] == 'check_schedule':
               send_whatsapp_threaded(calendar_input['response'])
           else:  # intent == 'create_event'
               create_args = {
                   'title': calendar_input['title'],
                   'description': calendar_input['description'],
                   'date': calendar_input['date'],
                   'time': calendar_input['time'],
                   'duration': calendar_input['duration'],
                   'color_id': 9 if calendar_input['type'] == 'reminder' and calendar_input['duration'] == 0.5 else 0
               }
               create_google_calendar_event(**create_args)
               send_whatsapp_threaded('I have added that to your calendar!')
           return ok
       elif operation_type == 'notion':
           arguments = determine_notion_page_inputs(text)
           add_new_page(**arguments)
           send_whatsapp_threaded('Notion page created successfully!')
           return ok
       elif operation_type == 'search':
           response = google_search_pipeline(text)
           send_whatsapp_threaded(response)
           return ok
       elif operation_type == 'automation':
           response = automation_command(text)
           send_whatsapp_threaded(response)
           return ok
       else:
           response = simple_prompt_request(text + '. Respond like a friendly AI assistant in 10 to 15 words.')
           send_whatsapp_threaded(response)
           return ok

   except AssertionError:
       try:
           response = simple_prompt_request(text + '. Respond like a friendly AI assistant in 10 to 15 words.')
           send_whatsapp_threaded(response)
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
           result = retrieve_transcript_from_audio(message)
       else:
           text = message['text']['body']
           logger.info(f"Processing text message: {text}")
           result = process_text_message(text)

       processing_time = time.time() - start_time
       logger.info(f"Message processing completed in {processing_time:.2f} seconds")
       return result

   except Exception as e:
       processing_time = time.time() - start_time
       logger.error(f"Error processing message after {processing_time:.2f} seconds: {str(e)}")
       raise

if __name__ == "__main__":
   import uvicorn
   uvicorn.run(app, host="0.0.0.0", port=8000)
