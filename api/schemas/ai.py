"""
Pydantic схемы для AI-функций.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WeeklySummaryData(BaseModel):
    """Данные для генерации еженедельного саммари."""
    week_start: date
    week_end: date
    total_habits: int
    completed_count: int
    skipped_count: int
    failed_count: int
    best_streak: int
    best_habit: Optional[str] = None
    worst_habit: Optional[str] = None
    daily_completion_rates: List[float]  # Процент выполнения по дням


class WeeklySummaryResponse(BaseModel):
    """Ответ с еженедельным саммари."""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    week_start: date
    week_end: date
    
    # Статистика
    total_habits: int
    completed_count: int
    skipped_count: int
    best_streak: int
    completion_rate: float  # Процент выполнения
    
    # AI-текст
    ai_summary: str
    motivational_message: str
    tips: List[str]
    
    # Метаданные
    generated_at: datetime
    is_cached: bool = False
    share_text: str  # Текст для шеринга в сторис


class FailurePattern(BaseModel):
    """Паттерн срыва."""
    day_of_week: str
    time_of_day: Optional[str] = None
    reason: Optional[str] = None
    frequency: int


class FailureAnalysisRequest(BaseModel):
    """Запрос на анализ срывов."""
    habit_id: Optional[int] = None  # Если None - анализируем все привычки
    period_days: int = Field(default=30, ge=7, le=90)


class Strategy(BaseModel):
    """Стратегия преодоления."""
    title: str
    description: str
    action_steps: List[str]
    difficulty: str  # easy, medium, hard
    estimated_effectiveness: int = Field(..., ge=1, le=5)


class FailureAnalysisResponse(BaseModel):
    """Ответ с анализом срывов."""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    habit_id: Optional[int] = None
    habit_name: Optional[str] = None
    
    # Данные
    failure_count: int
    failure_rate: float  # Процент срывов
    common_patterns: List[FailurePattern]
    skip_reasons: List[str]
    
    # AI-анализ
    empathetic_message: str
    root_causes: List[str]
    strategies: List[Strategy]
    
    # Метаданные
    generated_at: datetime
    is_cached: bool = False


class AIAdviceRequest(BaseModel):
    """Запрос на AI-совет."""
    context: str = Field(..., min_length=5, max_length=500)
    habit_id: Optional[int] = None


class AIAdviceResponse(BaseModel):
    """Ответ с AI-советом."""
    advice: str
    category: str  # motivation, strategy, reminder
    confidence: float = Field(..., ge=0, le=1)
    is_cached: bool = False


class HabitSuggestion(BaseModel):
    """Предложение AI для новой привычки."""
    suggested_name: str
    suggested_emoji: str
    suggested_time: Optional[str] = None
    category: str
    reasoning: str


class ChatMessage(BaseModel):
    """Сообщение в чате с AI."""
    role: str  # user, assistant
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AIChatRequest(BaseModel):
    """Запрос в AI-чат."""
    message: str = Field(..., min_length=1, max_length=1000)
    history: List[ChatMessage] = []


class AIChatResponse(BaseModel):
    """Ответ AI-чата."""
    message: str
    suggestions: List[str] = []  # Предложенные быстрые ответы
    related_habits: List[int] = []  # ID связанных привычек
