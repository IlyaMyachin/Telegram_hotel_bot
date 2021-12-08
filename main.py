import telebot
import time
import os
import re
from datetime import date, datetime
from botrequests.city_id_request import search_city
from botrequests.low_high_price import hotels_info_for_low_high_price
from botrequests.best_deal import hotels_info_for_bestdeal
from botrequests.photo_request import get_photo
from loguru import logger
from db.chat_users_db import *
from db.history import *
from telebot import types
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from dotenv import load_dotenv


logger.add("log.log", format="{time} {level} {message}", level="INFO", rotation="10 MB", compression="zip")

load_dotenv()
bot = telebot.TeleBot(os.getenv('TOKEN'))


@logger.catch
@bot.message_handler(commands=['start'])
def start(message: types.Message) -> None:
    """
    Функция. Выполняет команду /start.
    Приветствует пользователя и знакомит его со списком доступных команд.
    :param message: сообщение пользователя с командной /start
    :return: None
    """
    logger.info(f'User {message.chat.id} used command /start')
    bot.send_message(chat_id=message.chat.id,
                     text=f"Добрый день, {message.from_user.first_name}!  Меня зовут HotelsAPIbot. "
                          "Я помогу вам подобрать отель с сайта hotels.com. "
                          "Доступны следующие команды: \n")
    help_message(message)


@logger.catch
@bot.message_handler(commands=['help'])
def help_message(message: types.Message) -> None:
    """
    Функция. Выполняет команду /help.
    Знакомит пользователя со списком доступных команд.
    :param message: сообщение пользователя с командной /help
    :return: None
    """
    logger.info(f'User {message.chat.id} used command /help')
    bot.send_message(chat_id=message.chat.id, text='/help - список доступных команд;\n'
                                                   '/lowprice - топ самых дешевых отелей в городе;\n'
                                                   '/highprice - топ самых дорогих отелей в городе;\n'
                                                   '/bestdeal - топ отелей, '
                                                   'наиболее подходящих по цене и расположению от центра;\n'
                                                   '/history - история поиска отелей;\n'
                                                   '/cancel - отмена текущего запроса.')


@logger.catch
@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
def get_city(message: types.Message) -> None:
    """
    Функция, которая реагирует на команды /lowprice, /highprice, /bestdeal.
    Принимает от пользователя название города, в котором требуется осуществить поиск.
    :param message: сообщение пользователя с одной из команд /lowprice, /highprice, /bestdeal.
    :return: None
    """
    logger.info(f'User {message.chat.id} used command {message.text}')
    chat_id = message.chat.id
    create_db(user_id=chat_id)
    set_info(column='command', value=message.text[1:], user_id=chat_id)
    set_info(column='request_time', value=datetime.today().strftime("%X %x"), user_id=chat_id)
    set_info(column='checkIn', value=None, user_id=message.chat.id)
    set_info(column='checkOut', value=None, user_id=message.chat.id)
    msg = bot.send_message(chat_id=message.chat.id, text='Укажите в каком городе ищем отель:')
    bot.register_next_step_handler(message=msg, callback=city_choice_keyboard)


@logger.catch
@bot.message_handler(commands=['cancel'])
def cancel_request(message: types.Message) -> None:
    """
    Функция, которая реагирует на команду /cancel.
    Отменяет текущий запрос пользователя.
    :param message: сообщение от пользователя с командой /cancel.
    :return: None
    """
    logger.info(f'User {message.chat.id} used command {message.text}')
    bot.send_message(chat_id=message.chat.id, text='Текущий запрос был отменен.')
    help_message(message)


