"""
Модели привычек и логов выполнения.
"""

from datetime import date, datetime, time
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class HabitFrequency(str, PyEnum):
    """Частота выполнения привычки."""
    DAILY = "daily"
    WEEKDAYS = "weekdays"
    WEEKENDS = "weekends"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class Habit(Base):
    """Модель привычки пользователя."""
    
    __tablename__ = "habits"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Основная информация
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emoji: Mapped[str] = mapped_column(String(10), default="✅")
    
    # Настройки времени
    reminder_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    frequency: Mapped[str] = mapped_column(
        String(20),
        default=HabitFrequency.DAILY.value
    )
    custom_days: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Битовая маска дней недели для custom частоты"
    )
    
    # Цели и прогресс
    target_days: Mapped[int] = mapped_column(
        Integer,
        default=21,
        comment="Целевое количество дней для формирования привычки"
    )
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_completions: Mapped[int] = mapped_column(Integer, default=0)
    
    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_paused: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        comment="Приостановлена ли привычка (временно отключена)"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # AI-контекст
    ai_suggested: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="habits")
    logs: Mapped[List["HabitLog"]] = relationship(
        "HabitLog",
        back_populates="habit",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(HabitLog.completed_date)"
    )
    
    def __repr__(self) -> str:
        return f"<Habit(id={self.id}, name={self.name}, user_id={self.user_id})>"
    
    @property
    def progress_percentage(self) -> float:
        """Процент выполнения цели."""
        if self.target_days == 0:
            return 0.0
        return min(100.0, (self.total_completions / self.target_days) * 100)
    
    @property
    def is_completed_today(self) -> bool:
        """Проверка, выполнена ли привычка сегодня."""
        today = date.today()
        for log in self.logs:
            if log.completed_date == today and log.status == "completed":
                return True
        return False
    
    def should_remind_today(self, current_date: date = None) -> bool:
        """Проверка, нужно ли напоминание на сегодня."""
        if not current_date:
            current_date = date.today()
        
        weekday = current_date.weekday()  # 0=Monday, 6=Sunday
        
        if self.frequency == HabitFrequency.DAILY.value:
            return True
        elif self.frequency == HabitFrequency.WEEKDAYS.value:
            return weekday < 5  # Пн-Пт
        elif self.frequency == HabitFrequency.WEEKENDS.value:
            return weekday >= 5  # Сб-Вс
        elif self.frequency == HabitFrequency.WEEKLY.value:
            # Напоминание в день создания или первый день недели
            return weekday == 0
        elif self.frequency == HabitFrequency.CUSTOM.value and self.custom_days:
            # custom_days - битовая маска
            try:
                mask = int(self.custom_days)
                return bool(mask & (1 << weekday))
            except ValueError:
                return True
        return True


class HabitLog(Base):
    """Лог выполнения/пропуска привычки."""
    
    __tablename__ = "habit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    habit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Дата выполнения
    completed_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Статус: completed, skipped, failed
    status: Mapped[str] = mapped_column(String(20), default="completed")
    
    # Дополнительные данные
    completed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mood: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Настроение 1-5"
    )
    
    # Relationships
    habit: Mapped["Habit"] = relationship("Habit", back_populates="logs")
    user: Mapped["User"] = relationship("User", back_populates="habit_logs")
    
    def __repr__(self) -> str:
        return (
            f"<HabitLog(id={self.id}, habit_id={self.habit_id}, "
            f"date={self.completed_date}, status={self.status})>"
        )
