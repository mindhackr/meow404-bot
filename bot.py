import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.reply("🐾 Добро пожаловать в MEOW×404.
Нажми СТАРТ — и фарм начнётся.")

@dp.message_handler(commands=["help"])
async def send_help(message: types.Message):
    await message.reply("ℹ️ Команды:
/start — вход
/help — помощь
/rank — твой хвостовый ранг (в разработке)")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
