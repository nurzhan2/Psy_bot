# Доработки проекта (блоки 1–4)

Этот архив — исходный Psy_bot с четырьмя встроенными блоками из TODO. Всё уже
подключено в код (роутеры, импорты, инициализация БД) — отдельной интеграции не требуется.

## Блок 1 — Платежи и подписка (ЮKassa)
- `app/db/subscriptions.py` — таблицы подписок и платежей (SQLAlchemy).
- `app/payments/yookassa_client.py` — первый платёж (с сохранением способа оплаты) и рекуррент.
- `app/payments/webhook.py` — приём вебхуков ЮKassa, активация подписки.
- `app/payments/scheduler.py` — уведомление за 3 дня + автосписания.
- `app/payments/texts.py` — тексты (формулировка уведомления — дословно по ТЗ).
- `app/handlers/subscription.py` — paywall, оплата, статус, мгновенная отмена, «калитка» доступа.
- Подключено в `main.py` и в пайплайн `dialogue.py` (текст и голос — за подпиской).

ВАЖНО: пока в `.env` не заданы `YOOKASSA_SHOP_ID`/`YOOKASSA_SECRET_KEY`, платежи
выключены (`PAYMENTS_ENABLED=False`) и бот работает БЕЗ paywall — удобно для теста.
Как только ключи заданы — включается подписка, вебхук-сервер и планировщик.
Вебхуку нужен публичный HTTPS (домен + nginx/TLS), URL вида `https://<домен>/yookassa`.

## Блок 2 — Шифрование переписки (152-ФЗ)
- `app/crypto.py` — Fernet-шифрование. Встроено в `app/db/history.py`
  (шифр при записи, расшифровка при чтении).
- Пока `FERNET_KEY` пуст — шифрование выключено (с предупреждением в логах).
  Для продакшена сгенерируйте ключ (команда в `.env.example`) и держите бэкап
  ключа отдельно от бэкапа БД.

## Блок 3 — Деплой, автозапуск, логирование
- `app/logging_setup.py` — консоль + файл с ротацией + опц. Sentry. Включено в `main.py`.
- `Dockerfile`, `docker-compose.yml`, `.dockerignore` — Docker-вариант.
- `deploy/psybot.service` — systemd-вариант для VPS без Docker.

## Блок 4 — Оптимизация расходов на OpenAI
- `app/llm_optimize.py` — роутинг моделей, обрезка контекста, кэш эмбеддингов, учёт стоимости.
- Встроено в `app/llm.py` (роутинг + лог стоимости) и `app/rag/vector_store.py` (кэш эмбеддингов).
- Кэш ответов модели намеренно НЕ делался (риск для приватности/качества терапии).

## Прочие правки
- В `requirements.txt` добавлен отсутствовавший `faiss-cpu` (без него RAG не стартует),
  плюс `yookassa`, `cryptography`, `aiohttp`.
- Файлы практик Екатерины (`personal_materials/practices/`) переименованы в
  `practice_NN.ext` — исходные имена из Telegram-экспорта были слишком длинными
  для файловой системы. Соответствие имён — в `personal_materials/practices/_filenames.txt`.

## Запуск
```
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # заполнить BOT_TOKEN, OPENAI_API_KEY (и остальное по мере подключения)
python -m app.rag.build_index   # собрать индекс из personal_materials/ и books/
python main.py
```

Полные инструкции по деплою и подписке — в README.md и в комментариях внутри модулей.
