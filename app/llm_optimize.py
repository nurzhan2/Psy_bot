"""
Слой оптимизации расходов на OpenAI (cost-aware).

Рычаги экономии:
  1. Роутинг моделей: простое -> дешёвая модель, сложное -> сильная.
  2. Обрезка контекста: в запрос уходит хвост диалога, а не вся история.
  3. Кэш эмбеддингов: при пересборке индекса не переэмбеддим неизменившиеся куски.
  4. Учёт стоимости: каждый запрос логируется с оценкой токенов и цены.

Сам сетевых вызовов не делает — помогает llm.py и rag/vector_store.py.
Все операции с кэшем защищены try/except: сбой кэша не должен ломать бота.
"""
import hashlib
import json
import logging
import os
import sqlite3
from contextlib import closing
from typing import List, Optional

from config import (
    DB_PATH,
    MODEL_SIMPLE,
    MODEL_COMPLEX,
    MODEL_PRICES_PER_1M,
    CONTEXT_MAX_MESSAGES,
    CONTEXT_MAX_CHARS,
    COMPLEXITY_CHAR_THRESHOLD,
)

log = logging.getLogger(__name__)

_COMPLEX_HINTS = (
    "почему", "разбер", "проанализир", "связь", "сценар", "родов",
    "карм", "глубин", "противореч", "запутал", "не понимаю почему",
)

_cache_ready = False


# ---------- 1. Роутинг моделей ----------

def choose_model(user_text: str, history_len: int = 0) -> str:
    text = (user_text or "").lower().strip()
    if len(text) >= COMPLEXITY_CHAR_THRESHOLD:
        return MODEL_COMPLEX
    if any(h in text for h in _COMPLEX_HINTS):
        return MODEL_COMPLEX
    if history_len >= CONTEXT_MAX_MESSAGES:
        return MODEL_COMPLEX
    return MODEL_SIMPLE


# ---------- 2. Обрезка контекста ----------

def trim_history(messages: List[dict], max_messages: Optional[int] = None,
                 max_chars: Optional[int] = None) -> List[dict]:
    max_messages = max_messages or CONTEXT_MAX_MESSAGES
    max_chars = max_chars or CONTEXT_MAX_CHARS

    tail = messages[-max_messages:]
    total = 0
    kept: List[dict] = []
    for msg in reversed(tail):
        c = len(msg.get("content", "") or "")
        if total + c > max_chars and kept:
            break
        kept.append(msg)
        total += c
    kept.reverse()
    return kept


# ---------- 3. Кэш эмбеддингов ----------

def _connect() -> sqlite3.Connection:
    d = os.path.dirname(DB_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_embedding_cache() -> None:
    global _cache_ready
    try:
        with closing(_connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    content_hash TEXT PRIMARY KEY,
                    model        TEXT NOT NULL,
                    vector       TEXT NOT NULL
                );
                """
            )
        _cache_ready = True
    except Exception:
        log.exception("Не удалось инициализировать кэш эмбеддингов")


def _ensure_cache():
    if not _cache_ready:
        init_embedding_cache()


def _hash(text: str, model: str) -> str:
    return hashlib.sha256(f"{model}:{text}".encode("utf-8")).hexdigest()


def get_cached_embedding(text: str, model: str) -> Optional[list]:
    try:
        _ensure_cache()
        with closing(_connect()) as conn:
            cur = conn.execute("SELECT vector FROM embedding_cache WHERE content_hash=?",
                               (_hash(text, model),))
            row = cur.fetchone()
        return json.loads(row[0]) if row else None
    except Exception:
        return None


def store_embedding(text: str, model: str, vector: list) -> None:
    try:
        _ensure_cache()
        with closing(_connect()) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO embedding_cache (content_hash, model, vector) VALUES (?,?,?)",
                (_hash(text, model), model, json.dumps(list(vector))),
            )
    except Exception:
        pass


# ---------- 4. Учёт стоимости ----------

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("o200k_base")
        return len(enc.encode(text or ""))
    except Exception:
        return max(1, len(text or "") // 4)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    price = MODEL_PRICES_PER_1M.get(model)
    if not price:
        return 0.0
    return (prompt_tokens * price["in"] + completion_tokens * price["out"]) / 1_000_000


def log_usage(model: str, prompt_tokens: int, completion_tokens: int, user_id: Optional[int] = None) -> float:
    cost = estimate_cost(model, prompt_tokens, completion_tokens)
    log.info("LLM usage | user=%s | model=%s | in=%d out=%d | ~$%.5f",
             user_id, model, prompt_tokens, completion_tokens, cost)
    return cost
