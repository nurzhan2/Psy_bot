# Образ для Telegram-бота по психологии (RAG + GPT)
FROM python:3.12-slim

# Не пишем .pyc, не буферизуем stdout (логи видны сразу)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Системные зависимости: ffmpeg нужен для расшифровки голосовых (Whisper/конвертация)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала зависимости — лучше кешируется
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Затем код
COPY . .

# data/ (БД, индексы) и logs/ монтируются томами — см. docker-compose.yml
RUN mkdir -p data logs

# Порт вебхука ЮKassa
EXPOSE 8080

CMD ["python", "main.py"]
