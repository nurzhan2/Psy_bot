"""
Фоновый планировщик подписок (блок 1).

Раз в SCHEDULER_INTERVAL_SECONDS:
  1) Уведомление за RENEWAL_NOTICE_DAYS дней до автосписания (формулировка — по ТЗ).
  2) Рекуррентные списания по наступившему сроку. Успех — продлеваем период,
     неудача — статус past_due + сообщение пользователю.
"""
import asyncio
import logging

from aiogram import Bot

from app.db import subscriptions
from app.payments import texts
from app.payments.yookassa_client import charge_recurring
from config import (
    RENEWAL_NOTICE_DAYS,
    SUBSCRIPTION_PERIOD_DAYS,
    SUBSCRIPTION_PLAN_NAME,
    SCHEDULER_INTERVAL_SECONDS,
)

log = logging.getLogger(__name__)


async def _send_notices(bot: Bot):
    for sub in subscriptions.due_for_notice(RENEWAL_NOTICE_DAYS):
        try:
            await bot.send_message(sub.user_id, texts.renewal_notice())
            subscriptions.mark_notice_sent(sub.user_id)
        except Exception:
            log.warning("Не удалось отправить уведомление о продлении: %s", sub.user_id)


async def _charge_due(bot: Bot):
    for sub in subscriptions.due_for_charge():
        user_id = sub.user_id
        pm_id = sub.payment_method_id
        try:
            payment = await asyncio.to_thread(charge_recurring, user_id, pm_id)
            subscriptions.record_payment(payment.id, user_id, payment.amount.value,
                                         payment.status, is_recurring=True)
            if payment.status == "succeeded":
                subscriptions.activate(user_id=user_id, payment_method_id=pm_id,
                                       period_days=SUBSCRIPTION_PERIOD_DAYS,
                                       plan=SUBSCRIPTION_PLAN_NAME)
                log.info("Подписка продлена: %s", user_id)
            else:
                subscriptions.set_status(user_id, "past_due")
                await bot.send_message(user_id, texts.CHARGE_FAILED)
        except Exception:
            log.exception("Ошибка автосписания для %s", user_id)
            subscriptions.set_status(user_id, "past_due")
            try:
                await bot.send_message(user_id, texts.CHARGE_FAILED)
            except Exception:
                pass


async def run_scheduler(bot: Bot):
    log.info("Планировщик подписок запущен")
    while True:
        try:
            await _send_notices(bot)
            await _charge_due(bot)
        except Exception:
            log.exception("Сбой в цикле планировщика")
        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)
