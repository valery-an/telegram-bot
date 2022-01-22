from decouple import config
import telebot


TOKEN = config('token')
RAPIDAPI_KEY = config('rapidapi_key')
bot = telebot.TeleBot(TOKEN)
help_text = 'Вы можете управлять мной с помощью следующих команд:\n' \
            '/lowprice — вывод самых дешёвых отелей в городе\n' \
            '/highprice — вывод самых дорогих отелей в городе\n' \
            '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n' \
            '/history — вывод истории поиска отелей'


@bot.message_handler(commands=['start', 'help'])
def start_handler(message):
    bot.send_message(message.chat.id, help_text)


bot.polling(none_stop=True, interval=0)
