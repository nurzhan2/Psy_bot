"""
Хендлеры команд: /start и /reset.
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db.history import clear_history
from app.db.user_state import is_fully_onboarded
from app.handlers.onboarding import start_onboarding

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    if is_fully_onboarded(message.from_user.id):
        await message.answer(
            "С возвращением! Расскажи, что тебя сейчас беспокоит — и мы разберём это вместе."
        )
        return
    await start_onboarding(message)


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    clear_history(message.from_user.id)
    await message.answer("Хорошо, начнём сначала. Расскажи, что тебя сейчас волнует?")
