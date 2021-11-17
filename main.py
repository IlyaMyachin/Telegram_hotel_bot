import telebot
import time
import os
from db.chat_users_db import *
from botrequests.city_id_request import search_city
from botrequests.low_high_price import hotels_info_for_low_high_price
from botrequests.photo_request import get_photo
from telebot import types
from dotenv import load_dotenv
from loguru import logger


logger.add("log.log", format="{time} {level} {message}", level="INFO", rotation="10 MB", compression="zip")

load_dotenv()
bot = telebot.TeleBot(os.getenv('TOKEN'))


@logger.catch
@bot.message_handler(commands=['start'])
def start(message: types.Message) -> None:
    """/lowprice
    Функция. Выполняет команду /start.
    Приветствует пользователя и знакомит его со списком доступных команд.
    :param message: сообщение пользователя с командной /start
    :return: None
    """
    logger.info(f'User {message.chat.id} used command /start')
    bot.send_message(chat_id=message.chat.id,
                     text=f"Добрый день, {message.from_user.first_name}!  Меня зовут HotelsAPIbot. "
                          "Я помогу вам подобрать отель с сайта hotels.com."
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
                                                   '/history - история поиска отелей.\n')


@logger.catch
@bot.message_handler(content_types=['text'])
def message_check(message: types.Message) -> None:
    """
    Функция. Отлавливает некорректные команды.
    :param message:
    :return: None
    """
    logger.info(f'User {message.chat.id} input unknown command.')
    bot.send_message(chat_id=message.chat.id, text='Введена неизвестная команда.')
    help_message(message)


@logger.catch
@bot.message_handler(commands=['lowprice', 'highprice'])
def get_city(message: types.Message) -> None:
    """
    Функция, которая реагирует на команды /lowprice, /highprice.
    Принимает от пользователя название города, в котором требуется осуществить поиск.
    :param message: сообщение пользователя с командной из команд /lowprice, /highprice.
    :return: None
    """
    logger.info(f'User {message.chat.id} used command {message.text}')
    chat_id = message.chat.id
    create_db(user_id=chat_id)
    set_info(column='command', value=message.text[1:], user_id=chat_id)
    msg = bot.send_message(chat_id=message.chat.id, text='Укажите в каком городе ищем отель:')
    bot.register_next_step_handler(message=msg, callback=city_choice_keyboard)


@logger.catch
def city_choice_keyboard(message: types.Message) -> None:
    """
    Функция, которая создает клавиатуру для выбора города из списка найденных городов.
    """
    logger.info(f'Make a list of cities for user {message.chat.id}')
    chat_id = message.chat.id
    city = message.text.title()
    city_list = search_city(city=city)

    if city_list is None:
        bot.send_message(chat_id=message.chat.id, text='Не удается получить информацию с сайта.'
                                                       'Повторите запрос позднее.')
        return

    markup = types.InlineKeyboardMarkup(row_width=3)
    for i in city_list:
        for city_id, region in i.items():
            markup.add(types.InlineKeyboardButton(text=region,
                                                  callback_data=('|'.join([region, str(city_id), str(chat_id)]))))

    if len(city_list) == 0:
        logger.info(f'City for user {message.chat.id} is not found')
        msg = bot.send_message(chat_id=chat_id, text=f'Город {city} не найден. Повторите ввод.')
        bot.register_next_step_handler(message=msg, callback=city_choice_keyboard)
    else:
        bot.send_message(chat_id=message.chat.id, text='Выберите город:', reply_markup=markup)


@logger.catch
def get_hotels_count(message: types.Message) -> None:
    """
    Функция, которая создает клавиатуру для уточнения необходимости выгрузки фотографий.
    Принимает от пользователя количество отелей для выгрузки.
    :param message: сообщение пользователя с количеством отелей.
    :return: None
    """
    try:
        if not 25 > int(message.text) > 0:
            logger.info(f'User {message.chat.id} chose wrong number of hotels.')
            msg = bot.send_message(chat_id=message.chat.id, text='Указано некорректное значение.\n'
                                                                 'Укажите от 1 до 25 отелей.')
            bot.register_next_step_handler(message=msg, callback=get_hotels_count)
            return
    except ValueError:
        msg = bot.send_message(chat_id=message.chat.id, text='Укажите количество цифрами.')
        bot.register_next_step_handler(message=msg, callback=get_hotels_count)
    else:
        logger.info(f'Ask user {message.chat.id} about hotel photo')
        chat_id = message.chat.id
        set_info(column='hotels_count', value=message.text, user_id=chat_id)
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(telebot.types.InlineKeyboardButton(text='Да', callback_data='Yes'))
        markup.add(telebot.types.InlineKeyboardButton(text='Нет', callback_data='No'))
        bot.send_message(chat_id=message.chat.id, text='Загрузить фото отеля?', reply_markup=markup)


