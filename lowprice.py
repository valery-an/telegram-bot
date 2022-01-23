import telebot
import requests
import re
from decouple import config
from db_helper import DBHelper


TOKEN = config('token')
RAPIDAPI_KEY = config('rapidapi_key')
bot = telebot.TeleBot(TOKEN)
information = DBHelper()
information.setup()


def find_destination_id(destination):
    url = 'https://hotels4.p.rapidapi.com/locations/v2/search'
    querystring = {'query': destination}
    headers = {
        'x-rapidapi-host': 'hotels4.p.rapidapi.com',
        'x-rapidapi-key': RAPIDAPI_KEY
        }
    response = requests.request('GET', url, headers=headers, params=querystring)
    destination_id = response.json()['suggestions'][0]['entities'][0]['destinationId']
    return destination_id


def output_hotels(destination_id, hotels_number):
    url = 'https://hotels4.p.rapidapi.com/properties/list'
    querystring = {
        'destinationId': destination_id, 'pageNumber': "0", 'pageSize': hotels_number,
        'checkIn': '2022-02-20', 'checkOut': '2022-02-25', 'adults1': '2', 'sortOrder': 'PRICE',
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


def output_photos(hotel_id, photos_number):
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


@bot.message_handler(commands=['lowprice'], content_types=['text'])
def start(message):
    information.args.append(message.from_user.id)
    bot.send_message(message.chat.id, 'В какой город Вы хотите поехать?')
    bot.register_next_step_handler(message, get_city)


def get_city(message):
    city = message.text.title()
    information.args.append(city)
    bot.send_message(message.chat.id, 'Введите количество отелей, которые необходимо вывести')
    bot.register_next_step_handler(message, get_hotels_amount)


def get_hotels_amount(message):
    hotels_amount = message.text
    if not hotels_amount.isdigit():
        new_message = bot.send_message(message.chat.id, 'Количество должно быть числом, введите ещё раз')
        bot.register_next_step_handler(new_message, get_hotels_amount)
        return
    information.args.append(hotels_amount)
    bot.send_message(message.chat.id, 'Показать фотографии отелей? (да/нет)')
    bot.register_next_step_handler(message, get_have_photos)


def get_have_photos(message):
    if message.text.lower() == 'да':
        bot.send_message(message.chat.id, 'Введите количество фотографий для каждого отеля')
        bot.register_next_step_handler(message, get_photos_amount)
    elif message.text.lower() == 'нет':
        information.args.append(None)
        bot.register_next_step_handler(message, output_results)
    else:
        new_message = bot.send_message(message.chat.id, 'Я Вас не понимаю, да или нет?')
        bot.register_next_step_handler(new_message, get_have_photos)


def get_photos_amount(message):
    photos_amount = message.text
    if not photos_amount.isdigit():
        new_message = bot.send_message(message.chat.id, 'Количество должно быть числом, введите ещё раз')
        bot.register_next_step_handler(new_message, get_photos_amount)
        return
    information.args.append(photos_amount)
    new_message = bot.send_message(message.chat.id, 'Вывожу результаты?')
    bot.register_next_step_handler(new_message, output_results)


def output_results(message):
    if message.text.lower() == 'нет':
        bot.send_message(message.chat.id, 'Давайте начнём с начала /start')
    elif message.text.lower() == 'да':
        city_id = find_destination_id(information.args[1])
        hotels = output_hotels(city_id, information.args[2])
        for hotel in hotels:
            bot.send_message(message.chat.id, hotel[1])
            photos = output_photos(hotel[0], information.args[3])
            for photo in photos:
                bot.send_message(message.chat.id, photo)

        information.add_item()
        information.args = []
    else:
        new_message = bot.send_message(message.chat.id, 'Я Вас не понимаю, да или нет?')
        bot.register_next_step_handler(new_message, output_results)


bot.polling(none_stop=True, interval=0)