@logger.catch
@bot.message_handler(commands=['history'])
def show_history(message: types.Message) -> None:
    """
    Функция. Реагирует на команду /history.
    :param message: сообщение пользователя с командной /history.
    :return: None.
    """
    logger.info(f'User {message.chat.id} used command {message.text}')

    try:
        history_list = list(get_history_info(user_id=message.chat.id))
    except TypeError:
        bot.send_message(chat_id=message.chat.id, text='Вы еще не производили поиск. История отсутствует.')
        help_message(message)
        return
    else:
        for data in history_list:
            history_message = f'{data[0]}: {data[1]}\n\n'
            for hotel in data[2].split("', "):
                hotel_pattern = re.sub(r"[\[\]\']", '', hotel)
                history_message += f'{hotel_pattern}\n'
            history_message += '*'*50
            bot.send_message(chat_id=message.chat.id, text=history_message)


@logger.catch
@bot.message_handler(content_types=['text'])
def message_check(message: types.Message) -> None:
    """
    Функция. Отлавливает некорректные команды.
    :param message: любое сообщение от пользователя, не являющееся командой.
    :return: None
    """
    logger.info(f'User {message.chat.id} input unknown command.')
    bot.send_message(chat_id=message.chat.id, text='Введена неизвестная команда.')
    help_message(message)


@logger.catch
def city_choice_keyboard(message: types.Message) -> None:
    """
    Функция, которая создает клавиатуру для выбора города из списка найденных городов.
    :param message: сообщение пользователя с названием города.
    :return: None
    """
    if message.text == '/cancel':
        cancel_request(message)
        return
    logger.info(f'Make a list of cities for user {message.chat.id}')
    bot.send_message(chat_id=message.chat.id, text='Осуществляю поиск...')
    chat_id = message.chat.id
    city = message.text.title()
    city_list = search_city(city=city)

    if city_list is None:
        bot.send_message(chat_id=message.chat.id, text='Не удается получить информацию с сайта.'
                                                       'Повторите запрос позднее.')
        return

    markup = types.InlineKeyboardMarkup(row_width=5)
    for i in city_list:
        for city_id, region in i.items():
            button_value = region.split(',')[0]
            markup.add(types.InlineKeyboardButton(text=region,
                                                  callback_data=('|'.join([button_value,
                                                                           str(city_id),
                                                                           str(chat_id)]))))
    markup.add(types.InlineKeyboardButton(text='Отмена',
                                          callback_data='Cancel'))

    if len(city_list) == 0:
        logger.info(f'City for user {message.chat.id} is not found')
        msg = bot.send_message(chat_id=chat_id, text=f'Город {city} не найден. Повторите ввод.')
        bot.register_next_step_handler(message=msg, callback=city_choice_keyboard)
    else:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id + 1)
        bot.send_message(chat_id=message.chat.id, text='Выберите город:', reply_markup=markup)


@logger.catch
def price_range(message: types.Message) -> None:
    """
    Функция. Принимает диапазон цен для поиска отелей в рамках команды /bestdeal.
    :param message: сообщение пользователя с диапазоном цен.
    :return: None
    """
    if message.text == '/cancel':
        cancel_request(message)
        return

    price_params = message.text.split()

    if len(price_params) != 2:
        logger.info(f'User {message.chat.id} input wrong price range.')
        msg = bot.send_message(chat_id=message.chat.id, text='Диапазон указан некорректно.\n'
                                                             'Укажите минимальную и максимальную '
                                                             'цены через пробел.')
        bot.register_next_step_handler(message=msg, callback=price_range)
        return

    try:
        if int(price_params[0]) > int(price_params[1]):
            price_params[0], price_params[1] = price_params[1], price_params[0]
        chat_id = message.chat.id
        set_info(column='price_min', value=int(price_params[0]), user_id=chat_id)
        set_info(column='price_max', value=int(price_params[1]), user_id=chat_id)
    except ValueError:
        msg = bot.send_message(chat_id=message.chat.id, text='Укажите значения цен цифрами.')
        bot.register_next_step_handler(message=msg, callback=price_range)
    else:
        logger.info(f'User {message.from_user.id} pick {message.text} as price range.')
        bot.send_message(chat_id=message.chat.id, text=f'Установлен диапазон: '
                                                       f'минимальная цена - {price_params[0]}, '
                                                       f'максимальная цена - {price_params[1]}.')
        msg = bot.send_message(chat_id=message.chat.id, text='Укажите через пробел диапазон расстояния, '
                                                             'в котором должен находиться отель от центра.')
        bot.register_next_step_handler(message=msg, callback=distance_range)


