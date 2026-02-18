"""
Роутер для AI-функций.
"""

from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_current_user_id
from api.models.base import get_db
from api.schemas.ai import (
    AIAdviceRequest,
    AIAdviceResponse,
    AIChatRequest,
    AIChatResponse,
    FailureAnalysisRequest,
    FailureAnalysisResponse,
    WeeklySummaryResponse,
    FailurePattern
)
from api.services.ai_service import AIService
from app.models import Habit, HabitLog

router = APIRouter()


def get_ai_service():
    return AIService()


@router.get("/weekly-summary", response_model=WeeklySummaryResponse)
async def get_weekly_summary(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ai: AIService = Depends(get_ai_service)
):
    """Получить еженедельное AI-саммари."""
    
    # Определяем период (последние 7 дней)
    today = date.today()
    week_start = today - timedelta(days=6)
    
    # Получаем статистику
    habits_result = await db.execute(
        select(Habit).where(
            and_(Habit.user_id == user_id, Habit.is_active == True)
        )
    )
    habits = habits_result.scalars().all()
    total_habits = len(habits)
    
    # Получаем логи за неделю
    logs_result = await db.execute(
        select(HabitLog).where(
            and_(
                HabitLog.user_id == user_id,
                HabitLog.completed_date >= week_start,
                HabitLog.completed_date <= today
            )
        )
    )
    logs = logs_result.scalars().all()
    
    completed = sum(1 for l in logs if l.status == "completed")
    skipped = sum(1 for l in logs if l.status == "skipped")
    
    # Находим лучшую привычку
    habit_stats = {}
    for log in logs:
        if log.status == "completed":
            habit_stats[log.habit_id] = habit_stats.get(log.habit_id, 0) + 1
    
    best_habit_id = max(habit_stats, key=habit_stats.get) if habit_stats else None
    best_habit = next((h for h in habits if h.id == best_habit_id), None)
    
    # Лучшая серия
    best_streak = max((h.current_streak for h in habits), default=0)
    
    # Процент выполнения по дням
    daily_rates = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_completed = sum(1 for l in logs if l.completed_date == day and l.status == "completed")
        daily_rates.append((day_completed / max(total_habits, 1)) * 100)
    
    # Создаем данные для AI
    from api.schemas.ai import WeeklySummaryData
    summary_data = WeeklySummaryData(
        week_start=week_start,
        week_end=today,
        total_habits=total_habits,
        completed_count=completed,
        skipped_count=skipped,
        failed_count=0,
        best_streak=best_streak,
        best_habit=best_habit.name if best_habit else None,
        worst_habit=None,
        daily_completion_rates=daily_rates
    )
    
    # Генерируем саммари
    result = await ai.generate_weekly_summary(db, user_id, summary_data)
    return result


@router.post("/failure-analysis", response_model=FailureAnalysisResponse)
async def analyze_failures(
    request: FailureAnalysisRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ai: AIService = Depends(get_ai_service)
):
    """Проанализировать срывы привычки."""
    
    period_start = date.today() - timedelta(days=request.period_days)
    
    # Получаем привычку
    habit_name = None
    if request.habit_id:
        result = await db.execute(
            select(Habit).where(
                and_(Habit.id == request.habit_id, Habit.user_id == user_id)
            )
        )
        habit = result.scalar_one_or_none()
        if habit:
            habit_name = habit.name
    
    # Получаем логи с пропусками
    logs_result = await db.execute(
        select(HabitLog).where(
            and_(
                HabitLog.user_id == user_id,
                HabitLog.completed_date >= period_start,
                HabitLog.status == "skipped"
            )
        )
    )
    logs = logs_result.scalars().all()
    
    if not logs:
        return FailureAnalysisResponse(
            habit_id=request.habit_id,
            habit_name=habit_name,
            failure_count=0,
            failure_rate=0,
            common_patterns=[],
            skip_reasons=[],
            empathetic_message="Отлично! У тебя нет срывов. Продолжай в том же духе! 🎉",
            root_causes=[],
            strategies=[],
            generated_at=datetime.utcnow(),
            is_cached=False
        )
    
    # Анализируем паттерны
    patterns = {}
    reasons = []
    
    for log in logs:
        # День недели
        weekday = log.completed_date.strftime("%A")
        key = weekday
        patterns[key] = patterns.get(key, 0) + 1
        
        # Причины
        if log.notes:
            reasons.append(log.notes)
    
    # Формируем паттерны
    failure_patterns = [
        FailurePattern(
            day_of_week=day,
            time_of_day=None,
            reason=None,
            frequency=count
        )
        for day, count in sorted(patterns.items(), key=lambda x: -x[1])[:3]
    ]
    
    # Анализ через AI
    result = await ai.analyze_failures(
        db, user_id, habit_name, len(logs), reasons[:5], failure_patterns
    )
    
    return result


