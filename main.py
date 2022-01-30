import telebot
from datetime import date, datetime
from telebot import types
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from loguru import logger
from decouple import config
from database.db_helper import create_db, set_info, get_info
from rapidapi import find_destination_id, output_hotels, output_photos


logger.add('log.log', format='{time} {level} {message}', level='INFO')
TOKEN = config('token')
RAPIDAPI_KEY = config('rapidapi_key')
bot = telebot.TeleBot(TOKEN)


@logger.catch
@bot.message_handler(commands=['start'])
def start_handler(message: types.Message) -> None:
    """ Функция, выполняющая команду /start """

    logger.info(f'User {message.from_user.id} used command /start')
    bot.send_message(chat_id=message.chat.id,
                     text=f'Добрый день, {message.from_user.first_name}!')
    help_handler(message)


@logger.catch
@bot.message_handler(commands=['help'])
def help_handler(message: types.Message) -> None:
    """ Функция, выполняющая команду /help """

    logger.info(f'User {message.from_user.id} used command /help')
    bot.send_message(chat_id=message.chat.id,
                     text='Вы можете управлять мной с помощью следующих команд:\n'
                     '/lowprice — вывод самых дешёвых отелей в городе\n'
                     '/highprice — вывод самых дорогих отелей в городе\n'
                     '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n'
                     '/history — вывод истории поиска отелей')


@logger.catch
@bot.message_handler(commands=['lowprice', 'highprice'])
def start(message: types.Message) -> None:
    """ Функция, которая реагирует на команды /lowprice, /highprice """

    logger.info(f'User {message.from_user.id} used command {message.text}')
    create_db(message.from_user.id)
    set_info(column='command', value=message.text, user_id=message.from_user.id)
    bot.send_message(chat_id=message.chat.id, text='В какой город вы хотите поехать?')
    bot.register_next_step_handler(message=message, callback=get_city)


@logger.catch
def get_city(message: types.Message) -> None:
    """ Функция, принимающая от пользователя название города, в котором необходимо осуществить поиск """

    city = message.text.title()
    try:
        set_info(column='city', value=city, user_id=message.from_user.id)
        city_id = find_destination_id(city)
        set_info(column='city_id', value=city_id, user_id=message.from_user.id)
        logger.info(f'Columns city and city_id updated for user {message.from_user.id}')
        bot.send_message(chat_id=message.chat.id, text='Выберите дату заезда')
        select_check_in(message)
    except KeyError:
        bot.send_message(chat_id=message.chat.id, text='Такой город не найден, попробуйте ещё раз')
        help_handler(message)


@logger.catch
def select_check_in(message: types.Message) -> None:
    """ Функция, которая создаёт календарь заезда """

    calendar, step = DetailedTelegramCalendar(
        calendar_id='in', locale='ru', min_date=date.today()
    ).build()
    bot.send_message(chat_id=message.chat.id,
                     text=f'Select {LSTEP[step]}',
                     reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id='in'))
def call(c: types.CallbackQuery) -> None:
    """ Функция, которая обрабатывает данные календаря заезда """

    result, key, step = DetailedTelegramCalendar(
        calendar_id='in', locale='ru', min_date=date.today()
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

    check_in_date_str = get_info(column='check_in', user_id=message.chat.id)
    check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
    calendar, step = DetailedTelegramCalendar(
        calendar_id='out', locale='ru', min_date=check_in_date
    ).build()
    bot.send_message(chat_id=message.chat.id,
                     text=f'Select {LSTEP[step]}',
                     reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id='out'))
