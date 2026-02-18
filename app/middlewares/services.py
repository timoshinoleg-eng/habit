"""
Middleware для внедрения зависимостей (Dependency Injection).
Добавляет сервисы в контекст хендлеров.
"""

import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.services.database import DatabaseService
from app.services.ai_service import AIService
from app.services.reminder_service import ReminderService
from app.services.streak_service import StreakService

logger = logging.getLogger(__name__)


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
        self.streak = StreakService(db)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Добавление сервисов в контекст и проверка streaks."""
        data["db"] = self.db
        data["ai"] = self.ai
        data["reminder"] = self.reminder
        data["streak"] = self.streak
        
        # Проверка streaks для сообщений и callback (кроме определенных команд)
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        
        if user_id:
            try:
                # Проверяем streaks (раз в час достаточно)
                user = await self.db.get_user(user_id)
                if user and (not user.last_streak_check or 
                           (await self._hours_since(user.last_streak_check)) >= 1):
                    broken = await self.streak.check_and_break_streaks(user_id)
                    # Уведомление отправится при следующем взаимодействии через специальный хендлер
                    if broken:
                        # Сохраняем информацию о broken streaks для уведомления
                        data["_broken_streaks"] = broken
            except Exception as e:
                logger.error(f"Error checking streaks for user {user_id}: {e}")
        
        return await handler(event, data)
    
    async def _hours_since(self, dt) -> int:
        """Вычисляет сколько часов прошло с момента dt."""
        from datetime import datetime
        return int((datetime.utcnow() - dt).total_seconds() / 3600)
