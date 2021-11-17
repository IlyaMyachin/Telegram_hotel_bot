import requests
import json
import os
import re
from loguru import logger
from typing import Optional, List
from dotenv import load_dotenv


load_dotenv()
headers = {
    'x-rapidapi-host': "hotels4.p.rapidapi.com",
    'x-rapidapi-key': os.getenv('API_KEY')
    }


@logger.catch
def search_city(city: Optional[str]) -> List[dict] or None:
    """
    Функция. Осуществляет запрос к API Hotels для получения списка городов,
    подходящих под заданное название.
    :param city: название города для запроса, которое указал пользователь.
    :return: список словарей из найденных городов в формате "ID города": "полное наименование города".
    """

    url_location = 'https://hotels4.p.rapidapi.com/locations/search'
    querystring = {'query': city, 'locale': "ru_RU"}

    if re.match(r'^[A-Za-z]', city):
        querystring['locale'] = 'en_US'
    try:
        response = json.loads(requests.request('GET', url_location,
                                               headers=headers,
                                               params=querystring,
                                               timeout=30).text)

        city_list = []

        for i in response['suggestions'][0]['entities']:
            if i['name'] == city.title():
                caption = i['caption'].split(',')[-1]
                city_list.append({i['destinationId']: i['name'] + ',' + caption})

        return city_list
    except requests.exceptions.RequestException as e:
        logger.info(f'{e} exceptions on step "search_city"')
        return None
