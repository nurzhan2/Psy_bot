"""
Точка входа в приложение. Запуск:
  python main.py
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from app.db.history import init_db
from app.db.user_state import init_state_db
from app.handlers import commands, onboarding, dialogue, voice


async def main():
    logging.basicConfig(level=logging.INFO)

    init_db()
    init_state_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(commands.router)
    dp.include_router(onboarding.router)
    dp.include_router(voice.router)
    dp.include_router(dialogue.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
