"""
Модель пользователя.
Хранит основную информацию и настройки пользователя.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ai_context import AIContext
    from app.models.habit import Habit, HabitLog


class User(Base):
    """Модель пользователя Telegram."""
    
    __tablename__ = "users"
    
    # Telegram ID как первичный ключ
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    
    # Профиль
    username: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    first_name: Mapped[str] = mapped_column(String(64), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Настройки
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Настройки серии (streak)
    streak_break_days: Mapped[int] = mapped_column(
        Integer, 
        default=2,
        comment="Количество дней без выполнения для сброса серии (1/2/3 или 0=никогда)"
    )
    last_streak_check: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Последняя проверка серий"
    )
    
    # Статистика
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    total_completions: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Состояние для FSM (хранение промежуточных данных)
    temp_data: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    # Relationships
    habits: Mapped[List["Habit"]] = relationship(
        "Habit",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    habit_logs: Mapped[List["HabitLog"]] = relationship(
        "HabitLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    ai_context: Mapped[Optional["AIContext"]] = relationship(
        "AIContext",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, name={self.first_name})>"
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    @property
    def mention(self) -> str:
        """Упоминание пользователя (username или имя)."""
        if self.username:
            return f"@{self.username}"
        return self.full_name
