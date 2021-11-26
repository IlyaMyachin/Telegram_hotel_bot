import sqlite3
from main import logger


@logger.catch
def create_history(req_time: str, user_id: int) -> None:
    """
    Функция. Создает таблицу для записи истории запросов пользователя.
    :param req_time: время создания запроса.
    :param user_id: id пользователя.
    :return: None
    """
    with sqlite3.connect('db/users_database.db') as chat_data:
        cursor = chat_data.cursor()

        table = f"""CREATE TABLE IF NOT EXISTS "{str(user_id)}_history"(request_time TEXT,
                                                                        command TEXT,
                                                                        hotels_name TEXT)"""
        cursor.execute(table)

        try:
            data = req_time,
            set_time = f""" INSERT INTO "{str(user_id)}_history"(request_time) VALUES(?) """
            cursor.execute(set_time, data)
        except sqlite3.IntegrityError:
            pass
        finally:
            chat_data.commit()
            logger.info(f'Table for user {user_id} history created')


@logger.catch
def set_history_info(command_type: str, request_result: str, user_id: int) -> None:
    """
    Функция. Записывает запросы пользователя в БД.
    :param user_id: id пользователя.
    :param command_type: тип запроса.
    :param request_result: названия найденный отелей.
    :return: None
    """
    with sqlite3.connect('db/users_database.db') as chat_data:
        cursor = chat_data.cursor()
        info_to_set = f""" UPDATE "{str(user_id)}_history" SET command = ?, 
                                                               hotels_name = ?
                                                           WHERE command is NULL and 
                                                                 hotels_name is NULL """
        data = (command_type, request_result)
        cursor.execute(info_to_set, data)
        chat_data.commit()
        logger.info(f"User's {user_id} history successfully saved")


@logger.catch
def get_history_info(user_id: int) -> list:
    """
    Функция. Возвращает историю запросов пользователя из таблицы БД.
    :param user_id: id пользователя.
    :return: список данных пользователя из таблицы БД.
    """
    try:
        with sqlite3.connect('db/users_database.db') as chat_data:
            cursor = chat_data.cursor()
            cursor.execute(f""" SELECT * FROM "{str(user_id)}_history" """)

            return cursor.fetchall()
    except sqlite3.OperationalError:
        pass

