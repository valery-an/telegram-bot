import telebot

from telebot import types
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datetime import date, datetime, timedelta
from loguru import logger
from decouple import config
from re import fullmatch, sub

from database.users_db import create_users_db, set_user_info, get_user_info
from database.history_db import create_history_db, set_history_info, get_history_info, clear_history_db
from rapidapi import find_destinations, output_lowprice_highprice, output_bestdeal


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
def begin(message: types.Message) -> None:
    """ Функция, которая реагирует на команды /lowprice, /highprice, /bestdeal """

    logger.info(f'User {message.chat.id} used command {message.text}')
    create_users_db(message.chat.id)
    create_history_db(message.chat.id)
    set_user_info(column='command', value=message.text, user_id=message.chat.id)
    bot.send_message(chat_id=message.chat.id, text='В какой город вы хотите поехать?')
    bot.register_next_step_handler(message=message, callback=get_city)


@logger.catch
def get_city(message: types.Message) -> None:
    """
    Функция, которая принимает от пользователя название города, в котором необходимо осуществить поиск
    и создаёт варианты направлений на выбор
    """

    destination = message.text
    suggestions = find_destinations(destination)
    if len(suggestions) == 0:
        bot.send_message(chat_id=message.chat.id, text='Город не найден, попробуйте ещё раз')
        bot.register_next_step_handler(message=message, callback=get_city)
        return
    inline_keyboard = types.InlineKeyboardMarkup(row_width=1)
    for city, destination_id in suggestions.items():
        inline_button = types.InlineKeyboardButton(city, callback_data=destination_id)
        inline_keyboard.add(inline_button)
    inline_button = types.InlineKeyboardButton('Выбрать другой город', callback_data='123')
    inline_keyboard.add(inline_button)
    bot.send_message(chat_id=message.chat.id, text='Уточните название города:', reply_markup=inline_keyboard)


@logger.catch
@bot.callback_query_handler(func=lambda call: fullmatch(r'\d{3,}', call.data))
def callback_city(cal: types.CallbackQuery) -> None:
    """ Функция, принимающая id города, в котором необходимо осуществить поиск """

    if cal.data == '123':
        bot.send_message(chat_id=cal.message.chat.id, text='В какой город вы хотите поехать?')
        bot.register_next_step_handler(message=cal.message, callback=get_city)
        return
    set_user_info(column='city_id', value=cal.data, user_id=cal.message.chat.id)
    command = get_user_info(column='command', user_id=cal.message.chat.id)
    if command == '/lowprice' or command == '/highprice':
        new_message = bot.send_message(chat_id=cal.message.chat.id, text='Выберите дату заезда')
        select_check_in(new_message)
    else:
        new_message = bot.send_message(chat_id=cal.message.chat.id,
                                       text='Введите диапазон цен за ночь (через пробел)\nнапример: 500 10000')
        bot.register_next_step_handler(message=new_message, callback=get_price_range)


@logger.catch
def get_price_range(message: types.Message) -> None:
    """ Функция, принимающая от пользователя диапазон цен для команды /bestdeal """

    if fullmatch(r'\d+\s\d+', message.text):
        price_range = message.text.split()
        price_min = price_range[0]
        price_max = price_range[1]
        if int(price_min) > int(price_max):
            price_min, price_max = price_max, price_min
        set_user_info(column='price_min', value=price_min, user_id=message.chat.id)
        set_user_info(column='price_max', value=price_max, user_id=message.chat.id)
        bot.send_message(chat_id=message.chat.id,
                         text='Введите максимальное расстояние, на котором отель находится от центра, '
                              'или диапазон расстояний (через пробел)\n'
                              'например: 2 10')
        bot.register_next_step_handler(message=message, callback=get_distance_range)
    else:
        bot.send_message(chat_id=message.chat.id,
                         text='Данные введены некорректно\nВведите минимальную и максимальную цены через пробел')
        bot.register_next_step_handler(message=message, callback=get_price_range)


