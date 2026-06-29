"""
Тонкая обёртка над ЮKassa SDK.

Два сценария:
  1) create_initial_payment — первый платёж пользователя. Просим ЮKassa
     сохранить способ оплаты (save_payment_method=True), чтобы потом списывать
     рекуррентно. Возвращаем ссылку на оплату (confirmation_url).
  2) charge_recurring — автосписание по сохранённому payment_method_id, без
     участия пользователя.

Вызовы SDK блокирующие (под капотом requests), поэтому из async-кода зовите
их через asyncio.to_thread — см. scheduler.py и handlers/subscription.py.
"""
from __future__ import annotations

import uuid
from typing import Optional

from yookassa import Configuration, Payment

from config import (
    YOOKASSA_SHOP_ID,
    YOOKASSA_SECRET_KEY,
    SUBSCRIPTION_PRICE_RUB,
    SUBSCRIPTION_RETURN_URL,
    SUBSCRIPTION_PLAN_NAME,
)

Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


def _amount() -> dict:
    return {"value": f"{float(SUBSCRIPTION_PRICE_RUB):.2f}", "currency": "RUB"}


def create_initial_payment(user_id: int, return_url: Optional[str] = None) -> Payment:
    """
    Первый платёж. После успешной оплаты ЮKassa пришлёт вебхук payment.succeeded,
    в объекте которого будет payment_method.id (сохранённый способ) — его кладём
    в подписку для будущих автосписаний.
    """
    idempotence_key = str(uuid.uuid4())
    payment = Payment.create(
        {
            "amount": _amount(),
            "capture": True,
            "save_payment_method": True,
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or SUBSCRIPTION_RETURN_URL,
            },
            "description": f"{SUBSCRIPTION_PLAN_NAME}. Пользователь {user_id}",
            "metadata": {"user_id": str(user_id), "kind": "initial"},
            # ВНИМАНИЕ про 54-ФЗ: если у магазина включена фискализация, ЮKassa
            # потребует объект receipt с контактом покупателя и составом чека.
            # Тогда раскомментируйте и заполните под свою номенклатуру:
            # "receipt": {
            #     "customer": {"email": "<email-или-телефон-покупателя>"},
            #     "items": [{
            #         "description": SUBSCRIPTION_PLAN_NAME,
            #         "quantity": "1.00",
            #         "amount": _amount(),
            #         "vat_code": 1,
            #         "payment_mode": "full_payment",
            #         "payment_subject": "service",
            #     }],
            # },
        },
        idempotence_key,
    )
    return payment


def charge_recurring(user_id: int, payment_method_id: str) -> Payment:
    """Автосписание по сохранённому способу оплаты. Подтверждение не требуется."""
    idempotence_key = str(uuid.uuid4())
    payment = Payment.create(
        {
            "amount": _amount(),
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": f"Продление: {SUBSCRIPTION_PLAN_NAME}. Пользователь {user_id}",
            "metadata": {"user_id": str(user_id), "kind": "recurring"},
        },
        idempotence_key,
    )
    return payment


def fetch_payment(payment_id: str) -> Payment:
    """Перезапрос платежа по id — используем для проверки подлинности вебхука."""
    return Payment.find_one(payment_id)
