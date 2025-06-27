import telebot
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "😼 Привет! Ты запустил MEOW×404 БОТА. Пиши команду или жди NFT-дропа.")

bot.polling()
