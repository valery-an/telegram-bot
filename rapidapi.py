import re
import requests
from decouple import config
from typing import Iterable


RAPIDAPI_KEY = config('rapidapi_key')


def find_destination_id(destination: str) -> str:
    """ Функция, которая находит id города """

    url = 'https://hotels4.p.rapidapi.com/locations/v2/search'
    querystring = {'query': destination, 'locale': 'ru_RU'}
    headers = {
        'x-rapidapi-host': 'hotels4.p.rapidapi.com',
        'x-rapidapi-key': RAPIDAPI_KEY
        }
    response = requests.request('GET', url, headers=headers, params=querystring)
    destination_id = response.json()['suggestions'][0]['entities'][0]['destinationId']
    return destination_id


def output_hotels(destination_id: str, hotels_number: str, check_in: str, check_out: str,
                  sort_order: str) -> Iterable[tuple]:
    """
    Функция, которая генерирует id и названия отелей в городе
    :param destination_id: id города
    :param hotels_number: кол-во отелей, которое необходимо вывести
    :param check_in: дата заезда
    :param check_out: дата выезда
    :param sort_order: порядок сортировки отелей
    :return: кортежи из id и названия отелей
    """

    url = 'https://hotels4.p.rapidapi.com/properties/list'
    querystring = {
        'destinationId': destination_id, 'pageNumber': '1', 'pageSize': hotels_number,
        'checkIn': check_in, 'checkOut': check_out, 'adults1': '1', 'sortOrder': sort_order,
        'locale': 'ru_RU', 'currency': 'RUB'
        }
    headers = {
        'x-rapidapi-host': 'hotels4.p.rapidapi.com',
        'x-rapidapi-key': RAPIDAPI_KEY
        }
    response = requests.request('GET', url, headers=headers, params=querystring)
    hotels = response.json()['data']['body']['searchResults']['results']
    for element in hotels:
        hotel_id = element['id']
        hotel_name = element['name']
        yield hotel_id, hotel_name


def output_photos(hotel_id: str, photos_number: str) -> Iterable[str]:
    """
    Функция, которая генерирует фотографии отелей
    :param hotel_id: id отеля
    :param photos_number: кол-во фотографий, которое необходимо вывести
    :return: ссылки на фотографии
    """

    url = 'https://hotels4.p.rapidapi.com/properties/get-hotel-photos'
    querystring = {'id': hotel_id}
    headers = {
        'x-rapidapi-host': 'hotels4.p.rapidapi.com',
        'x-rapidapi-key': RAPIDAPI_KEY
        }
    response = requests.request('GET', url, headers=headers, params=querystring)
    photos = response.json()['hotelImages'][:int(photos_number)]
    for element in photos:
        photo = re.sub(r'{size}', 'b', element['baseUrl'])
        yield photo
