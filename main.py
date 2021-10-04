import telebot
import os
from dotenv import load_dotenv

load_dotenv()
bot = telebot.TeleBot(os.getenv('TOKEN'))


@bot.message_handler(commands=['hello_world'])
def send_hello(message: telebot.types.Message) -> None:
    bot.reply_to(message, "Привет! Меня зовут HotelsAPIbot.")


@bot.message_handler(content_types=['text'])
def get_text_messages(message: telebot.types.Message):
    if message.text == 'Привет':
        bot.send_message(message.from_user.id, "Привет! Меня зовут HotelsAPIbot.")
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Напиши 'Привет' или /hello_world")


bot.polling(none_stop=True, interval=0)
