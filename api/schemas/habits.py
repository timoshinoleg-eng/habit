"""
Pydantic схемы для привычек.
"""

from datetime import date, datetime, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HabitBase(BaseModel):
    """Базовая схема привычки."""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    emoji: str = Field(default="✅", max_length=10)
    reminder_time: Optional[time] = None
    frequency: str = Field(default="daily")
    target_days: int = Field(default=21, ge=1, le=365)


class HabitCreate(HabitBase):
    """Схема создания привычки."""
    pass


class HabitUpdate(BaseModel):
    """Схема обновления привычки."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    emoji: Optional[str] = None
    reminder_time: Optional[time] = None
    frequency: Optional[str] = None
    is_active: Optional[bool] = None


class HabitLogSchema(BaseModel):
    """Схема лога выполнения."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    completed_date: date
    status: str
    notes: Optional[str] = None
    mood: Optional[int] = None
    completed_at: Optional[datetime] = None


class HabitResponse(HabitBase):
    """Схема ответа с привычкой."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    is_active: bool
    current_streak: int
    best_streak: int
    total_completions: int
    progress_percentage: float
    is_completed_today: bool
    created_at: datetime
    
    # Последние логи
    recent_logs: List[HabitLogSchema] = []


class HabitListResponse(BaseModel):
    """Список привычек."""
    habits: List[HabitResponse]
    total: int
    completed_today: int


class HabitCompleteRequest(BaseModel):
    """Запрос на отметку выполнения."""
    notes: Optional[str] = None
    mood: Optional[int] = Field(None, ge=1, le=5)


class HabitCompleteResponse(BaseModel):
    """Ответ после отметки выполнения."""
    success: bool
    new_streak: int
    message: str
    is_milestone: bool = False  # Достигнута ли цель (21 день и т.д.)


class DayProgress(BaseModel):
    """Прогресс за день."""
    date: date
    completed: int
    total: int
    percentage: float


class WeeklyProgress(BaseModel):
    """Прогресс за неделю."""
    week_start: date
    week_end: date
    days: List[DayProgress]
    total_completed: int
    total_habits: int
    average_percentage: float
