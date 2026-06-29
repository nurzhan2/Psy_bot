"""
Конфигурация проекта. Все секреты берутся из .env (см. .env.example)
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

TOP_K_PERSONAL = int(os.getenv("TOP_K_PERSONAL", 4))
TOP_K_BOOKS = int(os.getenv("TOP_K_BOOKS", 2))

DB_PATH = os.getenv("DB_PATH", "data/bot.db")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSONAL_MATERIALS_DIR = os.path.join(BASE_DIR, "personal_materials")
BOOKS_DIR = os.path.join(BASE_DIR, "books")
INDEX_DIR = os.path.join(BASE_DIR, "data", "index")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Проверь .env файл")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY не задан. Проверь .env файл")


# ==========================================================================
# Доработки (блоки 1–4). Все значения берутся из .env, есть безопасные дефолты.
# ==========================================================================
import json as _json

# --- Блок 4: роутинг моделей и оптимизация расходов на OpenAI ---
MODEL_SIMPLE = os.getenv("MODEL_SIMPLE", OPENAI_MODEL)          # дешёвая модель на простое
MODEL_COMPLEX = os.getenv("MODEL_COMPLEX", "gpt-4o")           # сильная модель на глубокое

_DEFAULT_PRICES = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o":      {"in": 2.50, "out": 10.00},
}
try:
    MODEL_PRICES_PER_1M = _json.loads(os.getenv("MODEL_PRICES_PER_1M_JSON", "")) or _DEFAULT_PRICES
except Exception:
    MODEL_PRICES_PER_1M = _DEFAULT_PRICES

CONTEXT_MAX_MESSAGES = int(os.getenv("CONTEXT_MAX_MESSAGES", 16))
CONTEXT_MAX_CHARS = int(os.getenv("CONTEXT_MAX_CHARS", 12000))
COMPLEXITY_CHAR_THRESHOLD = int(os.getenv("COMPLEXITY_CHAR_THRESHOLD", 600))

# --- Блок 2: шифрование переписки (Fernet). Пусто = шифрование выключено. ---
FERNET_KEY = os.getenv("FERNET_KEY", "")

# --- Блок 1: ЮKassa и подписка ---
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")
# Платежи включаются автоматически, когда заданы ключи ЮKassa.
# Пока не заданы — бот работает без paywall (удобно для теста).
PAYMENTS_ENABLED = bool(YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY)

SUBSCRIPTION_PRICE_RUB = float(os.getenv("SUBSCRIPTION_PRICE_RUB", 2990))
SUBSCRIPTION_PERIOD_DAYS = int(os.getenv("SUBSCRIPTION_PERIOD_DAYS", 30))
SUBSCRIPTION_PLAN_NAME = os.getenv("SUBSCRIPTION_PLAN_NAME", "Подписка на ИИ-ассистента")
RENEWAL_NOTICE_DAYS = int(os.getenv("RENEWAL_NOTICE_DAYS", 3))
SUBSCRIPTION_RETURN_URL = os.getenv("SUBSCRIPTION_RETURN_URL", "https://t.me/EkaterinaZvezdinaBot")

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 8080))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/yookassa")
SCHEDULER_INTERVAL_SECONDS = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", 3600))

# --- Блок 3: логирование ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", "logs")
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
