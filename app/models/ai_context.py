"""
Модель для хранения AI-контекста пользователя.
Используется для долгосрочной памяти AI-ассистента.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AIContext(Base):
    """
    Контекст пользователя для AI.
    Хранит агрегированные данные для персонализации рекомендаций.
    """
    
    __tablename__ = "ai_contexts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Агрегированная статистика (для AI-промптов)
    total_habits_created: Mapped[int] = mapped_column(Integer, default=0)
    total_habits_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_habits_failed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Паттерны поведения
    most_productive_day: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Самый продуктивный день недели"
    )
    most_productive_time: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Самое продуктивное время суток (morning/afternoon/evening)"
    )
    
    # Проблемные зоны (JSON-строка с названиями привычек)
    struggling_habits: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Список привычек, с которыми пользователь часто проваливается"
    )
    
    # Успешные паттерны
    successful_patterns: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Что работает хорошо для пользователя"
    )
    
    # История взаимодействий с AI (последние N рекомендаций)
    last_ai_recommendations: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON с последними рекомендациями"
    )
    
    # Настройки AI
    ai_aggressiveness: Mapped[int] = mapped_column(
        Integer,
        default=2,
        comment="Уровень настойчивости AI (1-3)"
    )
    preferred_reminder_style: Mapped[str] = mapped_column(
        String(20),
        default="friendly",
        comment="Стиль напоминаний: friendly, strict, motivational"
    )
    
    # Общее настроение пользователя (среднее)
    average_mood: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Среднее настроение 1-5"
    )
    
    # Последнее обновление контекста
    context_updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ai_context")
    
    def __repr__(self) -> str:
        return f"<AIContext(user_id={self.user_id}, updated={self.context_updated_at})>"
    
    def get_struggling_habits_list(self) -> list:
        """Возвращает список проблемных привычек."""
        import json
        if not self.struggling_habits:
            return []
        try:
            return json.loads(self.struggling_habits)
        except json.JSONDecodeError:
            return []
    
    def set_struggling_habits(self, habits: list) -> None:
        """Сохраняет список проблемных привычек."""
        import json
        self.struggling_habits = json.dumps(habits[:5])  # Только топ-5
    
    def get_successful_patterns_list(self) -> list:
        """Возвращает список успешных паттернов."""
        import json
        if not self.successful_patterns:
            return []
        try:
            return json.loads(self.successful_patterns)
        except json.JSONDecodeError:
            return []
    
    def set_successful_patterns(self, patterns: list) -> None:
        """Сохраняет успешные паттерны."""
        import json
        self.successful_patterns = json.dumps(patterns[:5])
    
    def get_summary_for_prompt(self) -> str:
        """
        Генерирует краткое саммари для AI-промпта.
        Оптимизировано по токенам.
        """
        parts = []
        
        if self.most_productive_time:
            parts.append(f"productive_time:{self.most_productive_time}")
        
        if self.most_productive_day:
            parts.append(f"best_day:{self.most_productive_day}")
        
        struggling = self.get_struggling_habits_list()
        if struggling:
            parts.append(f"struggles:{','.join(struggling[:3])}")
        
        successful = self.get_successful_patterns_list()
        if successful:
            parts.append(f"success:{','.join(successful[:3])}")
        
        if self.average_mood:
            parts.append(f"mood:{self.average_mood:.1f}")
        
        return ";".join(parts) if parts else "new_user"