@router.post("/advice", response_model=AIAdviceResponse)
async def get_advice(
    request: AIAdviceRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ai: AIService = Depends(get_ai_service)
):
    """Получить AI-совет."""
    
    habit_name = None
    if request.habit_id:
        result = await db.execute(
            select(Habit).where(
                and_(Habit.id == request.habit_id, Habit.user_id == user_id)
            )
        )
        habit = result.scalar_one_or_none()
        if habit:
            habit_name = habit.name
    
    result = await ai.get_advice(db, user_id, request.context, habit_name)
    return result


@router.post("/chat", response_model=AIChatResponse)
async def chat_with_ai(
    request: AIChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ai: AIService = Depends(get_ai_service)
):
    """Чат с AI-ассистентом."""
    
    # Формируем промпт из истории
    messages = [
        {"role": "system", "content": "Ты — дружелюбный ассистент по привычкам. Отвечай кратко и по существу."}
    ]
    
    for msg in request.history[-5:]:  # Последние 5 сообщений
        messages.append({"role": msg.role, "content": msg.content})
    
    messages.append({"role": "user", "content": request.message})
    
    response = await ai._make_request(messages, max_tokens=300)
    
    if response:
        return AIChatResponse(
            message=response.strip(),
            suggestions=["Спасибо!", "Расскажи подробнее", "У меня есть вопрос"],
            related_habits=[]
        )
    else:
        return AIChatResponse(
            message="Извини, я временно недоступен. Попробуй позже!",
            suggestions=[],
            related_habits=[]
        )


@router.post("/suggest-habit")
async def suggest_habit(
    query: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ai: AIService = Depends(get_ai_service)
):
    """Получить AI-предложение для новой привычки."""
    
    prompt = f"""Пользователь хочет завести привычку: "{query}"

Предложи:
1. Улучшенное название (краткое, конкретное)
2. Подходящий эмодзи
3. Категорию (здоровье, продуктивность, обучение, спорт, другое)
4. Лучшее время для напоминания
5. Краткое обоснование (1 предложение)

Ответ в формате JSON:
{{
    "suggested_name": "...",
    "suggested_emoji": "...",
    "category": "...",
    "suggested_time": "...",
    "reasoning": "..."
}}"""

    messages = [
        {"role": "system", "content": "Ты — эксперт по привычкам. Отвечай только в JSON формате."},
        {"role": "user", "content": prompt}
    ]
    
    response = await ai._make_request(messages, max_tokens=300)
    
    if response:
        try:
            import json
            data = json.loads(response.strip())
            return data
        except:
            return {
                "suggested_name": query,
                "suggested_emoji": "✨",
                "category": "другое",
                "suggested_time": "09:00",
                "reasoning": "Отличная привычка для начала!"
            }
    else:
        return {
            "suggested_name": query,
            "suggested_emoji": "✨",
            "category": "другое",
            "suggested_time": "09:00",
            "reasoning": "Отличная привычка для начала!"
        }
