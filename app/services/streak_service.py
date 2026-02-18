"""
Сервис для проверки и управления сериями привычек (streaks).
Отслеживает пропущенные дни и сбрасывает серии при необходимости.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Tuple

from app.services.database import DatabaseService
from app.models import User, Habit, HabitLog

logger = logging.getLogger(__name__)


class StreakService:
    """Сервис для управления streaks пользователей."""
    
    def __init__(self, db: DatabaseService):
        self.db = db
    
    async def check_and_break_streaks(self, user_id: int) -> List[Tuple[Habit, int]]:
        """
        Проверка всех привычек пользователя и сброс серий при пропуске.
        
        Returns:
            Список кортежей (habit, broken_streak) для привычек, у которых сброшена серия
        """
        # Получаем пользователя для настройки streak_break_days
        user = await self.db.get_user(user_id)
        if not user:
            return []
        
        # Если настройка "никогда" не сбрасывать - пропускаем
        if user.streak_break_days == 0:
            return []
        
        habits = await self.db.get_user_habits(user_id, active_only=True)
        broken_streaks = []
        
        for habit in habits:
            broken = await self._check_habit_streak(habit, user.streak_break_days)
            if broken:
                broken_streaks.append((habit, habit.current_streak))
                logger.info(
                    f"Streak broken for user {user_id}, habit {habit.id}: "
                    f"was {habit.current_streak}, reset to 0"
                )
        
        # Обновляем время последней проверки
        await self.db.update_user(user_id, last_streak_check=datetime.utcnow())
        
        return broken_streaks
    
    async def _check_habit_streak(self, habit: Habit, break_days: int) -> bool:
        """
        Проверка одной привычки на необходимость сброса серии.
        
        Args:
            habit: Привычка для проверки
            break_days: Количество дней без выполнения для сброса
        
        Returns:
            True если серия была сброшена
        """
        # Если серия уже 0 - нечего сбрасывать
        if habit.current_streak == 0:
            return False
        
        # Получаем последний лог привычки
        logs = await self.db.get_habit_logs(habit.id, habit.user_id, days=break_days + 1)
        
        if not logs:
            # Нет логов за последние N дней - сбрасываем серию
            await self._break_streak(habit)
            return True
        
        # Находим последнюю запись со статусом completed
        last_completed = None
        for log in sorted(logs, key=lambda x: x.completed_date, reverse=True):
            if log.status == "completed":
                last_completed = log.completed_date
                break
        
        if not last_completed:
            # Нет выполнений вообще - сбрасываем
            await self._break_streak(habit)
            return True
        
        # Вычисляем сколько дней прошло
        days_since_completion = (date.today() - last_completed).days
        
        if days_since_completion >= break_days:
            # Прошло достаточно дней - сбрасываем серию
            await self._break_streak(habit)
            return True
        
        return False
    
    async def _break_streak(self, habit: Habit) -> None:
        """Сброс серии привычки."""
        await self.db.update_habit(
            habit.id,
            habit.user_id,
            current_streak=0
        )
    
    async def notify_broken_streaks(
        self, 
        bot, 
        user_id: int, 
        broken: List[Tuple[Habit, int]]
    ) -> None:
        """Отправка уведомлений о сброшенных сериях."""
        if not broken:
            return
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Формируем сообщение
        if len(broken) == 1:
            habit, old_streak = broken[0]
            text = (
                f"😔 <b>Серия прервана</b>\n\n"
                f"{habit.emoji} <b>{habit.name}</b>\n"
                f"Серия из <b>{old_streak} дней</b> сброшена.\n\n"
                f"Не расстраивайся! Начни новую серию прямо сейчас 💪"
            )
        else:
            text = (
                f"😔 <b>Несколько серий прервано</b>\n\n"
                f"Сброшены серии:\n"
            )
            for habit, old_streak in broken:
                text += f"• {habit.emoji} {habit.name}: {old_streak} дней\n"
            text += "\nНе сдавайся! Начни заново 💪"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Мои привычки",
                    callback_data="list_habits"
                ),
                InlineKeyboardButton(
                    text="🤖 AI-совет",
                    callback_data="ai_advice"
                )
            ]
        ])
        
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send streak break notification to {user_id}: {e}")
    
    async def check_all_users(self, bot) -> int:
        """
        Проверка серий всех пользователей (для запуска по расписанию).
        
        Returns:
            Количество пользователей с broken streaks
        """
        # TODO: Получить всех активных пользователей из БД
        # Пока заглушка
        logger.info("Checking streaks for all users...")
        return 0
