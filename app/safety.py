"""
Грубый, но быстрый фильтр на кризисные слова (суицид/самоповреждение).
Это первая линия защиты — срабатывает до похода в GPT, чтобы исключить
любой риск, что модель "забудет" про табу из системного промпта.
"""
from app.prompts import CRISIS_KEYWORDS


def is_crisis_message(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in CRISIS_KEYWORDS)
