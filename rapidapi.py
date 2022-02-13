import requests
from decouple import config
from typing import Iterable
from loguru import logger
from re import sub
from telebot.types import InputMediaPhoto
from database.users_db import get_user_info


RAPIDAPI_KEY = config('rapidapi_key')
headers = {'x-rapidapi-host': 'hotels4.p.rapidapi.com', 'x-rapidapi-key': RAPIDAPI_KEY}


@logger.catch
def find_destinations(destination: str) -> dict:
    """ Функция, которая находит варианты направлений по введённому тексту """

    url = 'https://hotels4.p.rapidapi.com/locations/v2/search'
    querystring = {'query': destination, 'locale': 'ru_RU'}
    destinations = dict()
    try:
        response = requests.request('GET', url, headers=headers, params=querystring, timeout=10)
        suggestions = response.json()['suggestions'][0]['entities']
        for element in suggestions:
            caption = sub(r'<.*?>', '', element['caption'])
            destination_id = element['destinationId']
            destinations[caption] = destination_id
    except (requests.exceptions.ReadTimeout, IndexError) as exception:
        logger.info(f"Can't find destinations for {destination}: {exception}")
    finally:
        return destinations


@logger.catch
def output_hotels(destination_id: str, page_number: str, hotels_number: str, check_in: str, check_out: str,
                  price_min: str or None, price_max: str or None, sort_order: str) -> Iterable[dict]:
    """
    Функция, которая генерирует словари с информацией об отеле
    :param destination_id: id города
    :param page_number: номер страницы вывода (на каждой по 25 отелей)
    :param hotels_number: кол-во отелей, которое необходимо вывести
    :param check_in: дата заезда
    :param check_out: дата выезда
    :param price_min: минимальная цена за проживание
    :param price_max: максимальная цена за проживание
    :param sort_order: порядок сортировки отелей
    :return: словарь с данными отеля (id, название, рейтинг, адрес, расстояние до центра, цена, ссылка на сайт)
             или None в случае возникновения ошибки
    """

    url = 'https://hotels4.p.rapidapi.com/properties/list'
    querystring = {
        'destinationId': destination_id, 'pageNumber': page_number, 'pageSize': '25',
        'checkIn': check_in, 'checkOut': check_out, 'adults1': '1', 'priceMin': price_min, 'priceMax': price_max,
        'sortOrder': sort_order, 'locale': 'ru_RU', 'currency': 'RUB'
        }
    try:
        response = requests.request('GET', url, headers=headers, params=querystring, timeout=15)
        hotels = response.json()['data']['body']['searchResults']['results'][:int(hotels_number)]
        for element in hotels:
            hotel = dict()
            hotel['hotel_id'] = element['id']
            hotel['hotel_name'] = element['name']
            hotel['rating'] = element['starRating']
            address = element['address']
            hotel['country'] = address.get('countryName', '')
            hotel['locality'] = address.get('locality', '')
            hotel['street'] = address.get('streetAddress', '')
            hotel['postal_code'] = address.get('postalCode', '')
            hotel['downtown_distance'] = element['landmarks'][0]['distance']
            price = element['ratePlan']['price']
            hotel['price_info'] = price.get('info', '')
            hotel['price'] = price.get('exactCurrent')
            hotel['url'] = f"https://ru.hotels.com/ho{element['id']}"
            yield hotel
    except (requests.exceptions.ReadTimeout, IndexError) as exception:
        logger.info(f"Can't output hotels for city id {destination_id}: {exception}")
        return None


@logger.catch
def output_photos(hotel_id: str, photos_number: str) -> Iterable[str]:
    """
    Функция, которая генерирует фотографии отелей
    :param hotel_id: id отеля
    :param photos_number: кол-во фотографий, которое необходимо вывести
    :return: ссылки на фотографии
    """

    url = 'https://hotels4.p.rapidapi.com/properties/get-hotel-photos'
    querystring = {'id': hotel_id}
    try:
        response = requests.request('GET', url, headers=headers, params=querystring, timeout=15)
        photos = response.json()['hotelImages'][:int(photos_number)]
        for element in photos:
            photo_url = sub(r'{size}', 'b', element['baseUrl'])
            yield photo_url
    except (requests.exceptions.ReadTimeout, IndexError, KeyError) as exception:
        logger.info(f"Can't output photos for hotel id {hotel_id}: {exception}")
        return list()


