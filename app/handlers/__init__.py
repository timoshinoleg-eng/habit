"""
Хендлеры Aiogram для обработки сообщений и callback.
"""

from app.handlers.common import router as common_router
from app.handlers.habits import router as habits_router
from app.handlers.ai_handlers import router as ai_router

__all__ = ["common_router", "habits_router", "ai_router"]
