from decouple import config
import telebot
import lowprice
import help


TOKEN = config('token')
RAPIDAPI_KEY = config('rapidapi_key')
bot = telebot.TeleBot(TOKEN)

help.start_handler()
lowprice.start()


bot.polling(none_stop=True, interval=0)