@logger.catch
def output_lowprice_highprice(user_id: int) -> Iterable:
    """ Функция, которые выводит информацию об отелях и их фотографии для команд /lowprice и /highprice """

    city_id = get_user_info(column='city_id', user_id=user_id)
    hotels_amount = get_user_info(column='hotels_amount', user_id=user_id)
    check_in = get_user_info(column='check_in', user_id=user_id)
    check_out = get_user_info(column='check_out', user_id=user_id)
    photos_amount = get_user_info(column='photos_amount', user_id=user_id)
    command = get_user_info(column='command', user_id=user_id)
    if command == '/lowprice':
        sort_order = 'PRICE'
    else:
        sort_order = 'PRICE_HIGHEST_FIRST'
    hotels = output_hotels(destination_id=city_id, page_number='1', hotels_number=hotels_amount,
                           check_in=check_in, check_out=check_out,
                           price_min=None, price_max=None, sort_order=sort_order)
    if hotels is None:
        return None
    for index, hotel in enumerate(hotels, start=1):
        text = f"{index}) {hotel['hotel_name']}\nРейтинг: {hotel['rating']}\n" \
               f"Адрес: {hotel['country']}, {hotel['locality']}, {hotel['street']}, {hotel['postal_code']}\n" \
               f"Расстояние до центра: {hotel['downtown_distance']}\n" \
               f"Цена {hotel['price_info']}: {hotel['price']} руб.\n" \
               f"Ссылка: {hotel['url']}"
        photos = []
        if photos_amount != 'None':
            photos_url = output_photos(hotel_id=hotel['hotel_id'], photos_number=photos_amount)
            for photo_url in photos_url:
                photos.append(InputMediaPhoto(photo_url))
        yield hotel['hotel_name'], text, photos


@logger.catch
def output_bestdeal(user_id: int) -> Iterable:
    """ Функция, которые выводит информацию об отелях и их фотографии для команды /bestdeal """

    city_id = get_user_info(column='city_id', user_id=user_id)
    hotels_amount = get_user_info(column='hotels_amount', user_id=user_id)
    check_in = get_user_info(column='check_in', user_id=user_id)
    check_out = get_user_info(column='check_out', user_id=user_id)
    price_min = get_user_info(column='price_min', user_id=user_id)
    price_max = get_user_info(column='price_max', user_id=user_id)
    distance_min = get_user_info(column='distance_min', user_id=user_id)
    distance_max = get_user_info(column='distance_max', user_id=user_id)
    photos_amount = get_user_info(column='photos_amount', user_id=user_id)
    page_number = 1
    hotels_count = 0
    index = hotels_amount + 1
    while hotels_amount > 0 and hotels_count == 0:
        hotels_count = 25
        hotels = output_hotels(destination_id=city_id, page_number=str(page_number),
                               hotels_number=str(hotels_count), check_in=check_in, check_out=check_out,
                               price_min=price_min, price_max=price_max, sort_order='DISTANCE_FROM_LANDMARK')
        if hotels is None:
            return None
        for hotel in hotels:
            hotels_count -= 1
            if hotels_amount == 0:
                break
            distance = int(hotel['downtown_distance'].split()[0].split(',')[0])
            if distance_min > distance:
                continue
            if distance_max < distance + 1:
                hotels_amount = 0
                break
            text = f"{index - hotels_amount}) {hotel['hotel_name']}\nРейтинг: {hotel['rating']}\n" \
                   f"Адрес: {hotel['country']}, {hotel['locality']}, {hotel['street']}, {hotel['postal_code']}\n" \
                   f"Расстояние до центра: {hotel['downtown_distance']}\n" \
                   f"Цена {hotel['price_info']}: {hotel['price']} руб.\n" \
                   f"Ссылка: {hotel['url']}"
            photos = []
            if photos_amount != 'None':
                photos_url = output_photos(hotel_id=hotel['hotel_id'], photos_number=photos_amount)
                for photo_url in photos_url:
                    photos.append(InputMediaPhoto(photo_url))
            hotels_amount -= 1
            yield hotel['hotel_name'], text, photos
        page_number += 1