@logger.catch
def get_distance_range(message: types.Message) -> None:
    """ Функция, принимающая от пользователя диапазон расстояния для команды /bestdeal """

    if fullmatch(r'\d+\s\d+', message.text):
        distance_range = message.text.split()
        distance_min = distance_range[0]
        distance_max = distance_range[1]
        if int(distance_min) > int(distance_max):
            distance_min, distance_max = distance_max, distance_min
        set_user_info(column='distance_min', value=distance_min, user_id=message.chat.id)
        set_user_info(column='distance_max', value=distance_max, user_id=message.chat.id)
        bot.send_message(chat_id=message.chat.id, text='Выберите дату заезда')
        select_check_in(message)
    elif fullmatch(r'[1-9]\d+', message.text):
        set_user_info(column='distance_min', value=0, user_id=message.chat.id)
        set_user_info(column='distance_max', value=message.text, user_id=message.chat.id)
        bot.send_message(chat_id=message.chat.id, text='Выберите дату заезда')
        select_check_in(message)
    else:
        bot.send_message(chat_id=message.chat.id,
                         text='Данные введены некорректно\nВведите расстояние цифрами')
        bot.register_next_step_handler(message=message, callback=get_distance_range)


@logger.catch
def select_check_in(message: types.Message) -> None:
    """ Функция, которая создаёт календарь заезда """

    calendar, step = DetailedTelegramCalendar(
        calendar_id='in', locale='ru', min_date=date.today(), max_date=date(2022, 3, 31)
    ).build()
    bot.send_message(chat_id=message.chat.id,
                     text=f'Select {LSTEP[step]}',
                     reply_markup=calendar)


@logger.catch
@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id='in'))
def callback_calendar(cal: types.CallbackQuery) -> None:
    """ Функция, которая обрабатывает данные календаря заезда """

    result, key, step = DetailedTelegramCalendar(
        calendar_id='in', locale='ru', min_date=date.today(), max_date=date(2022, 3, 31)
    ).process(cal.data)
    if not result and key:
        bot.edit_message_text(text=f'Select {LSTEP[step]}',
                              chat_id=cal.message.chat.id,
                              message_id=cal.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(text=f'Дата заезда: {result}',
                              chat_id=cal.message.chat.id,
                              message_id=cal.message.message_id)
        set_user_info(column='check_in', value=result, user_id=cal.message.chat.id)
        new_message = bot.send_message(chat_id=cal.message.chat.id, text='Выберите дату выезда')
        select_check_out(new_message)


@logger.catch
def select_check_out(message: types.Message) -> None:
    """ Функция, которая создаёт календарь выезда """

    check_in_date = get_user_info(column='check_in', user_id=message.chat.id)
    check_in_date_plus = datetime.strptime(check_in_date, '%Y-%m-%d').date() + timedelta(days=1)
    calendar, step = DetailedTelegramCalendar(
        calendar_id='out', locale='ru', min_date=check_in_date_plus, max_date=date(2022, 3, 31)
    ).build()
    bot.send_message(chat_id=message.chat.id,
                     text=f'Select {LSTEP[step]}',
                     reply_markup=calendar)


@logger.catch
@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id='out'))
def callback_calendar(cal: types.CallbackQuery) -> None:
    """ Функция, которая обрабатывает данные календаря выезда """

    check_in_date = get_user_info(column='check_in', user_id=cal.message.chat.id)
    check_in_date_plus = datetime.strptime(check_in_date, '%Y-%m-%d').date() + timedelta(days=1)
    result, key, step = DetailedTelegramCalendar(
        calendar_id='out', locale='ru', min_date=check_in_date_plus, max_date=date(2022, 3, 31)
    ).process(cal.data)
    if not result and key:
        bot.edit_message_text(text=f'Select {LSTEP[step]}',
                              chat_id=cal.message.chat.id,
                              message_id=cal.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(text=f'Дата выезда: {result}',
                              chat_id=cal.message.chat.id,
                              message_id=cal.message.message_id)
        set_user_info(column='check_out', value=result, user_id=cal.message.chat.id)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=5)
        buttons = []
        for digit in range(5, 26, 5):
            button = types.KeyboardButton(str(digit))
            buttons.append(button)
        keyboard.add(*buttons)
        new_message = bot.send_message(chat_id=cal.message.chat.id,
                                       text='Выберите количество отелей, которые необходимо вывести',
                                       reply_markup=keyboard)
        bot.register_next_step_handler(message=new_message, callback=get_hotels_amount)


@logger.catch
def get_hotels_amount(message: types.Message) -> None:
    """ Функция, принимающая от пользователя кол-во отелей, которое нужно вывести """

    hotels_amount = message.text
    if not hotels_amount.isdigit():
        bot.send_message(chat_id=message.chat.id,
                         text='Количество должно быть числом, введите ещё раз')
        bot.register_next_step_handler(message=message, callback=get_hotels_amount)
        return
    if int(hotels_amount) < 1 or int(hotels_amount) > 25:
        new_message = bot.send_message(chat_id=message.chat.id,
                                       text='Количество должно быть от 1 до 25, введите ещё раз')
        bot.register_next_step_handler(message=new_message, callback=get_hotels_amount)
        return
    set_user_info(column='hotels_amount', value=hotels_amount, user_id=message.chat.id)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_1 = types.KeyboardButton('да')
    button_2 = types.KeyboardButton('нет')
    keyboard.row(button_1, button_2)
    bot.send_message(chat_id=message.chat.id,
                     text='Показать фотографии отелей?',
                     reply_markup=keyboard)
    bot.register_next_step_handler(message=message, callback=have_photos)


