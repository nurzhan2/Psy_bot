"""
Анализ стиля письма по постам из канала.

Идея: не копировать тексты постов как есть в системный промпт (это и дорого
по токенам, и не нужно), а один раз прогнать выборку постов через GPT с
запросом описать стиль — и сохранить ТОЛЬКО описание стиля (структура речи,
характерные обороты, длина предложений, эмоциональная окраска), а не сами
тексты. Это описание потом руками вставляется в app/prompts.py.

Запуск:
  python tools/analyze_style.py personal_materials/channel_posts.txt
"""
import sys
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

STYLE_ANALYSIS_PROMPT = """\
Ниже приведены примеры постов автора из её Telegram-канала (психолог,
интегративный подход). Проанализируй ТОЛЬКО стиль речи — не пересказывай
содержание постов и не используй цитаты длиннее нескольких слов.

Дай краткое структурированное описание стиля по пунктам:
1. Длина и ритм предложений (короткие/длинные, рубленые/плавные)
2. Обращение к читателю (на "ты"/"вы", прямое/мягкое)
3. Характерные слова-маркеры и обороты речи (без цитат, просто опиши, какие
   слова она использует часто — например, "часто использует метафоры пути",
   "обращается риторическими вопросами")
4. Эмоциональная окраска (тёплая/строгая/директивная/поддерживающая)
5. Структура поста (есть ли вступление-зацепка, вывод-призыв к действию и т.п.)

Не включай в ответ примеры прямых цитат длиннее 5-7 слов — только обобщённое
описание паттернов.

ПОСТЫ:
{posts}
"""


def analyze(posts_path: str, sample_size: int = 15):
    with open(posts_path, encoding="utf-8") as f:
        content = f.read()

    posts = content.split("\n\n---\n\n")
    sample = posts[:sample_size]
    joined = "\n\n---\n\n".join(sample)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "user", "content": STYLE_ANALYSIS_PROMPT.format(posts=joined)}
        ],
        temperature=0.3,
    )

    style_description = response.choices[0].message.content
    print("\n=== ОПИСАНИЕ СТИЛЯ (вставить в app/prompts.py вручную) ===\n")
    print(style_description)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python analyze_style.py <путь_к_файлу_с_постами>")
        sys.exit(1)
    analyze(sys.argv[1])
