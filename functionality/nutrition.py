import os
import datetime
import json

import requests
from notion_client import Client
from utils.gemini import *
from utils.redis_utils import get_generic_cache
from utils.whatsapp import send_whatsapp_threaded

redis_key = 'logic_for_prompt_after_image:most-recent-image'
ok = {'status': 'Ok'}

secret = os.getenv('NOTION_INTEGRATION_SECRET')
client = Client(auth=secret)
db_id = os.getenv('NOTION_FOOD_DATABASE_ID')

def get_cals_from_image():
   img_url = get_generic_cache(redis_key)
   
   if not img_url:
       send_whatsapp_threaded('Please send an image of the food item.')
       return ok

   image_path = 'media/' + img_url.split('/')[-1]

   response = analyze_image(image_path, '''
   Determine calories from the image.
   Output in json format with the keys: "calories" for number of calories
   and "food" with description of the Food with a max of 5 words.
   Output only the JSON.'''.replace('    ', ''))
   
   res_json = json.loads(response)
   category_meal = determine_meal()
   food = res_json['food']
   calories = res_json['calories']
   res = add_new_food(food, category_meal, calories)
   send_whatsapp_threaded(f'{res} was added to your foodlog')
   return ok

def add_new_food(food: str, category: str, calories: int):
   data = {
       "parent": {"database_id": db_id},
       "properties": {
           "Food": {"title": [{"text": {"content": food}}]},
           "Category": {"select": {"name": category}},
           "Calories": {"number": calories}
       }
   }
   response = requests.post('https://api.notion.com/v1/pages', json=data, headers={
       'Authorization': f'Bearer {secret}',
       'Content-Type': 'application/json',
       'Accept': 'application/json',
       'Notion-Version': '2022-06-28'
   })
   return food

def determine_meal():
   now = datetime.now()
   if 0 < now.hour <= 10:
       return "Breakfast"
   elif 11 < now.hour <= 17:
       return "Lunch"
   elif 18 < now.hour <= 22:
       return "Dinner"
   else:
       return "Snack"