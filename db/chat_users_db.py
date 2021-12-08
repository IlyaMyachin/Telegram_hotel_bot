import sqlite3
from loguru import logger


@logger.catch
def create_db(user_id: int) -> None:
    """
    Функция. Создает таблицу нового пользователя в БД.
    :param user_id: id пользователя.
    :return: None
    """
    with sqlite3.connect('db/users_database.db') as chat_data:
        cursor = chat_data.cursor()

        cursor.execute("""CREATE TABLE IF NOT EXISTS users_data(user_id INTEGER UNIQUE,
                                                                command TEXT,
                                                                city_id INTEGER,
                                                                city_name TEXT,
                                                                hotels_count INTEGER,
                                                                photos_count INTEGER,
                                                                price_min INTEGER,
                                                                price_max INTEGER,
                                                                distance_min INTEGER,
                                                                distance_max INTEGER,
                                                                request_time TEXT,
                                                                checkIn TEXT,
                                                                checkOut TEXT
                                                                )""")

        try:
            cursor.execute(f""" INSERT INTO users_data(user_id) VALUES({user_id}) """)
            logger.info(f'Table for user {user_id} created')
        except sqlite3.IntegrityError:
            pass
        finally:
            chat_data.commit()


@logger.catch
def set_info(column: str, value: str or int, user_id: int) -> None:
    """
    Функция. Записывает данные пользователя в таблицу БД.
    :param column: название колонки таблицы для внесения данных.
    :param value: значение, которое будет внесено в колонку.
    :param user_id: id пользователя, в чью таблицу данных будут внесены изменения.
    :return: None
    """
    with sqlite3.connect('db/users_database.db') as chat_data:
        cursor = chat_data.cursor()
        info_to_set = f""" UPDATE users_data SET {column} = ? WHERE user_id = ? """
        data = (value, user_id)
        cursor.execute(info_to_set, data)
        chat_data.commit()


@logger.catch
def get_info(user_id: int) -> tuple:
    """
    Функция. Возвращает данные пользователя для запроса к API из таблицы БД.
    :param user_id: id пользователя
    :return: кортеж данных пользователя из таблицы БД
    """
    with sqlite3.connect('db/users_database.db') as chat_data:
        cursor = chat_data.cursor()
        cursor.execute(f""" SELECT * FROM users_data WHERE user_id = {user_id} """)

        return cursor.fetchone()
