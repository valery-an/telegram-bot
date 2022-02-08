import telebot

from telebot import types
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datetime import date, datetime, timedelta
from loguru import logger
from decouple import config

from database.users_db import create_db, set_info, get_info
from rapidapi import find_destination_id, output_lowprice_highprice, output_bestdeal


logger.add('log.log', format='{time} {level} {message}', level='INFO')
TOKEN = config('token')
RAPIDAPI_KEY = config('rapidapi_key')
bot = telebot.TeleBot(TOKEN)


@logger.catch
@bot.message_handler(commands=['start'])
def start_handler(message: types.Message) -> None:
    """ Функция, выполняющая команду /start """

    logger.info(f'User {message.chat.id} used command /start')
    bot.send_message(chat_id=message.chat.id,
                     text=f'Добрый день, {message.from_user.first_name}!')
    help_handler(message)


@logger.catch
@bot.message_handler(commands=['help'])
def help_handler(message: types.Message) -> None:
    """ Функция, выполняющая команду /help """

    logger.info(f'User {message.chat.id} used command /help')
    bot.send_message(chat_id=message.chat.id,
                     text='Вы можете управлять мной с помощью следующих команд:\n'
                     '/lowprice — вывод самых дешёвых отелей в городе\n'
                     '/highprice — вывод самых дорогих отелей в городе\n'
                     '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n'
                     '/history — вывод истории поиска отелей')


@logger.catch
@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
def start(message: types.Message) -> None:
    """ Функция, которая реагирует на команды /lowprice, /highprice, /bestdeal """

    create_db(message.chat.id)
    logger.info(f'User {message.chat.id} used command {message.text}')
    set_info(column='command', value=message.text, user_id=message.chat.id)
    bot.send_message(chat_id=message.chat.id, text='В какой город вы хотите поехать?')
    bot.register_next_step_handler(message=message, callback=get_city)


@logger.catch
def get_city(message: types.Message) -> None:
    """ Функция, принимающая от пользователя название города, в котором необходимо осуществить поиск """

    city = message.text.title()
    set_info(column='city', value=city, user_id=message.chat.id)
    city_id = find_destination_id(city)
    if city_id == '0':
        bot.send_message(chat_id=message.chat.id, text='Город не найден, попробуйте ещё раз')
        bot.register_next_step_handler(message=message, callback=get_city)
        return
    set_info(column='city_id', value=city_id, user_id=message.chat.id)
    logger.info(f'Columns city and city_id updated for user {message.chat.id}')
    command = get_info(column='command', user_id=message.chat.id)
    if command == '/lowprice' or command == '/highprice':
        bot.send_message(chat_id=message.chat.id, text='Выберите дату заезда')
        select_check_in(message)
    else:
        bot.send_message(chat_id=message.chat.id, text='Введите диапазон цен за ночь (через пробел)\n'
                                                       'например: 500 10000')
        bot.register_next_step_handler(message=message, callback=get_price_range)


@logger.catch
def get_price_range(message: types.Message) -> None:
    """ Функция, принимающая от пользователя диапазон цен для команды /bestdeal """

    price_range = message.text.split()
    if len(price_range) != 2:
        bot.send_message(chat_id=message.chat.id,
                         text='Диапазон введён некорректно\nВведите минимальную и максимальную цены через пробел')
        bot.register_next_step_handler(message=message, callback=get_price_range)
        return
    price_min = price_range[0]
    price_max = price_range[1]
    if not price_min.isdigit() or not price_max.isdigit():
        bot.send_message(chat_id=message.chat.id, text='Диапазон введён некорректно\nВведите данные цифрами')
        bot.register_next_step_handler(message=message, callback=get_price_range)
        return
    if int(price_min.isdigit()) > int(price_max.isdigit()):
        price_min, price_max = price_max, price_min
    set_info(column='price_min', value=price_min, user_id=message.chat.id)
    set_info(column='price_max', value=price_max, user_id=message.chat.id)
    logger.info(f'Columns price_min and price_max updated for user {message.chat.id}')
    bot.send_message(chat_id=message.chat.id,
                     text='Введите диапазон расстояния, на котором отель находится от центра (через пробел)\n'
                          'например: 2 10')
    bot.register_next_step_handler(message=message, callback=get_distance_range)


