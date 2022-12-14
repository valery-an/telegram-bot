import sqlite3
from loguru import logger


@logger.catch
def create_users_db(user_id: int) -> None:
    """ Функция, которая создаёт таблицу users_info о пользователях для работы с API """

    connect = sqlite3.connect('database/bot_database.db')
    cursor = connect.cursor()
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS users_info(user_id INTEGER UNIQUE,
                                                                command TEXT,
                                                                city_id INTEGER,
                                                                price_min INTEGER,
                                                                price_max INTEGER,
                                                                distance_min INTEGER,
                                                                distance_max INTEGER,
                                                                check_in TEXT,
                                                                check_out TEXT,
                                                                hotels_amount INTEGER,
                                                                photos_amount INTEGER)""")
        cursor.execute(f"""INSERT INTO users_info(user_id) VALUES({user_id})""")
        logger.info('Table "users_info" created')
    except sqlite3.IntegrityError:
        pass
    finally:
        connect.commit()


@logger.catch
def set_user_info(column: str, value: str or int, user_id: int) -> None:
    """
    Функция, которая записывает данные пользователя в таблицу users_info
    :param column: название столбца таблицы
    :param value: значение, которое нужно записать
    :param user_id: id пользователя, в строку которого записываются данные
    """

    connect = sqlite3.connect('database/bot_database.db')
    cursor = connect.cursor()
    cursor.execute(f"""UPDATE users_info SET {column} = ? WHERE user_id = ?""", (value, user_id))
    connect.commit()
    logger.info(f'Column "{column}" in table users_info updated for user {user_id}')


@logger.catch
def get_user_info(column: str, user_id: int) -> str or int:
    """ Функция, которая возвращает данные пользователя из таблицы users_info """

    connect = sqlite3.connect('database/bot_database.db')
    cursor = connect.cursor()
    cursor.execute(f"""SELECT {column} FROM users_info WHERE user_id = {user_id}""")
    data = cursor.fetchone()[0]
    return data
