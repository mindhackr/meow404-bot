from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from app.db import init_database
from app.handlers import admin as admin_handlers
from app.handlers import user as user_handlers


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.MARKDOWN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    await init_database()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
