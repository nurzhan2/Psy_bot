"""
Сборка финального запроса к OpenAI: системный промпт + RAG-контекст + история диалога.
"""
from typing import List
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from app.prompts import SYSTEM_PROMPT
from app.rag.retriever import get_context

client = OpenAI(api_key=OPENAI_API_KEY)


def build_messages(user_text: str, history: List[dict]) -> List[dict]:
    context = get_context(user_text)

    system_content = SYSTEM_PROMPT
    if context:
        system_content += (
            "\n\nНиже — релевантные материалы из базы знаний. Используй их как опору, "
            "но не цитируй большими кусками, пересказывай своими словами:\n\n" + context
        )

    messages = [{"role": "system", "content": system_content}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages


def get_assistant_reply(user_text: str, history: List[dict]) -> str:
    messages = build_messages(user_text, history)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=700,
    )
    return response.choices[0].message.content
