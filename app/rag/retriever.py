"""
Retriever объединяет результаты поиска из personal и books хранилищ,
с приоритетом personal (как просила клиентка: "золотой фонд" — её личные
материалы — важнее, литература — теоретическая опора).
"""
from typing import List

from app.rag.vector_store import VectorStore
from config import TOP_K_PERSONAL, TOP_K_BOOKS

_personal_store = VectorStore("personal")
_books_store = VectorStore("books")

_personal_loaded = _personal_store.load()
_books_loaded = _books_store.load()


def get_context(query: str) -> str:
    """
    Возвращает текстовый контекст для подстановки в промпт.
    Личные материалы идут первыми и явно помечены как основной источник.
    """
    parts = []

    if _personal_loaded:
        personal_results = _personal_store.search(query, TOP_K_PERSONAL)
        if personal_results:
            parts.append("### Личные материалы автора методики (основной источник):")
            for chunk, score in personal_results:
                parts.append(f"- [{chunk.source}] {chunk.text}")

    if _books_loaded:
        book_results = _books_store.search(query, TOP_K_BOOKS)
        if book_results:
            parts.append("\n### Дополнительный теоретический контекст (если основного источника недостаточно):")
            for chunk, score in book_results:
                parts.append(f"- [{chunk.source}] {chunk.text}")

    if not parts:
        return ""

    return "\n".join(parts)


def reload_indexes():
    """Вызывать после пересборки индексов (app.rag.build_index), чтобы подхватить изменения без перезапуска бота."""
    global _personal_loaded, _books_loaded
    _personal_loaded = _personal_store.load()
    _books_loaded = _books_store.load()
