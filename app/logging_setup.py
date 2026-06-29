"""
Настройка логирования для продакшена.

- В консоль (видно в `docker logs` / journalctl).
- В файл с ротацией (logs/bot.log, 5 файлов по 5 МБ).
- Опционально Sentry — если задан SENTRY_DSN в окружении.

Вызвать ОДИН раз в самом начале main.py, до создания бота:
    from app.logging_setup import setup_logging
    setup_logging()
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_dir / "bot.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # aiogram бывает слишком болтлив на DEBUG — приглушим до WARNING
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    # Опциональный Sentry для алертов о падениях в проде.
    dsn = os.getenv("SENTRY_DSN")
    if dsn:
        try:
            import sentry_sdk

            sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0, send_default_pii=False)
            logging.getLogger(__name__).info("Sentry подключён")
        except Exception:
            logging.getLogger(__name__).warning("SENTRY_DSN задан, но sentry_sdk не установлен")

    _CONFIGURED = True
    logging.getLogger(__name__).info("Логирование настроено: уровень=%s", level_name)
