"""
Сборка финального запроса к OpenAI: системный промпт + RAG-контекст + история диалога.

Доработка (блок 4): модель выбирается по сложности запроса (choose_model),
история обрезается под бюджет контекста (trim_history), стоимость каждого
запроса логируется (log_usage).
"""
import logging
from typing import List, Optional

from openai import OpenAI

from config import OPENAI_API_KEY
from app.prompts import SYSTEM_PROMPT
from app.rag.retriever import get_context
from app import llm_optimize

log = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)


def build_messages(user_text: str, history: List[dict]) -> List[dict]:
    context = get_context(user_text)

    system_content = SYSTEM_PROMPT
    if context:
        system_content += (
            "\n\nНиже — релевантные материалы из базы знаний. Используй их как опору, "
            "но не цитируй большими кусками, пересказывай своими словами:\n\n" + context
        )

    # Обрезаем историю под бюджет контекста (системный промпт сюда не входит).
    trimmed = llm_optimize.trim_history(history)

    messages = [{"role": "system", "content": system_content}]
    messages.extend(trimmed)
    messages.append({"role": "user", "content": user_text})
    return messages


def get_assistant_reply(user_text: str, history: List[dict], user_id: Optional[int] = None) -> str:
    messages = build_messages(user_text, history)
    model = llm_optimize.choose_model(user_text, history_len=len(history))

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=700,
    )

    # Учёт стоимости: берём фактические токены из usage, если они есть.
    try:
        usage = getattr(response, "usage", None)
        if usage:
            llm_optimize.log_usage(model, usage.prompt_tokens, usage.completion_tokens, user_id)
    except Exception:
        log.debug("Не удалось залогировать стоимость запроса", exc_info=True)

    return response.choices[0].message.content
