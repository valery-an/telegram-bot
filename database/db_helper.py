import sqlite3
from loguru import logger


@logger.catch
def create_db(user_id: int) -> None:
    """ Функция, которая создаёт таблицу нового пользователя """

    connect = sqlite3.connect('database/users_database.db')
    cursor = connect.cursor()
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS users_info(user_id INTEGER UNIQUE,
                                                                command TEXT,
                                                                city TEXT,
                                                                city_id INTEGER,
                                                                check_in TEXT,
                                                                check_out TEXT,
                                                                hotels_amount INTEGER,
                                                                photos_amount INTEGER)""")
        cursor.execute(f"""INSERT INTO users_info(user_id) VALUES({user_id})""")
        logger.info(f'Table for user {user_id} created')
    except sqlite3.IntegrityError:
        pass
    finally:
        connect.commit()


@logger.catch
def set_info(column: str, value: str or int, user_id: int) -> None:
    """
    Функция, которая записывает данные пользователя в таблицу
    :param column: название колонки таблицы
    :param value: значение, которое нужно записать
    :param user_id: id пользователя, в таблицу которого записываются данные
    """

    connect = sqlite3.connect('database/users_database.db')
    cursor = connect.cursor()
    cursor.execute(f"""UPDATE users_info SET {column} = ? WHERE user_id = ?""", (value, user_id))
    connect.commit()


@logger.catch
def get_info(column: str, user_id: int) -> str or int:
    """ Функция, которая возвращает данные пользователя для запроса к API """

    connect = sqlite3.connect('database/users_database.db')
    cursor = connect.cursor()
    cursor.execute(f"""SELECT {column} FROM users_info WHERE user_id = {user_id}""")
    data = cursor.fetchone()[0]
    return data
