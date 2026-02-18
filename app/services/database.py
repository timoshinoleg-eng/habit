"""
Сервис для работы с базой данных.
Реализует Repository Pattern для асинхронных операций с SQLAlchemy 2.0.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, update, delete, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models import Base, User, Habit, HabitLog, AIContext
from app.models.habit import HabitFrequency


class DatabaseService:
    """Сервис для работы с базой данных."""
    
    def __init__(self):
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.log_level == "DEBUG"
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def init_db(self) -> None:
        """Инициализация базы данных (создание таблиц)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self) -> None:
        """Закрытие соединения с БД."""
        await self.engine.dispose()
    
    async def get_session(self) -> AsyncSession:
        """Получение сессии БД."""
        return self.session_factory()
    
    # ==================== User Repository ====================
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Получение пользователя по ID."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def create_user(
        self,
        user_id: int,
        username: Optional[str],
        first_name: str,
        last_name: Optional[str] = None
    ) -> User:
        """Создание нового пользователя."""
        async with self.session_factory() as session:
            user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Обновление данных пользователя."""
        async with self.session_factory() as session:
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(**kwargs)
            )
            await session.commit()
            return await self.get_user(user_id)
    
    async def get_or_create_user(
        self,
        user_id: int,
        username: Optional[str],
        first_name: str,
        last_name: Optional[str] = None
    ) -> User:
        """Получение или создание пользователя."""
        user = await self.get_user(user_id)
        if not user:
            user = await self.create_user(user_id, username, first_name, last_name)
        return user
    
    # ==================== Habit Repository ====================
    
    async def create_habit(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        emoji: str = "✅",
        reminder_time: Optional[datetime] = None,
        frequency: str = HabitFrequency.DAILY.value,
        target_days: int = 21,
        custom_days: Optional[str] = None
    ) -> Habit:
        """Создание новой привычки."""
        async with self.session_factory() as session:
            habit = Habit(
                user_id=user_id,
                name=name,
                description=description,
                emoji=emoji,
                reminder_time=reminder_time.time() if reminder_time else None,
                frequency=frequency,
                target_days=target_days,
                custom_days=custom_days
            )
            session.add(habit)
            
            # Обновляем статистику AI-контекста
            await session.execute(
                update(AIContext)
                .where(AIContext.user_id == user_id)
                .values(total_habits_created=AIContext.total_habits_created + 1)
            )
            
            await session.commit()
            await session.refresh(habit)
            return habit
    
    async def get_habit(self, habit_id: int, user_id: int) -> Optional[Habit]:
        """Получение привычки по ID и user_id."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Habit)
                .where(and_(Habit.id == habit_id, Habit.user_id == user_id))
            )
            return result.scalar_one_or_none()
    
    async def get_user_habits(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[Habit]:
        """Получение всех привычек пользователя."""
        async with self.session_factory() as session:
            query = select(Habit).where(Habit.user_id == user_id)
            if active_only:
                query = query.where(Habit.is_active == True)
            query = query.order_by(desc(Habit.created_at))
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def update_habit(
        self,
        habit_id: int,
        user_id: int,
        **kwargs
    ) -> Optional[Habit]:
        """Обновление привычки."""
        async with self.session_factory() as session:
            await session.execute(
                update(Habit)
                .where(and_(Habit.id == habit_id, Habit.user_id == user_id))
                .values(**kwargs)
            )
            await session.commit()
            return await self.get_habit(habit_id, user_id)
    
    async def delete_habit(self, habit_id: int, user_id: int) -> bool:
        """Удаление привычки."""
        async with self.session_factory() as session:
            result = await session.execute(
                delete(Habit)
                .where(and_(Habit.id == habit_id, Habit.user_id == user_id))
            )
            await session.commit()
            return result.rowcount > 0
    
    # ==================== HabitLog Repository ====================
    
    async def log_habit_completion(
        self,
        habit_id: int,
        user_id: int,
        status: str = "completed",
        notes: Optional[str] = None,
        mood: Optional[int] = None,
        log_date: Optional[date] = None
    ) -> HabitLog:
        """Запись выполнения/пропуска привычки."""
        async with self.session_factory() as session:
            log_date = log_date or date.today()
            
            # Проверяем, есть ли уже запись на эту дату
            existing = await session.execute(
                select(HabitLog)
                .where(
                    and_(
                        HabitLog.habit_id == habit_id,
                        HabitLog.user_id == user_id,
                        HabitLog.completed_date == log_date
                    )
                )
            )
            existing_log = existing.scalar_one_or_none()
            
            if existing_log:
                # Обновляем существующую запись
                existing_log.status = status
                existing_log.notes = notes
                existing_log.mood = mood
                existing_log.completed_at = datetime.utcnow()
                log = existing_log
            else:
                # Создаем новую запись
                log = HabitLog(
                    habit_id=habit_id,
                    user_id=user_id,
                    completed_date=log_date,
                    status=status,
                    notes=notes,
                    mood=mood
                )
                session.add(log)
            
            # Обновляем статистику привычки
            habit = await session.get(Habit, habit_id)
            if habit:
                if status == "completed":
                    habit.total_completions += 1
                    habit.current_streak += 1
                    if habit.current_streak > habit.best_streak:
                        habit.best_streak = habit.current_streak
                else:
                    habit.current_streak = 0
            
            # Обновляем статистику пользователя
            user = await session.get(User, user_id)
            if user:
                user.total_completions += 1 if status == "completed" else 0
                user.last_active = datetime.utcnow()
            
            await session.commit()
            await session.refresh(log)
            return log
    
    async def get_habit_logs(
        self,
        habit_id: int,
        user_id: int,
        days: int = 30
    ) -> List[HabitLog]:
        """Получение логов привычки за последние N дней."""
        async with self.session_factory() as session:
            from_date = date.today() - timedelta(days=days)
            result = await session.execute(
                select(HabitLog)
                .where(
                    and_(
                        HabitLog.habit_id == habit_id,
                        HabitLog.user_id == user_id,
                        HabitLog.completed_date >= from_date
                    )
                )
                .order_by(desc(HabitLog.completed_date))
            )
            return list(result.scalars().all())
    
    async def get_today_logs(self, user_id: int) -> List[HabitLog]:
        """Получение логов за сегодня."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(HabitLog)
                .where(
                    and_(
                        HabitLog.user_id == user_id,
                        HabitLog.completed_date == date.today()
                    )
                )
            )
            return list(result.scalars().all())
    
    # ==================== Statistics ====================
    
    async def get_user_stats(self, user_id: int) -> dict:
        """Получение статистики пользователя."""
        async with self.session_factory() as session:
            # Общее количество привычек
            habits_count = await session.execute(
                select(func.count(Habit.id))
                .where(Habit.user_id == user_id)
            )
            
            # Активные привычки
            active_habits = await session.execute(
                select(func.count(Habit.id))
                .where(and_(Habit.user_id == user_id, Habit.is_active == True))
            )
            
            # Общее количество выполнений
            total_completions = await session.execute(
                select(func.count(HabitLog.id))
                .where(
                    and_(
                        HabitLog.user_id == user_id,
                        HabitLog.status == "completed"
                    )
                )
            )
            
            # Лучшая серия
            best_streak = await session.execute(
                select(func.max(Habit.best_streak))
                .where(Habit.user_id == user_id)
            )
            
            return {
                "total_habits": habits_count.scalar() or 0,
                "active_habits": active_habits.scalar() or 0,
                "total_completions": total_completions.scalar() or 0,
                "best_streak": best_streak.scalar() or 0,
            }
    
    # ==================== AI Context ====================
    
    async def get_or_create_ai_context(self, user_id: int) -> AIContext:
        """Получение или создание AI-контекста пользователя."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(AIContext).where(AIContext.user_id == user_id)
            )
            context = result.scalar_one_or_none()
            
            if not context:
                context = AIContext(user_id=user_id)
                session.add(context)
                await session.commit()
                await session.refresh(context)
            
            return context
    
    async def update_ai_context(self, user_id: int, **kwargs) -> AIContext:
        """Обновление AI-контекста."""
        async with self.session_factory() as session:
            await session.execute(
                update(AIContext)
                .where(AIContext.user_id == user_id)
                .values(**kwargs)
            )
            await session.commit()
            return await self.get_or_create_ai_context(user_id)
    
    async def get_habits_for_reminder(
        self,
        current_time: datetime
    ) -> List[tuple[Habit, User]]:
        """Получение привычек для напоминаний на текущее время."""
        async with self.session_factory() as session:
            from sqlalchemy.orm import joinedload
            import pytz
            
            result = await session.execute(
                select(Habit, User)
                .join(User)
                .where(
                    and_(
                        Habit.is_active == True,
                        Habit.reminder_time.isnot(None),
                        User.notification_enabled == True
                    )
                )
                .options(joinedload(Habit.user))
            )
            
            habits_users = []
            for habit, user in result.all():
                if habit.reminder_time:
                    # Конвертируем UTC время в локальное время пользователя
                    try:
                        user_tz = pytz.timezone(user.timezone)
                    except pytz.UnknownTimeZoneError:
                        user_tz = pytz.UTC
                    
                    # current_time приходит в UTC
                    user_local_time = current_time.replace(tzinfo=pytz.UTC).astimezone(user_tz)
                    current_time_str = user_local_time.strftime("%H:%M")
                    habit_time = habit.reminder_time.strftime("%H:%M")
                    
                    if habit_time == current_time_str and habit.should_remind_today(user_local_time.date()):
                        habits_users.append((habit, user))
            
            return habits_users
