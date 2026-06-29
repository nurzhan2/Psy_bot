"""
Шифрование переписки «на диске» (at-rest) — требование Екатерины по 152-ФЗ.

Симметричное шифрование Fernet (AES-128-CBC + HMAC). Ключ — из FERNET_KEY.

ВАЖНО про режим работы:
- Если FERNET_KEY задан — новые сообщения шифруются, старые читаются прозрачно.
- Если FERNET_KEY пуст — шифрование ВЫКЛЮЧЕНО (бот работает, пишет открытым текстом),
  и при старте выводится предупреждение в лог. Для продакшена ключ обязателен.

Сгенерировать ключ:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
и положить в .env как FERNET_KEY=...

Потеря ключа = невозможность расшифровать старую переписку. Бэкап ключа держите
ОТДЕЛЬНО от бэкапа БД.
"""
import logging

from config import FERNET_KEY

log = logging.getLogger(__name__)

_PREFIX = "enc:"
_fernet = None
_warned = False

if FERNET_KEY:
    try:
        from cryptography.fernet import Fernet, InvalidToken
        _fernet = Fernet(FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY)
    except Exception:
        log.exception("FERNET_KEY задан, но невалиден — шифрование выключено")
        _fernet = None
else:
    class InvalidToken(Exception):  # заглушка, чтобы except ниже не падал на импорте
        pass


def _warn_once():
    global _warned
    if not _warned:
        log.warning("FERNET_KEY не задан — переписка хранится БЕЗ шифрования. "
                    "Для продакшена задайте ключ в .env (см. app/crypto.py).")
        _warned = True


def encrypt(plaintext: str) -> str:
    if plaintext is None:
        return plaintext
    if _fernet is None:
        _warn_once()
        return plaintext  # passthrough без шифрования
    return _PREFIX + _fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(stored: str) -> str:
    if stored is None:
        return stored
    if not stored.startswith(_PREFIX):
        return stored  # легаси/незашифрованное значение
    if _fernet is None:
        return ""  # есть шифротекст, но нет ключа — расшифровать нечем
    token = stored[len(_PREFIX):]
    try:
        return _fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return ""
