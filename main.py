import telebot
import requests
import re


bot = telebot.TeleBot('5034812020:AAEIohPIE_aLVS11Kp-SOVY4evg-2ZMIHWA')

help_text = 'Вы можете управлять мной с помощью следующих команд:\n' \
            '/lowprice — вывод самых дешёвых отелей в городе\n' \
            '/highprice — вывод самых дорогих отелей в городе\n' \
            '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n' \
            '/history — вывод истории поиска отелей'


city = ''
hotels_amount = 0
photos_amount = 0


def find_destination_id(destination):
    url = 'https://hotels4.p.rapidapi.com/locations/v2/search'
    querystring = {'query': destination}
    headers = {
        'x-rapidapi-host': 'hotels4.p.rapidapi.com',
        'x-rapidapi-key': '14ca6f0ecemsh1b6fc359f42f3cdp1f155fjsn10f1ce327f68'
        }
    response = requests.request('GET', url, headers=headers, params=querystring)
    destination_id = response.json()['suggestions'][0]['entities'][0]['destinationId']
    return destination_id


def output_hotels(destination_id, hotels_number):
    url = 'https://hotels4.p.rapidapi.com/properties/list'
    querystring = {
        'destinationId': destination_id, 'pageNumber': "0", 'pageSize': hotels_number,
        'checkIn': '2022-01-20', 'checkOut': '2022-01-25', 'adults1': '2', 'sortOrder': 'PRICE',
        'locale': 'ru_RU', 'currency': 'RUB'
        }
    headers = {
        'x-rapidapi-host': 'hotels4.p.rapidapi.com',
        'x-rapidapi-key': '14ca6f0ecemsh1b6fc359f42f3cdp1f155fjsn10f1ce327f68'
        }
    response = requests.request('GET', url, headers=headers, params=querystring)
    hotels = response.json()['data']['body']['searchResults']['results']
    for element in hotels:
        hotel_id = element['id']
        hotel_name = element['name']
        yield hotel_id, hotel_name


def output_photos(hotel_id, photos_number):
    url = 'https://hotels4.p.rapidapi.com/properties/get-hotel-photos'
    querystring = {'id': hotel_id}
    headers = {
        'x-rapidapi-host': 'hotels4.p.rapidapi.com',
        'x-rapidapi-key': '14ca6f0ecemsh1b6fc359f42f3cdp1f155fjsn10f1ce327f68'
        }
    response = requests.request('GET', url, headers=headers, params=querystring)
    photos = response.json()['hotelImages'][:int(photos_number)]
    for element in photos:
        photo = re.sub(r'{size}', 'b', element['baseUrl'])
        yield photo


@bot.message_handler(commands=['start', 'help'])
def start_handler(message):
    bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=['lowprice'], content_types=['text'])
def start(message):
    bot.send_message(message.chat.id, 'В какой город Вы хотите поехать?')
    bot.register_next_step_handler(message, get_city)


def get_city(message):
    global city
    city = message.text.title()
    bot.send_message(message.chat.id, 'Введите количество отелей, которые необходимо вывести')
    bot.register_next_step_handler(message, get_hotels_amount)


def get_hotels_amount(message):
    global hotels_amount
    hotels_amount = message.text
    if not hotels_amount.isdigit():
        new_message = bot.send_message(message.chat.id, 'Количество должно быть числом, введите ещё раз')
        bot.register_next_step_handler(new_message, get_hotels_amount)
        return
    bot.send_message(message.chat.id, 'Показать фотографии отелей? (да/нет)')
    bot.register_next_step_handler(message, get_have_photos)


def get_have_photos(message):
    if message.text.lower() == 'да':
        bot.send_message(message.chat.id, 'Введите количество фотографий для каждого отеля')
        bot.register_next_step_handler(message, get_photos)
    elif message.text.lower() == 'нет':
        bot.send_message(
            message.chat.id,
            'Вы хотите поехать в город {city}, мне нужно вывести список {hotels_amount} отелей без фотографий. '
            'Всё верно? (да/нет)'.format(city=city, hotels_amount=hotels_amount)
        )
        bot.register_next_step_handler(message, output_results)
    else:
        new_message = bot.send_message(message.chat.id, 'Я Вас не понимаю, да или нет?')
        bot.register_next_step_handler(new_message, get_have_photos)


def get_photos(message):
    global photos_amount
    photos_amount = message.text
    if not photos_amount.isdigit():
        new_message = bot.send_message(message.chat.id, 'Количество должно быть числом, введите ещё раз')
        bot.register_next_step_handler(new_message, get_photos)
        return
    bot.send_message(
        message.chat.id,
        'Вы хотите поехать в город {city}, мне нужно вывести список {hotels_amount} отелей с фотографиями. '
        'Всё верно? (да/нет)'.format(city=city, hotels_amount=hotels_amount)
    )
    bot.register_next_step_handler(message, output_results)


def output_results(message):
    if message.text.lower() == 'нет':
        bot.send_message(message.chat.id, 'Давайте начнём с начала /start')
    elif message.text.lower() == 'да':
        city_id = find_destination_id(city)
        hotels = output_hotels(city_id, hotels_amount)
        for hotel in hotels:
            bot.send_message(message.chat.id, hotel[1])
            photos = output_photos(hotel[0], photos_amount)
            for photo in photos:
                bot.send_message(message.chat.id, photo)
    else:
        new_message = bot.send_message(message.chat.id, 'Я Вас не понимаю, да или нет?')
        bot.register_next_step_handler(new_message, output_results)


bot.polling(none_stop=True, interval=0)