@logger.catch
def get_distance_range(message: types.Message) -> None:
    """ Функция, принимающая от пользователя диапазон расстояния для команды /bestdeal """

    distance_range = message.text.split()
    if len(distance_range) != 2:
        bot.send_message(chat_id=message.chat.id,
                         text='Диапазон введён некорректно\n'
                              'Введите минимальное и максимальное расстояния через пробел')
        bot.register_next_step_handler(message=message, callback=get_distance_range)
        return
    distance_min = distance_range[0]
    distance_max = distance_range[1]
    if not distance_min.isdigit() or not distance_max.isdigit():
        bot.send_message(chat_id=message.chat.id, text='Диапазон введён некорректно\nВведите данные цифрами')
        bot.register_next_step_handler(message=message, callback=get_distance_range)
        return
    if int(distance_min.isdigit()) > int(distance_max.isdigit()):
        distance_min, distance_max = distance_max, distance_min
    set_info(column='distance_min', value=distance_min, user_id=message.chat.id)
    set_info(column='distance_max', value=distance_max, user_id=message.chat.id)
    logger.info(f'Columns distance_min and distance_max updated for user {message.chat.id}')
    bot.send_message(chat_id=message.chat.id, text='Выберите дату заезда')
    select_check_in(message)


@logger.catch
def select_check_in(message: types.Message) -> None:
    """ Функция, которая создаёт календарь заезда """

    calendar, step = DetailedTelegramCalendar(
        calendar_id='in', locale='ru', min_date=date.today(), max_date=date(2022, 3, 31)
    ).build()
    bot.send_message(chat_id=message.chat.id,
                     text=f'Select {LSTEP[step]}',
                     reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id='in'))
def cal(c: types.CallbackQuery) -> None:
    """ Функция, которая обрабатывает данные календаря заезда """

    result, key, step = DetailedTelegramCalendar(
        calendar_id='in', locale='ru', min_date=date.today(), max_date=date(2022, 3, 31)
    ).process(c.data)
    if not result and key:
        bot.edit_message_text(text=f'Select {LSTEP[step]}',
                              chat_id=c.message.chat.id,
                              message_id=c.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(text=f'Вы выбрали {result}',
                              chat_id=c.message.chat.id,
                              message_id=c.message.message_id)
        set_info(column='check_in', value=result, user_id=c.message.chat.id)
        logger.info(f'Column check_in updated for user {c.message.chat.id}')
        new_message = bot.send_message(chat_id=c.message.chat.id, text='Выберите дату выезда')
        select_check_out(new_message)


@logger.catch
def select_check_out(message: types.Message) -> None:
    """ Функция, которая создаёт календарь выезда """

    check_in_date = get_info(column='check_in', user_id=message.chat.id)
    check_in_date_plus = datetime.strptime(check_in_date, '%Y-%m-%d').date() + timedelta(days=1)
    calendar, step = DetailedTelegramCalendar(
        calendar_id='out', locale='ru', min_date=check_in_date_plus, max_date=date(2022, 3, 31)
    ).build()
    bot.send_message(chat_id=message.chat.id,
                     text=f'Select {LSTEP[step]}',
                     reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id='out'))