@logger.catch
def distance_range(message: types.Message) -> None:
    """
    Функция. Принимает диапазон расстояния удаленности отелей от центра города
    в рамках команды /bestdeal.
    :param message: сообщение пользователя с диапазоном расстояния.
    :return: None
    """
    if message.text == '/cancel':
        cancel_request(message)
        return

    distance_params = message.text.split()

    if len(distance_params) != 2:
        logger.info(f'User {message.chat.id} input wrong distance range.')
        msg = bot.send_message(chat_id=message.chat.id, text='Диапазон указан некорректно.\n'
                                                             'Укажите минимальное и максимальное '
                                                             'расстояние через пробел (в км).')
        bot.register_next_step_handler(message=msg, callback=distance_range)
        return

    try:
        if int(distance_params[0]) > int(distance_params[1]):
            distance_params[0], distance_params[1] = distance_params[1], distance_params[0]

        chat_id = message.chat.id
        set_info(column='distance_min', value=int(distance_params[0]), user_id=chat_id)
        set_info(column='distance_max', value=int(distance_params[1]), user_id=chat_id)
    except ValueError:
        msg = bot.send_message(chat_id=message.chat.id, text='Укажите значения расстояния цифрами.')
        bot.register_next_step_handler(message=msg, callback=distance_range)
    else:
        logger.info(f'User {message.from_user.id} pick {message.text} as distance range.')
        bot.send_message(chat_id=message.chat.id, text=f'Установлен диапазон: '
                                                       f'минимальное расстояние - {distance_params[0]}, '
                                                       f'максимальное расстояние - {distance_params[1]}.')
        msg = bot.send_message(chat_id=message.chat.id, text='Сколько отелей ищем (не более 25)?')
        bot.register_next_step_handler(message=msg, callback=get_hotels_count)


@logger.catch
def get_hotels_count(message: types.Message) -> None:
    """
    Функция, которая создает клавиатуру для уточнения необходимости выгрузки фотографий.
    Принимает от пользователя количество отелей для выгрузки.
    :param message: сообщение пользователя с количеством отелей.
    :return: None
    """
    if message.text == '/cancel':
        cancel_request(message)
        return

    try:
        if not 25 >= int(message.text) > 0:
            logger.info(f'User {message.chat.id} chose wrong number of hotels.')
            msg = bot.send_message(chat_id=message.chat.id, text='Указано некорректное значение.\n'
                                                                 'Укажите от 1 до 25 отелей.')
            bot.register_next_step_handler(message=msg, callback=get_hotels_count)
            return
    except ValueError:
        msg = bot.send_message(chat_id=message.chat.id, text='Укажите количество цифрами.')
        bot.register_next_step_handler(message=msg, callback=get_hotels_count)
    else:
        logger.info(f'Ask user {message.chat.id} about hotel photo.')
        chat_id = message.chat.id
        set_info(column='hotels_count', value=message.text, user_id=chat_id)
        bot.send_message(chat_id=message.chat.id, text='Укажите дату заезда в отель.')
        get_check_in_out_date(message)


@logger.catch
def get_check_in_out_date(message: types.Message) -> None:
    """
    Функция, которая вызывает календарь для выбора даты заезда в отель.
    :param message: сообщение с выбором дат.
    :return: None
    """
    calendar, step = DetailedTelegramCalendar().build()
    bot.send_message(chat_id=message.chat.id,
                     text=f"Select {LSTEP[step]}",
                     reply_markup=calendar)


