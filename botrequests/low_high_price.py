import requests
import os

from loguru import logger
from typing import List
from datetime import date, timedelta
from dotenv import load_dotenv


load_dotenv()
headers = {
    'x-rapidapi-host': "hotels4.p.rapidapi.com",
    'x-rapidapi-key': os.getenv('API_KEY')
    }


@logger.catch
def hotels_info_for_low_high_price(town_id: str, count_of_hotels: int, command: str) -> List[dict] or None:
    """
    Функция. Осуществляет запрос к API Hotels для получения списка отелей
    и их характеристик по заданному ID города для команд lowprice и highprice.
    :param town_id: id города, для запроса.
    :param count_of_hotels: количество отелей, которое запросил пользователь.
    :param command: тип запроса, который выбрал пользователь.
    :return: список словарей из найденных отелей и их характеристик в формате:
        "ID": "цифровое значение ID города"
        "Наименование": "полное наименование отеля"
        "Адрес": "полный адрес отеля"
        "Расстояние": "расстояние от центра города до отеля"
        "Цена": "стоимость пребывания в отеле за сутки"
    """

    url_hotels = 'https://hotels4.p.rapidapi.com/properties/list'
    querystring = {"destinationId": town_id,
                   "pageNumber": "1",
                   "pageSize": count_of_hotels,
                   "checkIn": date.today(),
                   "checkOut": date.today() + timedelta(days=1),
                   "adults1": "1",
                   "sortOrder": "PRICE",
                   "locale": "ru_RU",
                   "currency": "RUB"}

    if command == 'highprice':
        querystring['sortOrder'] = 'PRICE_HIGHEST_FIRST'

    try:
        response = requests.request("GET", url_hotels,
                                    headers=headers,
                                    params=querystring,
                                    timeout=30)

        if response.status_code != 200:
            return None

        founded_hotels = response.json()
        hotels_list = [{'id': hotel['id'],
                        'name': hotel['name'],
                        'address': hotel.get('address', {}).get('streetAddress'),
                        'distance': hotel['landmarks'][0]['distance'],
                        'cur_price': hotel['ratePlan']['price']['current'],
                        }
                       for hotel in founded_hotels['data']['body']['searchResults']['results']]

        for dicts in hotels_list:
            for key, value in dicts.items():
                if value is None:
                    dicts[key] = 'Информация отсутствует'

        return hotels_list

    except requests.exceptions.RequestException as e:
        logger.info(f'{e} exceptions on step "hotels_info_for_low_high_price"')
        return None
