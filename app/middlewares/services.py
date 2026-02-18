"""
Middleware для внедрения зависимостей (Dependency Injection).
Добавляет сервисы в контекст хендлеров.
"""

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.services.database import DatabaseService
from app.services.ai_service import AIService
from app.services.reminder_service import ReminderService


class ServicesMiddleware(BaseMiddleware):
    """
    Middleware для передачи сервисов в хендлеры.
    Реализует Dependency Injection pattern.
    """
    
    def __init__(
        self,
        db: DatabaseService,
        ai: AIService,
        reminder: ReminderService
    ):
        super().__init__()
        self.db = db
        self.ai = ai
        self.reminder = reminder
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Добавление сервисов в контекст."""
        data["db"] = self.db
        data["ai"] = self.ai
        data["reminder"] = self.reminder
        return await handler(event, data)
