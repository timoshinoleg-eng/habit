"""
Базовые модели SQLAlchemy для Mini App API.
Расширяют существующие модели из бота.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings


class Base(DeclarativeBase):
    """Базовый класс для моделей."""
    pass


class UserActivity(Base):
    """Модель для отслеживания активности пользователя в Mini App."""
    
    __tablename__ = "user_activities"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    
    # Данные о сессии
    session_start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    session_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Действия в Mini App
    actions: Mapped[str] = mapped_column(Text, default="")  # JSON строка
    
    # Метаданные
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)


class WeeklySummary(Base):
    """Сохраненные еженедельные саммари."""
    
    __tablename__ = "weekly_summaries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    
    # Период
    week_start: Mapped[datetime] = mapped_column(DateTime)
    week_end: Mapped[datetime] = mapped_column(DateTime)
    
    # Статистика
    total_habits: Mapped[int] = mapped_column(Integer, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    
    # AI-генерация
    ai_summary_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Кэширование
    is_cached: Mapped[bool] = mapped_column(default=True)
    cache_expires_at: Mapped[datetime] = mapped_column(DateTime)


class FailureAnalysis(Base):
    """Сохраненные анализы срывов."""
    
    __tablename__ = "failure_analyses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    habit_id: Mapped[int] = mapped_column(Integer, ForeignKey("habits.id", ondelete="CASCADE"))
    
    # Данные для анализа
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    skip_reasons: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    
    # AI-генерация
    ai_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strategies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Кэширование
    is_cached: Mapped[bool] = mapped_column(default=True)
    cache_expires_at: Mapped[datetime] = mapped_column(DateTime)


class AIRequestCache(Base):
    """Кэш для AI-запросов (rate limiting)."""
    
    __tablename__ = "ai_request_cache"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    
    # Тип запроса
    request_type: Mapped[str] = mapped_column(String(50))  # weekly_summary, failure_analysis, advice
    
    # Хеш параметров запроса
    request_hash: Mapped[str] = mapped_column(String(64))
    
    # Ответ
    response_data: Mapped[str] = mapped_column(Text)
    
    # TTL
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class HabitInsight(Base):
    """AI-инсайты о привычках пользователя."""
    
    __tablename__ = "habit_insights"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    habit_id: Mapped[int] = mapped_column(Integer, ForeignKey("habits.id", ondelete="CASCADE"))
    
    # Тип инсайта
    insight_type: Mapped[str] = mapped_column(String(50))  # pattern, suggestion, prediction
    
    # Содержание
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    
    # Метаданные
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_read: Mapped[bool] = mapped_column(default=False)


# Database engine и session
engine = create_async_engine(
    settings.database_url,
    echo=settings.log_level == "DEBUG"
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """Dependency для получения сессии БД."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