def cal(c: types.CallbackQuery) -> None:
    """ Функция, которая обрабатывает данные календаря выезда """

    check_in_date = get_info(column='check_in', user_id=c.message.chat.id)
    check_in_date_plus = datetime.strptime(check_in_date, '%Y-%m-%d').date() + timedelta(days=1)
    result, key, step = DetailedTelegramCalendar(
        calendar_id='out', locale='ru', min_date=check_in_date_plus, max_date=date(2022, 3, 31)
    ).process(c.data)
    if not result and key:
        bot.edit_message_text(text=f'Select {LSTEP[step]}',
                              chat_id=c.message.chat.id,
                              message_id=c.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(text=f'Вы выбрали {result}',
                              chat_id=c.message.chat.id,
                              message_id=c.message.message_id)
        set_info(column='check_out', value=result, user_id=c.message.chat.id)
        logger.info(f'Column check_out updated for user {c.message.chat.id}')
        new_message = bot.send_message(chat_id=c.message.chat.id,
                                       text='Введите количество отелей, которые необходимо вывести (максимум 25)')
        bot.register_next_step_handler(message=new_message, callback=get_hotels_amount)


@logger.catch
def get_hotels_amount(message: types.Message) -> None:
    """ Функция, принимающая от пользователя кол-во отелей, которое нужно вывести """

    hotels_amount = message.text
    if not hotels_amount.isdigit():
        new_message = bot.send_message(chat_id=message.chat.id,
                                       text='Количество должно быть числом, введите ещё раз')
        bot.register_next_step_handler(message=new_message, callback=get_hotels_amount)
        return
    if int(hotels_amount) < 1 or int(hotels_amount) > 25:
        new_message = bot.send_message(chat_id=message.chat.id,
                                       text='Количество должно быть от 1 до 25, введите ещё раз')
        bot.register_next_step_handler(message=new_message, callback=get_hotels_amount)
        return
    set_info(column='hotels_amount', value=hotels_amount, user_id=message.chat.id)
    logger.info(f'Column hotels_amount updated for user {message.chat.id}')
    bot.send_message(chat_id=message.chat.id, text='Показать фотографии отелей? (да/нет)')
    bot.register_next_step_handler(message=message, callback=have_photos)


@logger.catch
def have_photos(message: types.Message) -> None:
    """ Функция, принимающая от пользователя согласие или отказ на вывод фотографий """

    if message.text.lower() == 'да':
        bot.send_message(chat_id=message.chat.id,
                         text='Введите количество фотографий для каждого отеля (максимум 10)')
        bot.register_next_step_handler(message=message, callback=get_photos_amount)
    elif message.text.lower() == 'нет':
        set_info(column='photos_amount', value='None', user_id=message.chat.id)
        logger.info(f'Column photos_amount updated for user {message.chat.id}')
        bot.send_message(chat_id=message.chat.id, text='Выполняется поиск...')
        output_results(message)
    else:
        new_message = bot.send_message(chat_id=message.chat.id, text='Я Вас не понимаю, да или нет?')
        bot.register_next_step_handler(message=new_message, callback=have_photos)


@logger.catch
def get_photos_amount(message: types.Message) -> None:
    """ Функция, принимающая от пользователя кол-во фотографий, которое нужно вывести """

    photos_amount = message.text
    if not photos_amount.isdigit():
        new_message = bot.send_message(chat_id=message.chat.id,
                                       text='Количество должно быть числом, введите ещё раз')
        bot.register_next_step_handler(message=new_message, callback=get_photos_amount)
        return
    if int(photos_amount) < 1 or int(photos_amount) > 10:
        new_message = bot.send_message(chat_id=message.chat.id,
                                       text='Количество должно быть от 1 до 10, введите ещё раз')
        bot.register_next_step_handler(message=new_message, callback=get_photos_amount)
        return
    set_info(column='photos_amount', value=photos_amount, user_id=message.chat.id)
    logger.info(f'Column photos_amount updated for user {message.chat.id}')
    bot.send_message(chat_id=message.chat.id, text='Выполняется поиск...')
    output_results(message)


@logger.catch
def output_results(message: types.Message) -> None:
    """ Функция, которые выводит информацию об отелях и их фотографии """

    command = get_info(column='command', user_id=message.chat.id)
    if command == '/lowprice' or command == '/highprice':
        results = output_lowprice_highprice(message.chat.id)
    else:
        results = output_bestdeal(message.chat.id)
    for hotel_name, text, photos in results:
        bot.send_message(chat_id=message.chat.id, text=text)
        if len(photos) > 0:
            try:
                bot.send_media_group(chat_id=message.chat.id, media=photos)
            except telebot.apihelper.ApiTelegramException:
                logger.info(f"Can't output photos for {hotel_name}")
                bot.send_message(chat_id=message.chat.id, text='Фотографии не найдены')
    bot.send_message(chat_id=message.chat.id, text='Поиск завершён')
    logger.info(f'Command {command} for user {message.chat.id} completed')


@logger.catch
@bot.message_handler(content_types=['text'])
def check_command(message: types.Message) -> None:
    """ Функция, вылавливающая неверные команды """

    logger.info(f'User {message.chat.id} input unknown command')
    bot.send_message(chat_id=message.chat.id,
                     text='Вы ввели неизвестную мне команду')
    help_handler(message)


bot.polling(none_stop=True, interval=0)