@logger.catch
@bot.callback_query_handler(func=lambda call: True)
def reg_city_choice(call: types.CallbackQuery) -> None:
    """
    Функция. Обрабатывает ответ пользователя, введенной с клавиатуры телеграм бота.
    :param call: ответ на выбор населенного пункта для поиска, ответ вопрос о необходимости выгрузки фотографий.
    :return: None
    """
    if call.data == 'No':
        logger.info(f'User {call.from_user.id} choose request without photo.')
        bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
        set_info(column='photos_count', value=0, user_id=call.from_user.id)
        result(user_id=call.from_user.id)
    elif call.data == 'Yes':
        logger.info(f'User {call.from_user.id} choose request with photo.')
        bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
        msg = bot.send_message(chat_id=call.from_user.id, text='Укажите кол-во фотографий (не более 5).')
        bot.register_next_step_handler(message=msg, callback=add_photo)
    else:
        logger.info(f'User {call.from_user.id} choose city {call.data.split("|")[0]}')
        set_info(column='city_id', value=int(call.data.split('|')[1]), user_id=int(call.data.split('|')[2]))
        set_info(column='city_name', value=call.data.split('|')[0], user_id=int(call.data.split('|')[2]))
        bot.send_message(chat_id=call.from_user.id, text=call.data.split('|')[0])
        msg = bot.send_message(chat_id=call.from_user.id, text='Сколько отелей ищем (не более 25)?')
        bot.edit_message_reply_markup(chat_id=call.from_user.id, message_id=call.message.message_id)
        bot.register_next_step_handler(message=msg, callback=get_hotels_count)


@logger.catch
def add_photo(message: types.Message) -> None:
    """
    Функция. Принимает от пользователя количество фотографий.
    :param message сообщение пользователя с количеством фотографий отеля.
    :return None
    """
    try:
        if not 5 > int(message.text) > 0:
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


@logger.catch
def result(user_id) -> None:
    """
    Функция. Осуществляет вывод информации о найденных отелях и их фотографии.
    :param user_id: id пользователя, по чьему запросу будет осуществлен вывод данных.
    :return: None
    """
    info_from_bd = get_info(user_id=user_id)
    request_result = hotels_info_for_low_high_price(town_id=info_from_bd[2],
                                                    count_of_hotels=info_from_bd[4],
                                                    command=info_from_bd[1])
    if request_result is None:
        bot.send_message(chat_id=user_id, text='Не удается получить информацию с сайта.'
                                               'Повторите запрос позднее.')
        return

    bot.send_message(chat_id=user_id, text=f'Вот что удалось найти')

    for data in request_result:
        request_answer = f'Название отеля: {data.get("name")}\n'\
                         f'Адрес: {data.get("address")}\n' \
                         f'Расстояние от центра города: {data.get("distance")}\n' \
                         f'Цена: {data.get("cur_price")}'
        bot.send_message(chat_id=user_id, text=request_answer)
        if info_from_bd[5] != 0:
            photos_list = []
            photos = get_photo(hotel_id=data['id'])
            if request_result is None:
                bot.send_message(chat_id=user_id, text='Не удается получить информацию с сайта.'
                                                       'Повторите запрос позднее.')
                return

            for elem in photos[:info_from_bd[5]]:
                photos_list.append(types.InputMediaPhoto((elem['photo']).replace('{size}', 'z')))
            bot.send_media_group(chat_id=user_id, media=photos_list)
    bot.send_message(chat_id=user_id, text='Поиск завершен.')


if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True, interval=0)
        except Exception as e:
            logger.error(f'Exception: {e}')
            time.sleep(15)