@logger.catch
def add_photo(message: types.Message) -> None:
    """
    Функция. Принимает от пользователя количество фотографий.
    :param message сообщение пользователя с количеством фотографий отеля.
    :return None
    """

    if message.text == '/cancel':
        cancel_request(message)
        return

    try:
        if not 5 >= int(message.text) > 0:
            logger.info(f'User {message.chat.id} chose wrong number of photos.')
            msg = bot.send_message(chat_id=message.chat.id, text='Указано некорректное значение.')
            bot.register_next_step_handler(message=msg, callback=add_photo)
            return
    except ValueError:
        msg = bot.send_message(chat_id=message.chat.id, text='Укажите количество цифрами.')
        bot.register_next_step_handler(message=msg, callback=add_photo)
    else:
        logger.info(f'Set number of photos from user {message.chat.id} request')
        chat_id = message.chat.id
        set_info(column='photos_count', value=message.text, user_id=chat_id)
        result(user_id=chat_id)
        help_message(message)


@logger.catch
@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(call: types.CallbackQuery) -> None:
    """
    Функция. Принимает и обрабатывает данные календаря. Вносит даты заезда и выезда из отеля в бд.
    :param call: ответ на выбранные даты.
    :return: None
    """
    choice, key, step = DetailedTelegramCalendar().process(call.data)
    if not choice and key:
        bot.edit_message_text(f"Select {LSTEP[step]}",
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif choice:
        cur_choice = datetime.strptime(str(choice), "%Y-%m-%d").date()
        bot.delete_message(chat_id=int(call.message.chat.id), message_id=call.message.message_id)
        if date.today() > choice:
            bot.send_message(chat_id=call.message.chat.id, text='Нельзя выбрать прошедшую дату.\n'
                                                                'Выберите дату заезда.')
            get_check_in_out_date(call.message)
        elif get_info(call.message.chat.id)[11] is None:
            bot.send_message(chat_id=call.message.chat.id, text=f"Вы выбрали {choice}")
            set_info(column='checkIn', value=str(choice), user_id=call.message.chat.id)
            logger.info(f'User select {call.from_user.id} as IN date.')
            bot.send_message(chat_id=call.message.chat.id, text='Выберите дату выезда.')
            get_check_in_out_date(call.message)
        elif get_info(call.message.chat.id)[12] is None and datetime.strptime(str(get_info(call.message.chat.id)[11]),
                                                                              "%Y-%m-%d").date() < cur_choice:
            bot.send_message(chat_id=call.message.chat.id, text=f"Вы выбрали {choice}")
            set_info(column='checkOut', value=str(choice), user_id=call.message.chat.id)
            logger.info(f'User select {call.from_user.id} as OUT date.')
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(telebot.types.InlineKeyboardButton(text='Да', callback_data='Yes'))
            markup.add(telebot.types.InlineKeyboardButton(text='Нет', callback_data='No'))
            bot.send_message(chat_id=call.message.chat.id, text='Загрузить фото отеля?', reply_markup=markup)

        else:
            bot.send_message(chat_id=call.message.chat.id, text='Дата выезда не может совпадать или быть раньше '
                                                                'даты заезда.\nВыберите дату заезда.')
            set_info(column='checkIn', value=None, user_id=call.from_user.id)
            logger.info(f'User select wrong OUT date, IN date deleted.')
            get_check_in_out_date(call.message)


@logger.catch
@bot.callback_query_handler(func=lambda call: True)
def reg_city_choice(call: types.CallbackQuery) -> None:
    """
    Функция. Обрабатывает ответ пользователя, введенный с клавиатуры телеграм бота.
    :param call: ответ на выбор населенного пункта для поиска, ответ на вопрос о необходимости выгрузки фотографий.
    :return: None
    """
    if call.data == 'No':
        logger.info(f'User {call.from_user.id} choose request without photo.')
        bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
        set_info(column='photos_count', value=0, user_id=call.from_user.id)
        result(user_id=call.from_user.id)
        help_message(call.message)
    elif call.data == 'Yes':
        logger.info(f'User {call.from_user.id} choose request with photo.')
        bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
        msg = bot.send_message(chat_id=call.from_user.id, text='Укажите кол-во фотографий (не более 5).')
        bot.register_next_step_handler(message=msg, callback=add_photo)
    elif call.data == 'Cancel':
        bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
        cancel_request(call.message)
        return
    else:
        logger.info(f"User {call.from_user.id} choose city {call.data.split('|')[0]}")
        set_info(column='city_id', value=int(call.data.split('|')[1]), user_id=int(call.data.split('|')[2]))
        set_info(column='city_name', value=call.data.split('|')[0], user_id=int(call.data.split('|')[2]))
        bot.send_message(chat_id=call.from_user.id, text=call.data.split('|')[0])
        command_check = get_info(user_id=call.from_user.id)
        bot.edit_message_reply_markup(chat_id=call.from_user.id, message_id=call.message.message_id)
        if command_check[1] == 'bestdeal':
            msg = bot.send_message(chat_id=call.from_user.id, text='Введите диапазон цен через пробел.')
            bot.register_next_step_handler(message=msg, callback=price_range)
        else:
            msg = bot.send_message(chat_id=call.from_user.id, text='Сколько отелей ищем (не более 25)?')
            bot.register_next_step_handler(message=msg, callback=get_hotels_count)


@logger.catch
def result(user_id) -> None:
    """
    Функция. Осуществляет вывод информации о найденных отелях и их фотографии.
    :param user_id: id пользователя, по чьему запросу будет осуществлен вывод данных.
    :return: None
    """
    bot.send_message(chat_id=user_id, text='Подготавливаю список отелей по заданным параметрам...')
    info_from_bd = get_info(user_id=user_id)
    hotels_history_list = []

    if info_from_bd[1] == 'bestdeal':
        request_result = hotels_info_for_bestdeal(town_id=info_from_bd[2],
                                                  count_of_hotels=info_from_bd[4],
                                                  min_price=info_from_bd[6],
                                                  max_price=info_from_bd[7],
                                                  min_distance=info_from_bd[8],
                                                  max_distance=info_from_bd[9],
                                                  in_date=info_from_bd[11],
                                                  out_date=info_from_bd[12]
                                                  )
    else:
        request_result = hotels_info_for_low_high_price(town_id=info_from_bd[2],
                                                        count_of_hotels=info_from_bd[4],
                                                        command=info_from_bd[1],
                                                        in_date=info_from_bd[11],
                                                        out_date=info_from_bd[12])

    if request_result is None:
        bot.send_message(chat_id=user_id, text='Не удается получить информацию с сайта.'
                                               'Повторите запрос позднее.')
        return
    elif len(request_result) == 0:
        bot.send_message(chat_id=user_id, text='Отели по заданным условиям не найдены.')
        return

    for data in request_result:
        request_answer = f'Название отеля: {data.get("name")}\n'\
                         f'Адрес: {data.get("address")}\n' \
                         f'Расстояние от центра города: {data.get("distance")}\n' \
                         f'Цена: {data.get("cur_price")}\n'\
                         f'https://ru.hotels.com/ho{data.get("id")}'
        hotels_history_list.append(f'{data.get("name")}')
        bot.send_message(chat_id=user_id, text=request_answer, disable_web_page_preview=True)
        if info_from_bd[5] != 0:
            photos_list = []
            photos = get_photo(hotel_id=data['id'])

            if request_result is None:
                bot.send_message(chat_id=user_id, text='Не удается получить информацию с сайта.'
                                                       'Повторите запрос позднее.')
                return

            for elem in photos[:info_from_bd[5]]:
                if elem is not None:
                    photos_list.append(types.InputMediaPhoto((elem['photo']).replace('{size}', 'z')))
            try:
                bot.send_media_group(chat_id=user_id, media=photos_list)
            except telebot.apihelper.ApiTelegramException:
                bot.send_message(chat_id=user_id, text='По данному отелю не удалось получить фотографии.')

    create_history(req_time=info_from_bd[10], user_id=user_id)
    set_history_info(command_type=str(info_from_bd[1]),
                     request_result=str(hotels_history_list),
                     user_id=user_id)
    bot.send_message(chat_id=user_id, text='Поиск завершен.')


if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True, interval=0)
        except Exception as e:
            logger.error(f'Exception: {e}')
            time.sleep(15)