@logger.catch
def have_photos(message: types.Message) -> None:
    """ Функция, принимающая от пользователя согласие или отказ на вывод фотографий """

    if message.text.lower() == 'да':
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=5)
        buttons = []
        for digit in range(1, 11):
            button = types.KeyboardButton(str(digit))
            buttons.append(button)
        keyboard.add(*buttons)
        bot.send_message(chat_id=message.chat.id,
                         text='Выберите количество фотографий для каждого отеля',
                         reply_markup=keyboard)
        bot.register_next_step_handler(message=message, callback=get_photos_amount)
    elif message.text.lower() == 'нет':
        set_user_info(column='photos_amount', value='None', user_id=message.chat.id)
        bot.send_message(chat_id=message.chat.id, text='Выполняется поиск...',
                         reply_markup=types.ReplyKeyboardRemove())
        output_results(message)
    else:
        new_message = bot.send_message(chat_id=message.chat.id, text='Я вас не понимаю, да или нет?')
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
    set_user_info(column='photos_amount', value=photos_amount, user_id=message.chat.id)
    bot.send_message(chat_id=message.chat.id, text='Выполняется поиск...',
                     reply_markup=types.ReplyKeyboardRemove())
    output_results(message)


@logger.catch
def output_results(message: types.Message) -> None:
    """ Функция, которые выводит информацию об отелях и их фотографии """

    command = get_user_info(column='command', user_id=message.chat.id)
    text_for_history = ''
    if command == '/lowprice' or command == '/highprice':
        results = output_lowprice_highprice(message.chat.id)
    else:
        results = output_bestdeal(message.chat.id)
    if results is None:
        bot.send_message(chat_id=message.chat.id, text='Что-то пошло не так, попробуйте ещё раз')
        help_handler(message)
        logger.info(f'Command {command} for user {message.chat.id} NOT completed')
        return
    for hotel_name, text, photos in results:
        text_for_history += sub(r'Рейтинг.*\n.*\n.*\n', '', text) + '\n'
        try:
            bot.send_message(chat_id=message.chat.id, text=text, disable_web_page_preview=True)
            if len(photos) > 0:
                bot.send_media_group(chat_id=message.chat.id, media=photos)
        except telebot.apihelper.ApiTelegramException:
            logger.info(f"Can't output photos or text for {hotel_name}")
    bot.send_message(chat_id=message.chat.id, text='Поиск завершён')
    logger.info(f'Command {command} for user {message.chat.id} completed')
    if text_for_history != '':
        set_history_info(command=command, date_time=datetime.now().replace(microsecond=0),
                         hotels=text_for_history, user_id=message.chat.id)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_1 = types.KeyboardButton('да')
    button_2 = types.KeyboardButton('нет')
    keyboard.row(button_1, button_2)
    bot.send_message(chat_id=message.chat.id, text='Искать ещё?', reply_markup=keyboard)
    bot.register_next_step_handler(message=message, callback=restart)


@logger.catch
def restart(message: types.Message) -> None:
    bot.send_message(chat_id=message.chat.id, text='Хорошо', reply_markup=types.ReplyKeyboardRemove())
    if message.text.lower() == 'да':
        help_handler(message)


@logger.catch
@bot.message_handler(commands=['history'])
def history_handler(message: types.Message) -> None:
    """ Функция, выполняющая команду /history """

    logger.info(f'User {message.chat.id} used command /history')
    clear_history_db(message.chat.id)
    data = get_history_info(message.chat.id)
    for row in data:
        bot.send_message(chat_id=message.chat.id,
                         text=f'Команда: {row[0]}\nДата: {row[1]}\n{row[2]}',
                         disable_web_page_preview=True)


@logger.catch
@bot.message_handler(content_types=['text'])
def check_command(message: types.Message) -> None:
    """ Функция, вылавливающая неверные команды """

    logger.info(f'User {message.chat.id} input unknown command')
    bot.send_message(chat_id=message.chat.id, text='Вы ввели неизвестную мне команду')
    help_handler(message)


bot.polling(none_stop=True, interval=0)
