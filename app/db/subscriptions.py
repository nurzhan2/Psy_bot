"""
Хранилище состояния подписок (SQLAlchemy, та же БД, что и история диалогов).
Синхронное — в том же стиле, что history.py / user_state.py.

Статусы:
    none      — ещё не оплачивал
    active    — доступ открыт, период не закончился
    past_due  — автосписание не прошло (грейс до конца периода)
    canceled  — автопродление выключено пользователем; доступ до конца периода
    expired   — период закончился
"""
import datetime as dt
from typing import List, Optional

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DB_PATH

Base = declarative_base()


class Subscription(Base):
    __tablename__ = "subscriptions"

    user_id = Column(Integer, primary_key=True)
    status = Column(String(20), default="none", nullable=False)
    plan = Column(String(120))
    payment_method_id = Column(String(120))           # сохранённый способ оплаты для рекуррента
    current_period_end = Column(DateTime)
    next_charge_at = Column(DateTime)
    auto_renew = Column(Boolean, default=True)
    renewal_notice_sent_for = Column(DateTime)        # для какого period_end уже слали уведомление
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(80), primary_key=True)         # id платежа ЮKassa
    user_id = Column(Integer, index=True)
    amount = Column(String(20))
    status = Column(String(20))
    is_recurring = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_subscriptions_db():
    Base.metadata.create_all(engine)


def _now() -> dt.datetime:
    return dt.datetime.utcnow()


def get(user_id: int) -> Optional[Subscription]:
    with SessionLocal() as session:
        sub = session.get(Subscription, user_id)
        if sub is not None:
            session.expunge(sub)
        return sub


def is_active(user_id: int) -> bool:
    sub = get(user_id)
    if not sub or sub.status not in ("active", "canceled", "past_due"):
        return False
    return bool(sub.current_period_end and sub.current_period_end > _now())


def activate(user_id: int, payment_method_id: Optional[str], period_days: int, plan: str):
    """Активирует/продлевает подписку. Продление считается от конца текущего периода."""
    with SessionLocal() as session:
        sub = session.get(Subscription, user_id)
        now = _now()
        base = now
        if sub and sub.current_period_end and sub.current_period_end > now:
            base = sub.current_period_end
        new_end = base + dt.timedelta(days=period_days)

        if sub is None:
            sub = Subscription(user_id=user_id, created_at=now)
            session.add(sub)

        sub.status = "active"
        sub.plan = plan
        if payment_method_id:
            sub.payment_method_id = payment_method_id
        sub.current_period_end = new_end
        sub.next_charge_at = new_end
        sub.auto_renew = True
        sub.renewal_notice_sent_for = None
        sub.updated_at = now
        session.commit()


def cancel_auto_renew(user_id: int) -> bool:
    """Мгновенно выключает автопродление. Доступ остаётся до конца периода."""
    with SessionLocal() as session:
        sub = session.get(Subscription, user_id)
        if not sub or sub.status not in ("active", "past_due"):
            return False
        sub.status = "canceled"
        sub.auto_renew = False
        sub.next_charge_at = None
        sub.updated_at = _now()
        session.commit()
        return True


def set_status(user_id: int, status: str):
    with SessionLocal() as session:
        sub = session.get(Subscription, user_id)
        if sub:
            sub.status = status
            sub.updated_at = _now()
            session.commit()


def due_for_charge() -> List[Subscription]:
    with SessionLocal() as session:
        rows = (
            session.query(Subscription)
            .filter(
                Subscription.auto_renew.is_(True),
                Subscription.payment_method_id.isnot(None),
                Subscription.next_charge_at.isnot(None),
                Subscription.next_charge_at <= _now(),
            )
            .all()
        )
        for r in rows:
            session.expunge(r)
        return rows


def due_for_notice(days_before: int) -> List[Subscription]:
    threshold = _now() + dt.timedelta(days=days_before)
    with SessionLocal() as session:
        rows = (
            session.query(Subscription)
            .filter(
                Subscription.auto_renew.is_(True),
                Subscription.status == "active",
                Subscription.next_charge_at.isnot(None),
                Subscription.next_charge_at <= threshold,
            )
            .all()
        )
        result = []
        for r in rows:
            # ещё не уведомляли про этот конкретный period_end
            if r.renewal_notice_sent_for != r.current_period_end:
                session.expunge(r)
                result.append(r)
        return result


def mark_notice_sent(user_id: int):
    with SessionLocal() as session:
        sub = session.get(Subscription, user_id)
        if sub:
            sub.renewal_notice_sent_for = sub.current_period_end
            sub.updated_at = _now()
            session.commit()


def record_payment(payment_id: str, user_id: int, amount: str, status: str, is_recurring: bool):
    with SessionLocal() as session:
        p = session.get(Payment, payment_id)
        if p is None:
            p = Payment(id=payment_id, user_id=user_id, amount=str(amount),
                        status=status, is_recurring=is_recurring, created_at=_now())
            session.add(p)
        else:
            p.status = status
        session.commit()
