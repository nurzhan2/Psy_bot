"""
Хранение состояния согласий пользователя и счётчика сообщений для антифлуд-логики.
Отдельная таблица от истории диалогов (app/db/history.py), потому что это не
терапевтический контент, а технические/юридические флаги.
"""
import datetime as dt

from sqlalchemy import create_engine, Column, Integer, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DB_PATH

Base = declarative_base()


class UserState(Base):
    __tablename__ = "user_state"

    user_id = Column(Integer, primary_key=True)

    # Три отдельных согласия — нельзя объединять в одну галочку (152-ФЗ, ст. 9)
    consent_offer = Column(Boolean, default=False)         # оферта + пользовательское соглашение (обязательное)
    consent_personal_data = Column(Boolean, default=False)  # обработка перс. данных (обязательное)
    consent_marketing = Column(Boolean, default=False)       # рекламная рассылка (необязательное)

    # Возрастное подтверждение 18+
    age_confirmed = Column(Boolean, default=False)

    # Антифлуд: считаем сообщения с момента последнего "заземления" к запросу
    messages_since_focus = Column(Integer, default=0)
    last_message_at = Column(DateTime, default=dt.datetime.utcnow)

    onboarding_completed = Column(Boolean, default=False)


engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_state_db():
    Base.metadata.create_all(engine)


def get_or_create_state(user_id: int) -> UserState:
    with SessionLocal() as session:
        state = session.get(UserState, user_id)
        if state is None:
            state = UserState(user_id=user_id)
            session.add(state)
            session.commit()
            session.refresh(state)
        # detach для использования вне сессии
        session.expunge(state)
        return state


def update_state(user_id: int, **fields):
    with SessionLocal() as session:
        state = session.get(UserState, user_id)
        if state is None:
            state = UserState(user_id=user_id)
            session.add(state)
        for key, value in fields.items():
            setattr(state, key, value)
        session.commit()


def is_fully_onboarded(user_id: int) -> bool:
    state = get_or_create_state(user_id)
    return bool(
        state.consent_offer
        and state.consent_personal_data
        and state.age_confirmed
        and state.onboarding_completed
    )


def increment_flood_counter(user_id: int) -> int:
    with SessionLocal() as session:
        state = session.get(UserState, user_id)
        if state is None:
            state = UserState(user_id=user_id, messages_since_focus=1)
            session.add(state)
        else:
            state.messages_since_focus = (state.messages_since_focus or 0) + 1
        state.last_message_at = dt.datetime.utcnow()
        session.commit()
        return state.messages_since_focus


def reset_flood_counter(user_id: int):
    update_state(user_id, messages_since_focus=0)