def cal(c: types.CallbackQuery) -> None:
    """ Функция, которая обрабатывает данные календаря выезда """

    check_in_date_str = get_info(column='check_in', user_id=c.message.chat.id)
    check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
    result, key, step = DetailedTelegramCalendar(
        calendar_id='out', locale='ru', min_date=check_in_date
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
        new_message = bot.send_message(c.message.chat.id,
                                       'Введите количество отелей, которые необходимо вывести (максимум 20)')
        bot.register_next_step_handler(new_message, get_hotels_amount)


@logger.catch
def get_hotels_amount(message: types.Message) -> None:
    """ Функция, принимающая от пользователя кол-во отелей, которое нужно вывести """

    hotels_amount = message.text
    if not hotels_amount.isdigit():
        new_message = bot.send_message(message.chat.id, 'Количество должно быть числом, введите ещё раз')
        bot.register_next_step_handler(new_message, get_hotels_amount)
        return
    if int(hotels_amount) < 1 or int(hotels_amount) > 20:
        new_message = bot.send_message(message.chat.id, 'Количество должно быть от 1 до 20, введите ещё раз')
        bot.register_next_step_handler(new_message, get_hotels_amount)
        return
    set_info(column='hotels_amount', value=hotels_amount, user_id=message.from_user.id)
    logger.info(f'Column hotels_amount updated for user {message.from_user.id}')
    bot.send_message(message.chat.id, 'Показать фотографии отелей? (да/нет)')
    bot.register_next_step_handler(message, get_have_photos)


@logger.catch
def get_have_photos(message: types.Message) -> None:
    """ Функция, принимающая от пользователя согласие или отказ на вывод фотографий """

    if message.text.lower() == 'да':
        bot.send_message(message.chat.id, 'Введите количество фотографий для каждого отеля (максимум 20)')
        bot.register_next_step_handler(message, get_photos_amount)
    elif message.text.lower() == 'нет':
        set_info(column='photos_amount', value='None', user_id=message.from_user.id)
        logger.info(f'Column photos_amount updated for user {message.from_user.id}')
        bot.send_message(message.chat.id, 'Выполняется поиск...')
        output_results(message)
    else:
        new_message = bot.send_message(message.chat.id, 'Я Вас не понимаю, да или нет?')
        bot.register_next_step_handler(new_message, get_have_photos)


@logger.catch
def get_photos_amount(message: types.Message) -> None:
    """ Функция, принимающая от пользователя кол-во фотографий, которое нужно вывести """

    photos_amount = message.text
    if not photos_amount.isdigit():
        new_message = bot.send_message(message.chat.id, 'Количество должно быть числом, введите ещё раз')
        bot.register_next_step_handler(new_message, get_photos_amount)
        return
    if int(photos_amount) < 1 or int(photos_amount) > 20:
        new_message = bot.send_message(message.chat.id, 'Количество должно быть от 1 до 20, введите ещё раз')
        bot.register_next_step_handler(new_message, get_hotels_amount)
        return
    set_info(column='photos_amount', value=photos_amount, user_id=message.from_user.id)
    logger.info(f'Column photos_amount updated for user {message.from_user.id}')
    bot.send_message(message.chat.id, 'Выполняется поиск...')
    output_results(message)


@logger.catch
def output_results(message: types.Message) -> None:
    """ Функция, которые выводит названия отелей и фотографии """

    city_id = get_info(column='city_id', user_id=message.from_user.id)
    hotels_amount = get_info(column='hotels_amount', user_id=message.from_user.id)
    check_in = get_info(column='check_in', user_id=message.from_user.id)
    check_out = get_info(column='check_out', user_id=message.from_user.id)
    photos_amount = get_info(column='photos_amount', user_id=message.from_user.id)
    command = get_info(column='command', user_id=message.from_user.id)
    if command == '/lowprice':
        sort_order = 'PRICE'
    elif command == '/highprice':
        sort_order = 'PRICE_HIGHEST_FIRST'
    else:
        sort_order = 'BEST_SELLER'
    hotels = output_hotels(destination_id=city_id, hotels_number=hotels_amount,
                           check_in=check_in, check_out=check_out, sort_order=sort_order)
    for hotel in hotels:
        bot.send_message(message.chat.id, hotel[1])
        if photos_amount != 'None':
            try:
                photos = output_photos(hotel[0], photos_amount)
                for photo in photos:
                    bot.send_message(message.chat.id, photo)
            except KeyError:
                pass


@logger.catch
@bot.message_handler(content_types=['text'])
def check_command(message: types.Message) -> None:
    """ Функция, вылавливающая неверные команды """

    logger.info(f'User {message.from_user.id} input unknown command')
    bot.send_message(chat_id=message.chat.id,
                     text='Вы ввели неизвестную мне команду')
    help_handler(message)


bot.polling(none_stop=True, interval=0)
