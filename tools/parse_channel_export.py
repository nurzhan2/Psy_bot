"""
Парсер экспорта Telegram-аккаунта.

ВАЖНО: при экспорте через Telegram Desktop без выбора конкретного диалога
(Settings -> Advanced -> Export Telegram Data) получается файл со ВСЕМИ чатами
аккаунта в структуре data["chats"]["list"], а не одним каналом. Этот скрипт
работает именно с такой структурой и даёт выбрать нужные чаты по имени.

Получить файл:
  Settings -> Advanced -> Export Telegram Data -> отметить только "Personal chats"
  или конкретные каналы -> формат: JSON (machine-readable) -> Export

Запуск (посмотреть, какие чаты есть в файле):
  python tools/parse_channel_export.py path/to/result.json --list

Запуск (выгрузить конкретные чаты по имени, можно несколько):
  python tools/parse_channel_export.py path/to/result.json personal_materials/channel_posts.txt \\
      --include "Психолог Екатерина Звездина"

  python tools/parse_channel_export.py path/to/result.json personal_materials/private_channels.txt \\
      --include "Любовь к себе" "Исцеление внутреннего ребёнка" "Терапевтическая группа с Екатериной Звездиной"
"""
import argparse
import json
from pathlib import Path
from typing import List


def extract_text(message: dict) -> str:
    """
    В экспорте Telegram текст сообщения может быть строкой или списком
    "кусочков" (если есть форматирование, ссылки и т.п.) — собираем в одну строку.
    """
    text = message.get("text", "")
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        parts = []
        for piece in text:
            if isinstance(piece, str):
                parts.append(piece)
            elif isinstance(piece, dict):
                parts.append(piece.get("text", ""))
        return "".join(parts)
    return ""


def list_chats(data: dict):
    chats = data.get("chats", {}).get("list", [])
    print(f"Найдено чатов: {len(chats)}\n")
    for c in chats:
        name = c.get("name") or "(без названия)"
        ctype = c.get("type", "?")
        msg_count = len(c.get("messages", []))
        print(f"  [{ctype:16s}] {msg_count:5d} сообщ.  —  {name}")


def parse_export(json_path: str, output_path: str, include: List[str], min_length: int = 30):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    chats = data.get("chats", {}).get("list", [])
    include_lower = [name.lower() for name in include]

    posts = []
    matched_chats = []

    for chat in chats:
        name = chat.get("name") or ""
        if name.lower() not in include_lower:
            continue
        matched_chats.append(name)

        for msg in chat.get("messages", []):
            if msg.get("type") != "message":
                continue
            text = extract_text(msg).strip()
            if len(text) < min_length:
                continue
            posts.append(f"[{name}]\n{text}")

    if not matched_chats:
        print("Не найдено ни одного чата с указанными именами. Проверь точное название (--list).")
        return

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n---\n\n".join(posts))

    print(f"Обработаны чаты: {', '.join(matched_chats)}")
    print(f"Сохранено постов: {len(posts)}")
    print(f"Результат: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", help="Путь к result.json")
    parser.add_argument("output_path", nargs="?", help="Куда сохранить текст (нужно, если не --list)")
    parser.add_argument("--include", nargs="+", default=[], help="Точные названия чатов для выгрузки")
    parser.add_argument("--list", action="store_true", help="Просто показать список чатов в файле")
    args = parser.parse_args()

    with open(args.json_path, encoding="utf-8") as f:
        loaded = json.load(f)

    if args.list:
        list_chats(loaded)
    else:
        if not args.output_path or not args.include:
            print("Нужны output_path и --include (или используй --list для просмотра имён чатов)")
        else:
            parse_export(args.json_path, args.output_path, args.include)

