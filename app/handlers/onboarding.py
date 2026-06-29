"""
Онбординг: дисклеймер -> три раздельных согласия -> подтверждение 18+.
До прохождения всех обязательных шагов доступ к обычному диалогу с ботом
заблокирован (см. middleware-проверку в dialogue.py).
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.db.user_state import get_or_create_state, update_state
from app.legal_texts import (
    DISCLAIMER_TEXT,
    CONSENT_OFFER_TEXT,
    CONSENT_PERSONAL_DATA_TEXT,
    CONSENT_MARKETING_TEXT,
    AGE_CONFIRMATION_TEXT,
    AGE_REJECTED_TEXT,
    ONBOARDING_COMPLETE_TEXT,
    PRIVACY_POLICY_URL,
    PUBLIC_OFFER_URL,
)

router = Router()


def consents_keyboard(state) -> InlineKeyboardMarkup:
    def mark(value: bool) -> str:
        return "✅" if value else "⬜️"

    rows = [
        [InlineKeyboardButton(
            text=f"{mark(state.consent_offer)} Оферта и Пользовательское соглашение",
            callback_data="toggle_offer",
        )],
        [InlineKeyboardButton(
            text=f"{mark(state.consent_personal_data)} Обработка персональных данных",
            callback_data="toggle_personal_data",
        )],
        [InlineKeyboardButton(
            text=f"{mark(state.consent_marketing)} Рекламные рассылки (необязательно)",
            callback_data="toggle_marketing",
        )],
        [InlineKeyboardButton(text="📄 Документы на сайте", url=PRIVACY_POLICY_URL)],
    ]
    if state.consent_offer and state.consent_personal_data:
        rows.append([InlineKeyboardButton(text="Продолжить ➡️", callback_data="consents_done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def age_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мне есть 18 лет", callback_data="age_yes")],
        [InlineKeyboardButton(text="Мне нет 18 лет", callback_data="age_no")],
    ])


async def start_onboarding(message: Message):
    state = get_or_create_state(message.from_user.id)
    await message.answer(DISCLAIMER_TEXT)
    await message.answer(
        f"{CONSENT_OFFER_TEXT}\n\n{CONSENT_PERSONAL_DATA_TEXT}\n\n{CONSENT_MARKETING_TEXT}\n\n"
        "Отметь нужные пункты ниже:",
        reply_markup=consents_keyboard(state),
    )


@router.callback_query(F.data.in_({"toggle_offer", "toggle_personal_data", "toggle_marketing"}))
async def handle_consent_toggle(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = get_or_create_state(user_id)

    field_map = {
        "toggle_offer": "consent_offer",
        "toggle_personal_data": "consent_personal_data",
        "toggle_marketing": "consent_marketing",
    }
    field = field_map[callback.data]
    new_value = not getattr(state, field)
    update_state(user_id, **{field: new_value})

    state = get_or_create_state(user_id)
    await callback.message.edit_reply_markup(reply_markup=consents_keyboard(state))
    await callback.answer()


@router.callback_query(F.data == "consents_done")
async def handle_consents_done(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = get_or_create_state(user_id)

    if not (state.consent_offer and state.consent_personal_data):
        await callback.answer("Нужно принять оба обязательных пункта 🙏", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(AGE_CONFIRMATION_TEXT, reply_markup=age_keyboard())
    await callback.answer()


@router.callback_query(F.data == "age_yes")
async def handle_age_yes(callback: CallbackQuery):
    user_id = callback.from_user.id
    update_state(user_id, age_confirmed=True, onboarding_completed=True)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(ONBOARDING_COMPLETE_TEXT)
    await callback.answer()


@router.callback_query(F.data == "age_no")
async def handle_age_no(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(AGE_REJECTED_TEXT)
    await callback.answer()
