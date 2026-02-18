"""
Pydantic схемы для пользователя.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class TelegramUser(BaseModel):
    """Данные пользователя из Telegram."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None


class UserStats(BaseModel):
    """Статистика пользователя."""
    total_habits: int
    active_habits: int
    total_completions: int
    best_streak: int
    current_streak: int
    completion_rate_7d: float
    completion_rate_30d: float


class UserSettings(BaseModel):
    """Настройки пользователя."""
    model_config = ConfigDict(from_attributes=True)
    
    ai_enabled: bool = True
    notification_enabled: bool = True
    timezone: str = "UTC"
    theme: str = "system"  # light, dark, system


class UserResponse(BaseModel):
    """Ответ с данными пользователя."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    settings: UserSettings
    stats: UserStats
    created_at: datetime
    last_active: Optional[datetime] = None


class UserOnboardingRequest(BaseModel):
    """Запрос на завершение онбординга."""
    timezone: str = "UTC"
    goals: List[str] = []  # Цели пользователя
