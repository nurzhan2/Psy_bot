"""
Точка входа в приложение. Запуск:
  python main.py
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.logging_setup import setup_logging

setup_logging()

from config import BOT_TOKEN, PAYMENTS_ENABLED, WEBHOOK_HOST, WEBHOOK_PORT
from app.db.history import init_db
from app.db.user_state import init_state_db
from app.db.subscriptions import init_subscriptions_db
from app.llm_optimize import init_embedding_cache
from app.handlers import commands, onboarding, dialogue, voice, subscription

log = logging.getLogger(__name__)


async def main():
    # Инициализация всех таблиц (одна БД, разные таблицы)
    init_db()
    init_state_db()
    init_subscriptions_db()
    init_embedding_cache()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Порядок важен: подписка раньше dialogue, чтобы её команды/колбэки
    # перехватывались до catch-all хендлера диалога.
    dp.include_router(commands.router)
    dp.include_router(onboarding.router)
    dp.include_router(subscription.router)
    dp.include_router(voice.router)
    dp.include_router(dialogue.router)

    runner = None
    if PAYMENTS_ENABLED:
        # aiohttp-сервер для вебхуков ЮKassa (это НЕ вебхук Telegram).
        from aiohttp import web
        from app.payments.webhook import setup_webhook_routes
        from app.payments.scheduler import run_scheduler

        web_app = web.Application()
        web_app["bot"] = bot
        setup_webhook_routes(web_app)
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, WEBHOOK_HOST, WEBHOOK_PORT)
        await site.start()
        log.info("Вебхук ЮKassa слушает %s:%s", WEBHOOK_HOST, WEBHOOK_PORT)

        asyncio.create_task(run_scheduler(bot))
    else:
        log.warning("Платежи выключены (ключи ЮKassa не заданы) — бот работает без подписки.")

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        if runner is not None:
            await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
