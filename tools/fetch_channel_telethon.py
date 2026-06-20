"""
Альтернативный способ выгрузки — напрямую через Telegram API (Telethon),
без Desktop-экспорта. Подходит, если канал публичный и большой, либо если
экспорт через Desktop по каким-то причинам неудобен.

ВАЖНО ПО БЕЗОПАСНОСТИ:
- Для работы скрипта нужен СВОЙ Telegram-аккаунт (API_ID/API_HASH с my.telegram.org)
  и номер телефона, на который придёт код подтверждения.
- Не используйте для этого аккаунт Екатерины и не просите у неё код/пароль
  от её личного Telegram — это создаёт ненужный риск (доступ к личной переписке,
  а не только к каналу). Если канал публичный — достаточно вашего собственного
  аккаунта, который просто подписывается на канал и читает историю.
- Если канал приватный и закрытый — проще и безопаснее попросить Екатерину
  самостоятельно сделать Desktop-экспорт и переслать файл (см. parse_channel_export.py).

Установка:
  pip install telethon

Получить API_ID и API_HASH:
  https://my.telegram.org -> API Development Tools

Запуск:
  python tools/fetch_channel_telethon.py @channel_username personal_materials/channel_posts.txt
"""
import asyncio
import os
import sys

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
SESSION_NAME = "channel_export_session"


async def fetch_channel(channel_username: str, output_path: str, min_length: int = 30):
    if not API_ID or not API_HASH:
        print("Не заданы TG_API_ID / TG_API_HASH. Получи их на https://my.telegram.org")
        sys.exit(1)

    client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
    await client.start()

    posts = []
    async for message in client.iter_messages(channel_username, reverse=True):
        text = (message.text or "").strip()
        if len(text) >= min_length:
            posts.append(text)

    await client.disconnect()

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n---\n\n".join(posts))

    print(f"Сохранено постов: {len(posts)}")
    print(f"Результат: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python fetch_channel_telethon.py <@channel> <output.txt>")
        sys.exit(1)
    asyncio.run(fetch_channel(sys.argv[1], sys.argv[2]))
