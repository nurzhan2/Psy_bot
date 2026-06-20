"""
Хранение истории диалога по каждому пользователю (SQLite через SQLAlchemy).
Нужно, чтобы GPT видел контекст последних сообщений внутри сессии
и мог проходить по шагам алгоритма (заземление → уточнение → причина → практика).
"""
import datetime as dt
from typing import List

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DB_PATH

Base = declarative_base()


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    role = Column(String(20), nullable=False)  # "user" или "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def save_message(user_id: int, role: str, content: str):
    with SessionLocal() as session:
        msg = Message(user_id=user_id, role=role, content=content)
        session.add(msg)
        session.commit()


def get_history(user_id: int, limit: int = 12) -> List[dict]:
    """Возвращает последние `limit` сообщений пользователя в хронологическом порядке."""
    with SessionLocal() as session:
        rows = (
            session.query(Message)
            .filter(Message.user_id == user_id)
            .order_by(Message.id.desc())
            .limit(limit)
            .all()
        )
    rows.reverse()
    return [{"role": r.role, "content": r.content} for r in rows]


def clear_history(user_id: int):
    with SessionLocal() as session:
        session.query(Message).filter(Message.user_id == user_id).delete()
        session.commit()
