# -*- coding: utf-8 -*-
"""
HabitMax Bot - Configuration settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).parent.parent

# Load environment variables from .env file
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

# Bot settings
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")

# Database settings
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"sqlite+aiosqlite:///{BASE_DIR}/habitmax.db"
)

# OCR Settings
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "")

# Scheduler settings
REMINDER_CHECK_INTERVAL = int(os.getenv("REMINDER_CHECK_INTERVAL", "60"))  # seconds
FINANCE_REMINDER_HOUR = int(os.getenv("FINANCE_REMINDER_HOUR", "9"))
FINANCE_REMINDER_MINUTE = int(os.getenv("FINANCE_REMINDER_MINUTE", "0"))

# AI settings (placeholder for future AI integration)
AI_ENABLED = os.getenv("AI_ENABLED", "false").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Cache settings
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
HABITS_CACHE_SIZE = int(os.getenv("HABITS_CACHE_SIZE", "1000"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Banks list for finance module
BANKS = [
    "Т-Банк",
    "Сбербанк", 
    "ВТБ",
    "Альфа-Банк",
    "Тинькофф",
    "Другой"
]

# Achievement definitions
ACHIEVEMENTS = {
    'streak_7': {
        'title': 'Первые 7 дней',
        'description': '7 дней подряд выполняете привычку',
        'icon': '🔥'
    },
    'streak_30': {
        'title': 'Месяц огня',
        'description': '30 дней подряд! Невероятно!',
        'icon': '🏆'
    },
    'streak_100': {
        'title': 'Легенда',
        'description': '100 дней подряд! Вы неостановимы!',
        'icon': '👑'
    },
    'total_50': {
        'title': 'Мастер привычек',
        'description': '50 выполнений привычек',
        'icon': '⭐'
    },
    'finance_10': {
        'title': 'Финансовый дисциплинар',
        'description': '10 платежей вовремя',
        'icon': '💰'
    },
}
