"""
Роутер для работы с пользователем.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_current_user_id
from api.models.base import get_db
from api.schemas.user import UserResponse, UserSettings, UserStats
from app.models import User, Habit, HabitLog

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить данные текущего пользователя."""
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Статистика
    habits_result = await db.execute(
        select(Habit).where(Habit.user_id == user_id)
    )
    habits = habits_result.scalars().all()
    
    active_habits = sum(1 for h in habits if h.is_active)
    total_completions = sum(h.total_completions for h in habits)
    best_streak = max((h.best_streak for h in habits), default=0)
    
    # Текущая серия
    current_streak = 0
    from datetime import date
    today = date.today()
    
    logs_result = await db.execute(
        select(HabitLog).where(
            HabitLog.user_id == user_id
        )
    )
    logs = logs_result.scalars().all()
    
    # Считаем серию
    check_date = today
    while True:
        day_completed = any(
            l.completed_date == check_date and l.status == "completed"
            for l in logs
        )
        if day_completed:
            current_streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    
    stats = UserStats(
        total_habits=len(habits),
        active_habits=active_habits,
        total_completions=total_completions,
        best_streak=best_streak,
        current_streak=current_streak,
        completion_rate_7d=0,  # TODO: рассчитать
        completion_rate_30d=0
    )
    
    settings = UserSettings(
        ai_enabled=user.ai_enabled,
        notification_enabled=user.notification_enabled,
        timezone=user.timezone,
        theme="system"
    )
    
    return UserResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        settings=settings,
        stats=stats,
        created_at=user.created_at,
        last_active=user.last_active
    )


@router.patch("/settings")
async def update_settings(
    settings: UserSettings,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Обновить настройки пользователя."""
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Обновляем поля
    user.ai_enabled = settings.ai_enabled
    user.notification_enabled = settings.notification_enabled
    user.timezone = settings.timezone
    
    await db.commit()
    
    return {"success": True, "settings": settings}


@router.post("/onboarding/complete")
async def complete_onboarding(
    data: dict,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Завершить онбординг."""
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        user.timezone = data.get("timezone", "UTC")
        await db.commit()
    
    return {"success": True, "message": "Добро пожаловать в HabitMax!"}


from datetime import timedelta
