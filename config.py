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
