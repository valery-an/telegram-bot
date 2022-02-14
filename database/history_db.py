import sqlite3
from loguru import logger
from datetime import datetime, timedelta


@logger.catch
def create_history_db(user_id: int) -> None:
    """ Функция, которая создаёт таблицу history об истории поиска пользователя """

    connect = sqlite3.connect('database/bot_database.db')
    cursor = connect.cursor()
    try:
        cursor.execute(f"""CREATE TABLE history_{user_id}(command TEXT,
                                                          date_time DATETIME,
                                                          hotels TEXT)""")
        connect.commit()
        logger.info(f'Table "history_{user_id}" created')
    except sqlite3.OperationalError:
        pass


@logger.catch
def set_history_info(command: str, date_time: datetime, hotels: str, user_id: int) -> None:
    """
    Функция, которая записывает данные пользователя в таблицу history
    :param command: команда, которую вызвал пользователь
    :param date_time: дата и время ввода команда
    :param hotels: отели, которые были найдены
    :param user_id: id пользователя, в таблицу которого записываются данные
    """

    connect = sqlite3.connect('database/bot_database.db')
    cursor = connect.cursor()
    cursor.execute(f"""INSERT INTO history_{user_id}(command, date_time, hotels) VALUES(?, ?, ?)""",
                   (command, date_time, hotels))
    connect.commit()
    logger.info(f'Table "history_{user_id}" updated')


@logger.catch
def get_history_info(user_id: int) -> list or None:
    """ Функция, которая возвращает данные пользователя из таблицы history """

    connect = sqlite3.connect('database/bot_database.db')
    cursor = connect.cursor()
    if (f'history_{user_id}', ) in cursor.execute("""SELECT name FROM sqlite_master WHERE type='table'""").fetchall():
        data = cursor.execute(f"""SELECT * FROM history_{user_id}""").fetchall()
        return data
    else:
        return None


@logger.catch
def clear_history_db(user_id: int) -> None:
    connect = sqlite3.connect('database/bot_database.db')
    cursor = connect.cursor()
    clear_time = (datetime.now() - timedelta(days=2))
    cursor.execute(f"""DELETE FROM history_{user_id} WHERE date_time < '{clear_time}'""")
    connect.commit()
