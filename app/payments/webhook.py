"""
Приём вебхуков ЮKassa (aiohttp) — блок 1.

Обрабатываем первый платёж (kind=initial): при payment.succeeded активируем
подписку и сохраняем payment_method_id для будущих автосписаний.

Подлинность вебхука проверяем перезапросом платежа через API (fetch_payment).
URL в кабинете ЮKassa: https://<домен>/yookassa
"""
import asyncio
import logging

from aiohttp import web
from aiogram import Bot

from app.db import subscriptions
from app.payments import texts
from app.payments.yookassa_client import fetch_payment
from config import SUBSCRIPTION_PERIOD_DAYS, SUBSCRIPTION_PLAN_NAME, WEBHOOK_PATH

log = logging.getLogger(__name__)


async def _handle(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400)

    event = body.get("event")
    obj = body.get("object") or {}
    payment_id = obj.get("id")
    if not payment_id:
        return web.Response(status=200)

    try:
        payment = await asyncio.to_thread(fetch_payment, payment_id)
    except Exception:
        log.exception("Не удалось перезапросить платёж %s", payment_id)
        return web.Response(status=200)

    metadata = getattr(payment, "metadata", None) or {}
    user_id_raw = metadata.get("user_id")
    kind = metadata.get("kind", "initial")
    if not user_id_raw:
        return web.Response(status=200)
    user_id = int(user_id_raw)

    subscriptions.record_payment(payment.id, user_id, payment.amount.value,
                                 payment.status, is_recurring=(kind == "recurring"))

    if event == "payment.succeeded" and payment.status == "succeeded":
        pm = getattr(payment, "payment_method", None)
        pm_id = getattr(pm, "id", None) if pm else None
        saved = getattr(pm, "saved", False) if pm else False

        subscriptions.activate(
            user_id=user_id,
            payment_method_id=pm_id if saved else None,
            period_days=SUBSCRIPTION_PERIOD_DAYS,
            plan=SUBSCRIPTION_PLAN_NAME,
        )
        try:
            await bot.send_message(user_id, texts.ACTIVATED)
        except Exception:
            log.warning("Не удалось отправить подтверждение пользователю %s", user_id)

    return web.Response(status=200)


def setup_webhook_routes(app: web.Application):
    app.router.add_post(WEBHOOK_PATH, _handle)
