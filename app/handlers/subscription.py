"""
Хендлеры подписки и «калитка» доступа (блок 1).

Подключение в main.py:
    from app.handlers import subscription
    dp.include_router(subscription.router)   # ДО dialogue.router

«Калитка» — require_active_subscription(message): зовётся в process_user_text
(app/handlers/dialogue.py) после онбординга и до обращения к GPT.
Если PAYMENTS_ENABLED=False (ключи ЮKassa не заданы) — калитка пропускает всех.
"""
import asyncio
import logging

from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.db import subscriptions
from app.payments import texts
from config import PAYMENTS_ENABLED

log = logging.getLogger(__name__)
router = Router()


def _paywall_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.PAY_BUTTON, callback_data="sub:pay")],
        [InlineKeyboardButton(text=texts.MANAGE_BUTTON, callback_data="sub:status")],
    ])


def _manage_keyboard(auto_renew: bool) -> InlineKeyboardMarkup:
    rows = []
    if auto_renew:
        rows.append([InlineKeyboardButton(text=texts.CANCEL_BUTTON, callback_data="sub:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_paywall(bot: Bot, chat_id: int):
    await bot.send_message(chat_id, texts.PAYWALL, reply_markup=_paywall_keyboard())


async def require_active_subscription(message: Message) -> bool:
    """True — доступ есть; False — paywall показан, диалог не продолжаем."""
    if not PAYMENTS_ENABLED:
        return True  # платежи не настроены — доступ открыт (режим теста)
    if subscriptions.is_active(message.from_user.id):
        return True
    await show_paywall(message.bot, message.chat.id)
    return False


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    if not PAYMENTS_ENABLED:
        await message.answer("Оплата подписки сейчас не подключена.")
        return
    if subscriptions.is_active(message.from_user.id):
        await _send_status(message.bot, message.from_user.id, message.chat.id)
    else:
        await show_paywall(message.bot, message.chat.id)


@router.callback_query(F.data == "sub:pay")
async def on_pay(callback: CallbackQuery):
    if not PAYMENTS_ENABLED:
        await callback.answer("Оплата сейчас недоступна.", show_alert=True)
        return
    user_id = callback.from_user.id
    try:
        from app.payments.yookassa_client import create_initial_payment
        payment = await asyncio.to_thread(create_initial_payment, user_id)
        url = payment.confirmation.confirmation_url
        subscriptions.record_payment(payment.id, user_id, payment.amount.value,
                                     payment.status, is_recurring=False)
    except Exception:
        log.exception("Не удалось создать платёж для %s", user_id)
        await callback.answer("Не удалось создать платёж, попробуйте позже.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Перейти к оплате", url=url)]])
    await callback.message.answer(texts.PAY_LINK_MESSAGE, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "sub:status")
async def on_status(callback: CallbackQuery):
    await _send_status(callback.bot, callback.from_user.id, callback.message.chat.id)
    await callback.answer()


@router.callback_query(F.data == "sub:cancel")
async def on_cancel(callback: CallbackQuery):
    canceled = subscriptions.cancel_auto_renew(callback.from_user.id)
    await callback.message.answer(texts.CANCELED if canceled else texts.CANCEL_NOTHING)
    await callback.answer()


async def _send_status(bot: Bot, user_id: int, chat_id: int):
    sub = subscriptions.get(user_id)
    if not sub or not subscriptions.is_active(user_id):
        await bot.send_message(chat_id, texts.status_none(), reply_markup=_paywall_keyboard())
        return
    end_str = sub.current_period_end.strftime("%d.%m.%Y") if sub.current_period_end else "—"
    auto_renew = bool(sub.auto_renew)
    await bot.send_message(chat_id, texts.status_active(end_str, auto_renew),
                           reply_markup=_manage_keyboard(auto_renew))
