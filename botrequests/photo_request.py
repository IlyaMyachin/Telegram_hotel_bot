import requests

from loguru import logger
from typing import List

from config import headers


@logger.catch
def get_photo(hotel_id: str) -> List[dict] or None:
    """
    Функция. Осуществляет запрос к API Hotels для получения фотографий отеля,
    по заданному ID отеля.
    :param hotel_id: id отеля, для запроса.
    :return: список словарей из найденных фотографий в формате "Фотография": "ссылка на фотографию отеля".
    """

    url_photos = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
    querystring = {'id': hotel_id}
    try:
        response = requests.request("GET", url_photos,
                                    headers=headers,
                                    params=querystring,
                                    timeout=30)

        if response.status_code != 200:
            return None

        founded_url = response.json()
        url_list = [{'photo': url[f'baseUrl']} for url in founded_url['hotelImages']]
        return url_list

    except requests.exceptions.RequestException as e:
        logger.info(f'{e} exceptions on step "get_photo"')
        return None
