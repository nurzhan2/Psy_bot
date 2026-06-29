"""
Основной хендлер: принимает текстовое сообщение пользователя,
проверяет онбординг, лимит длины, кризисные признаки и флуд,
затем формирует ответ через LLM с таймаутом.

Логика вынесена в process_user_text(), чтобы её мог переиспользовать
хендлер голосовых сообщений (app/handlers/voice.py) после расшифровки
аудио в текст — весь остальной пайплайн (онбординг/лимиты/кризис/
антифлуд/LLM) при этом остаётся общим и не дублируется.
"""
import asyncio

from aiogram import Router, F
from aiogram.types import Message

from app.db.history import save_message, get_history
from app.db.user_state import is_fully_onboarded, increment_flood_counter, reset_flood_counter
from app.handlers.onboarding import start_onboarding
from app.handlers.subscription import require_active_subscription
from app.llm import get_assistant_reply
from app.prompts import (
    CRISIS_RESPONSE,
    MAX_MESSAGE_LENGTH,
    MESSAGE_TOO_LONG_RESPONSE,
    LLM_TIMEOUT_SECONDS,
    TIMEOUT_RESPONSE,
    FLOOD_THRESHOLD,
    FLOOD_RESPONSE,
)
from app.safety import is_crisis_message

router = Router()


async def process_user_text(message: Message, user_text: str, source: str = "text"):
    """
    Общий пайплайн обработки текста пользователя — вне зависимости от того,
    пришёл он напрямую текстом или был распознан из голосового сообщения.

    source: "text" | "voice" — пока используется только для возможного
    логирования/аналитики в будущем, на саму логику не влияет.
    """
    user_id = message.from_user.id

    # Доступ заблокирован до прохождения дисклеймера и согласий
    if not is_fully_onboarded(user_id):
        await start_onboarding(message)
        return

    # Доступ за подпиской (если платежи включены). Если выключены — пропускает всех.
    if not await require_active_subscription(message):
        return

    # Лимит длины сообщения — защита от спама и перегрузки контекста
    if len(user_text) > MAX_MESSAGE_LENGTH:
        await message.answer(MESSAGE_TOO_LONG_RESPONSE)
        return

    # Приоритет №1 — проверка на кризис, выше любой другой логики
    if is_crisis_message(user_text):
        await message.answer(CRISIS_RESPONSE)
        save_message(user_id, "user", user_text)
        save_message(user_id, "assistant", CRISIS_RESPONSE)
        reset_flood_counter(user_id)
        return

    # Антифлуд: считаем подряд идущие сообщения без явного перехода к практике.
    # Простая эвристика, финальное решение остаётся за самой моделью через промпт —
    # здесь только мягкая защита на случай очень долгого разговора без фокуса.
    flood_count = increment_flood_counter(user_id)
    if flood_count > 0 and flood_count % FLOOD_THRESHOLD == 0:
        await message.answer(FLOOD_RESPONSE)
        save_message(user_id, "user", user_text)
        save_message(user_id, "assistant", FLOOD_RESPONSE)
        return

    save_message(user_id, "user", user_text)
    history = get_history(user_id, limit=12)

    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        reply = await asyncio.wait_for(
            asyncio.to_thread(get_assistant_reply, user_text, history[:-1], user_id),
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        reply = TIMEOUT_RESPONSE
    except Exception:
        reply = (
            "Кажется, что-то пошло не так на технической стороне. "
            "Попробуй написать ещё раз чуть позже 🙏"
        )
        # В реальном проекте здесь стоит добавить логирование ошибки (logging.exception)

    await message.answer(reply)
    save_message(user_id, "assistant", reply)


@router.message(F.text)
async def handle_text(message: Message):
    await process_user_text(message, message.text, source="text")


@router.message()
async def handle_unsupported(message: Message):
    """
    Любой другой тип сообщения (фото, видео, документ, стикер, геолокация и т.п.) —
    бот по требованию клиентки работает только с текстом и голосовыми (которые
    тоже превращаются в текст), остальное вежливо отклоняем.
    """
    await message.answer(
        "Я работаю только с текстовыми и голосовыми сообщениями. "
        "Расскажи, пожалуйста, словами, что тебя сейчас беспокоит 🙏"
    )
