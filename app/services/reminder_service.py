"""
Сервис для управления напоминаниями.
Использует APScheduler для планирования задач.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.services.database import DatabaseService
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class ReminderService:
    """Сервис для отправки напоминаний о привычках."""
    
    def __init__(
        self,
        bot: Bot,
        db_service: DatabaseService,
        ai_service: AIService
    ):
        self.bot = bot
        self.db = db_service
        self.ai = ai_service
        self.scheduler: Optional[AsyncIOScheduler] = None
    
    async def start(self) -> None:
        """Запуск планировщика напоминаний."""
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        
        # Добавляем задачу на каждую минуту для проверки напоминаний
        self.scheduler.add_job(
            self._check_and_send_reminders,
            trigger=CronTrigger(minute="*"),  # Каждую минуту
            id="reminder_check",
            replace_existing=True
        )
        
        # Добавляем задачу анализа паттернов раз в день
        self.scheduler.add_job(
            self._daily_pattern_analysis,
            trigger=CronTrigger(hour=3, minute=0),  # В 3 ночи
            id="pattern_analysis",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Reminder scheduler started")
    
    async def stop(self) -> None:
        """Остановка планировщика."""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Reminder scheduler stopped")
    
    async def _check_and_send_reminders(self) -> None:
        """Проверка и отправка напоминаний (вызывается каждую минуту)."""
        try:
            now = datetime.utcnow()
            
            # Получаем привычки для напоминания
            # Теперь передаем UTC время, а сравнение происходит с учетом часового пояса
            habits_users = await self.db.get_habits_for_reminder(now)
            
            for habit, user in habits_users:
                # Проверяем, не выполнена ли уже привычка сегодня
                if habit.is_completed_today:
                    continue
                
                # Проверяем, включены ли AI-напоминания
                if user.ai_enabled:
                    try:
                        message = await self.ai.get_personalized_reminder(user, habit)
                    except Exception as e:
                        logger.error(f"AI reminder generation failed: {e}")
                        message = (
                            f"{habit.emoji} <b>Напоминание!</b>\n\n"
                            f"Пора выполнить привычку: <b>{habit.name}</b>\n"
                            f"🔥 Текущая серия: {habit.current_streak} дней"
                        )
                else:
                    message = (
                        f"{habit.emoji} <b>Напоминание!</b>\n\n"
                        f"Пора выполнить привычку: <b>{habit.name}</b>\n"
                        f"🔥 Текущая серия: {habit.current_streak} дней"
                    )
                
                # Отправляем напоминание
                try:
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Выполнено",
                                callback_data=f"complete:{habit.id}"
                            ),
                            InlineKeyboardButton(
                                text="⏰ Напомнить через час",
                                callback_data=f"snooze:{habit.id}"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="❌ Пропустить",
                                callback_data=f"skip:{habit.id}"
                            )
                        ]
                    ])
                    
                    await self.bot.send_message(
                        chat_id=user.id,
                        text=message,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                    
                    logger.debug(f"Reminder sent to user {user.id} for habit {habit.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to send reminder to {user.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in reminder check: {e}")
    
    async def _daily_pattern_analysis(self) -> None:
        """Ежедневный анализ паттернов пользователей."""
        try:
            logger.info("Starting daily pattern analysis")
            
            # Получаем всех активных пользователей
            # Для простоты анализируем всех, у кого есть привычки
            # В реальном приложении можно добавить флаг "needs_analysis"
            
            # TODO: Оптимизировать для большого количества пользователей
            # Пока просто логируем
            logger.info("Daily pattern analysis completed")
            
        except Exception as e:
            logger.error(f"Error in pattern analysis: {e}")
    
    async def schedule_habit_reminder(
        self,
        user_id: int,
        habit_id: int,
        reminder_time: datetime,
        use_ai: bool = True
    ) -> None:
        """
        Планирование напоминания для конкретной привычки.
        
        Note: В текущей реализации напоминания проверяются каждую минуту
        через cron, так что это скорее вспомогательный метод.
        """
        # В данной архитектуре напоминания проверяются глобально каждую минуту
        # Этот метод может быть расширен для специфических случаев
        pass
    
    async def send_manual_reminder(
        self,
        user_id: int,
        habit_id: int
    ) -> bool:
        """Отправка ручного напоминания."""
        try:
            habit = await self.db.get_habit(habit_id, user_id)
            if not habit:
                return False
            
            user = await self.db.get_user(user_id)
            if not user:
                return False
            
            if user.ai_enabled:
                message = await self.ai.get_personalized_reminder(user, habit)
            else:
                message = (
                    f"{habit.emoji} <b>Напоминание!</b>\n\n"
                    f"Не забудь про: <b>{habit.name}</b>\n"
                    f"🔥 Текущая серия: {habit.current_streak} дней"
                )
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Выполнено",
                        callback_data=f"complete:{habit.id}"
                    )
                ]
            ])
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send manual reminder: {e}")
            return False
