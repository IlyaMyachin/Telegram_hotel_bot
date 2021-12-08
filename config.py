import os

from dotenv import load_dotenv

load_dotenv()
headers = {
    'x-rapidapi-host': "hotels4.p.rapidapi.com",
    'x-rapidapi-key': os.getenv('API_KEY')
    }

TOKEN = os.getenv('TOKEN')
