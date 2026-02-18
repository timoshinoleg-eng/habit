"""
Роутер для работы с привычками.
"""

from datetime import date, datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_current_user_id
from api.models.base import get_db
from api.schemas.habits import (
    HabitCompleteRequest,
    HabitCompleteResponse,
    HabitCreate,
    HabitListResponse,
    HabitResponse,
    HabitUpdate,
    WeeklyProgress,
    DayProgress
)
from app.models import Habit, HabitLog

router = APIRouter()


@router.get("", response_model=HabitListResponse)
async def get_habits(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить список привычек пользователя."""
    result = await db.execute(
        select(Habit).where(
            and_(Habit.user_id == user_id, Habit.is_active == True)
        )
    )
    habits = result.scalars().all()
    
    # Считаем выполненные сегодня
    completed_today = sum(1 for h in habits if h.is_completed_today)
    
    return HabitListResponse(
        habits=[HabitResponse.model_validate(h) for h in habits],
        total=len(habits),
        completed_today=completed_today
    )


@router.post("", response_model=HabitResponse)
async def create_habit(
    habit: HabitCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую привычку."""
    from datetime import time as dt_time
    
    # Преобразуем время
    reminder_time = None
    if habit.reminder_time:
        reminder_time = dt_time(
            hour=habit.reminder_time.hour,
            minute=habit.reminder_time.minute
        )
    
    new_habit = Habit(
        user_id=user_id,
        name=habit.name,
        description=habit.description,
        emoji=habit.emoji,
        reminder_time=reminder_time,
        frequency=habit.frequency,
        target_days=habit.target_days
    )
    
    db.add(new_habit)
    await db.commit()
    await db.refresh(new_habit)
    
    return HabitResponse.model_validate(new_habit)


@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(
    habit_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить конкретную привычку."""
    result = await db.execute(
        select(Habit).where(
            and_(Habit.id == habit_id, Habit.user_id == user_id)
        )
    )
    habit = result.scalar_one_or_none()
    
    if not habit:
        raise HTTPException(status_code=404, detail="Привычка не найдена")
    
    return HabitResponse.model_validate(habit)


@router.patch("/{habit_id}", response_model=HabitResponse)
async def update_habit(
    habit_id: int,
    update: HabitUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Обновить привычку."""
    result = await db.execute(
        select(Habit).where(
            and_(Habit.id == habit_id, Habit.user_id == user_id)
        )
    )
    habit = result.scalar_one_or_none()
    
    if not habit:
        raise HTTPException(status_code=404, detail="Привычка не найдена")
    
    # Обновляем поля
    update_data = update.model_dump(exclude_unset=True)
    
    # Особая обработка для reminder_time
    if "reminder_time" in update_data and update_data["reminder_time"]:
        from datetime import time as dt_time
        t = update_data["reminder_time"]
        update_data["reminder_time"] = dt_time(hour=t.hour, minute=t.minute)
    
    for field, value in update_data.items():
        setattr(habit, field, value)
    
    await db.commit()
    await db.refresh(habit)
    
    return HabitResponse.model_validate(habit)


@router.delete("/{habit_id}")
async def delete_habit(
    habit_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Удалить привычку (мягкое удаление - деактивация)."""
    result = await db.execute(
        select(Habit).where(
            and_(Habit.id == habit_id, Habit.user_id == user_id)
        )
    )
    habit = result.scalar_one_or_none()
    
    if not habit:
        raise HTTPException(status_code=404, detail="Привычка не найдена")
    
    habit.is_active = False
    await db.commit()
    
    return {"success": True, "message": "Привычка удалена"}


@router.post("/{habit_id}/complete", response_model=HabitCompleteResponse)
async def complete_habit(
    habit_id: int,
    data: HabitCompleteRequest = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Отметить привычку выполненной."""
    result = await db.execute(
        select(Habit).where(
            and_(Habit.id == habit_id, Habit.user_id == user_id)
        )
    )
    habit = result.scalar_one_or_none()
    
    if not habit:
        raise HTTPException(status_code=404, detail="Привычка не найдена")
    
    # Создаем лог
    log = HabitLog(
        habit_id=habit_id,
        user_id=user_id,
        completed_date=date.today(),
        status="completed",
        notes=data.notes if data else None,
        mood=data.mood if data else None,
        completed_at=datetime.utcnow()
    )
    
    # Обновляем привычку
    habit.total_completions += 1
    habit.current_streak += 1
    if habit.current_streak > habit.best_streak:
        habit.best_streak = habit.current_streak
    
    db.add(log)
    await db.commit()
    
    # Проверяем milestones
    is_milestone = habit.current_streak in [7, 21, 30, 60, 100]
    
    return HabitCompleteResponse(
        success=True,
        new_streak=habit.current_streak,
        message=f"Отлично! 🔥 Серия: {habit.current_streak} дней",
        is_milestone=is_milestone
    )


@router.post("/{habit_id}/skip")
async def skip_habit(
    habit_id: int,
    reason: str = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Отметить пропуск привычки с причиной."""
    result = await db.execute(
        select(Habit).where(
            and_(Habit.id == habit_id, Habit.user_id == user_id)
        )
    )
    habit = result.scalar_one_or_none()
    
    if not habit:
        raise HTTPException(status_code=404, detail="Привычка не найдена")
    
    # Создаем лог
    log = HabitLog(
        habit_id=habit_id,
        user_id=user_id,
        completed_date=date.today(),
        status="skipped",
        notes=reason,
        completed_at=datetime.utcnow()
    )
    
    # Сбрасываем серию
    habit.current_streak = 0
    
    db.add(log)
    await db.commit()
    
    return {"success": True, "message": "Записано. Не сдавайся! 💪"}


@router.get("/progress/weekly", response_model=WeeklyProgress)
async def get_weekly_progress(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить прогресс за последние 7 дней."""
    today = date.today()
    week_start = today - timedelta(days=6)
    
    # Получаем все привычки пользователя
    result = await db.execute(
        select(Habit).where(
            and_(Habit.user_id == user_id, Habit.is_active == True)
        )
    )
    habits = result.scalars().all()
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
    
    # Группируем по дням
    days = []
    total_completed = 0
    
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_logs = [l for l in logs if l.completed_date == day and l.status == "completed"]
        completed = len(day_logs)
        total_completed += completed
        
        days.append(DayProgress(
            date=day,
            completed=completed,
            total=total_habits,
            percentage=(completed / max(total_habits, 1)) * 100
        ))
    
    return WeeklyProgress(
        week_start=week_start,
        week_end=today,
        days=days,
        total_completed=total_completed,
        total_habits=total_habits * 7,
        average_percentage=sum(d.percentage for d in days) / 7
    )
