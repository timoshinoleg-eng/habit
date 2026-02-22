# -*- coding: utf-8 -*-
"""
Habits handlers - optimized for speed
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from functools import lru_cache
from typing import Dict, Optional, List

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit, HabitLog
from app.models.user import User
from app.models.achievement import Achievement
from config.settings import ACHIEVEMENTS
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)
router = Router()

# Simple in-memory cache
_habits_cache: Dict[str, dict] = {}
_streak_cache: Dict[str, int] = {}


class AddHabitFSM(StatesGroup):
    """FSM for adding habit"""
    name = State()
    description = State()
    reminder_time = State()
    emoji = State()
    confirm = State()


# ============================================================================
# Cache functions
# ============================================================================

def get_cache_key(user_id: int, habit_id: int) -> str:
    """Generate cache key"""
    return f"{user_id}:{habit_id}"


def cache_habit(habit_id: int, user_id: int, data: dict):
    """Cache habit data"""
    cache_key = get_cache_key(user_id, habit_id)
    _habits_cache[cache_key] = data


def get_cached_habit(user_id: int, habit_id: int) -> Optional[dict]:
    """Get cached habit data"""
    cache_key = get_cache_key(user_id, habit_id)
    return _habits_cache.get(cache_key)


async def preload_habits_cache(db: AsyncSession):
    """Preload active habits to cache on startup"""
    result = await db.execute(
        select(Habit).where(Habit.is_active == True)
    )
    habits = result.scalars().all()
    
    for habit in habits:
        cache_key = get_cache_key(habit.user_id, habit.id)
        _habits_cache[cache_key] = {
            'id': habit.id,
            'user_id': habit.user_id,
            'name': habit.name,
            'emoji': habit.emoji,
            'current_streak': habit.current_streak or 0,
            'best_streak': habit.best_streak or 0,
        }
    
    logger.info(f"Preloaded {len(habits)} habits to cache")


# ============================================================================
# Fast habit completion handler
# ============================================================================

@router.callback_query(F.data.startswith("done:"))
async def fast_done_handler(callback: CallbackQuery, db: AsyncSession):
    """
    Ultra-fast habit completion handler (< 200ms response)
    Strategy:
    1. Instant user feedback
    2. Optimistic UI update
    3. Heavy operations in background
    """
    habit_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    cache_key = get_cache_key(user_id, habit_id)
    
    # 1. INSTANT RESPONSE (< 50ms)
    await callback.answer("✅ Зачтено!", show_alert=False)
    
    # 2. GET DATA (from cache or quick query)
    habit_data = get_cached_habit(user_id, habit_id)
    
    if not habit_data:
        # Optimized query: only needed fields
        result = await db.execute(
            select(Habit.id, Habit.name, Habit.current_streak, 
                   Habit.best_streak, Habit.emoji, Habit.target_days)
            .where(Habit.id == habit_id)
        )
        row = result.first()
        if not row:
            await callback.message.edit_text("❌ Привычка не найдена")
            return
        
        habit_data = {
            'id': row.id,
            'name': row.name,
            'current_streak': row.current_streak or 0,
            'best_streak': row.best_streak or 0,
            'emoji': row.emoji or '✅',
            'target_days': row.target_days,
        }
        cache_habit(habit_id, user_id, habit_data)
    
    # 3. OPTIMISTIC UI UPDATE (instant)
    new_streak = habit_data['current_streak'] + 1
    is_new_record = new_streak > habit_data['best_streak']
    
    # Progress emoji
    if new_streak >= 100:
        progress_emoji = "👑"
    elif new_streak >= 30:
        progress_emoji = "🏆"
    elif new_streak >= 7:
        progress_emoji = "🔥"
    elif new_streak >= 3:
        progress_emoji = "⚡"
    else:
        progress_emoji = "✨"
    
    text = f"{habit_data['emoji']} <b>{habit_data['name']}</b>\n"
    text += "─" * 20 + "\n"
    text += f"{progress_emoji} Серия: {new_streak} дней"
    
    if is_new_record:
        text += " 🎉 Новый рекорд!"
    text += "\n"
    
    # Progress bar if target set
    if habit_data.get('target_days'):
        progress = min(100, int((new_streak / habit_data['target_days']) * 100))
        bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
        text += f"\n🎯 Цель: [{bar}] {progress}%\n"
    
    text += "\n<i>Что дальше?</i>"
    
    # Fast keyboard
    kb = InlineKeyboardBuilder()
    kb.button(text="📷 Фото", callback_data=f"photo:{habit_id}")
    kb.button(text="📝 Заметка", callback_data=f"note:{habit_id}")
    kb.button(text="➡️ Далее", callback_data="show:next_habit")
    kb.adjust(3)
    
    # Update message (main UI response)
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    
    # 4. HEAVY OPERATIONS - BACKGROUND (don't block UI)
    asyncio.create_task(
        _save_completion_async(db, habit_id, user_id, new_streak, cache_key, habit_data)
    )


async def _save_completion_async(
    db: AsyncSession, 
    habit_id: int, 
    user_id: int, 
    new_streak: int,
    cache_key: str,
    habit_data: dict
):
    """Background save operation"""
    from app.models.base import AsyncSessionLocal
    
    try:
        async with AsyncSessionLocal() as session:
            # Create log entry
            log = HabitLog(
                habit_id=habit_id,
                user_id=user_id,
                completed_date=date.today(),
                status='completed'
            )
            session.add(log)
            
            # Update habit
            result = await session.execute(
                select(Habit).where(Habit.id == habit_id)
            )
            habit = result.scalar_one()
            
            habit.current_streak = new_streak
            if new_streak > (habit.best_streak or 0):
                habit.best_streak = new_streak
            habit.total_completions = (habit.total_completions or 0) + 1
            
            await session.commit()
            
            # Update cache
            habit_data['current_streak'] = new_streak
            if new_streak > habit_data['best_streak']:
                habit_data['best_streak'] = new_streak
            _habits_cache[cache_key] = habit_data
            
            # Check achievements
            await check_and_grant_achievements(user_id, new_streak, session)
            
    except Exception as e:
        logger.error(f"Error saving completion: {e}")


# ============================================================================
# Achievement system
# ============================================================================

async def check_and_grant_achievements(user_id: int, streak: int, db: AsyncSession):
    """Check and grant achievements based on streak"""
    
    # Check streak achievements
    achievement_type = None
    if streak == 7:
        achievement_type = 'streak_7'
    elif streak == 30:
        achievement_type = 'streak_30'
    elif streak == 100:
        achievement_type = 'streak_100'
    
    if achievement_type:
        await grant_achievement(user_id, achievement_type, db)


async def grant_achievement(user_id: int, achievement_type: str, db: AsyncSession):
    """Grant achievement to user"""
    
    # Check if already granted
    result = await db.execute(
        select(Achievement).where(
            and_(
                Achievement.user_id == user_id,
                Achievement.achievement_type == achievement_type
            )
        )
    )
    if result.scalar_one_or_none():
        return
    
    # Create achievement
    ach_data = ACHIEVEMENTS.get(achievement_type)
    if not ach_data:
        return
    
    achievement = Achievement(
        user_id=user_id,
        achievement_type=achievement_type,
        title=ach_data['title'],
        description=ach_data['description'],
        icon=ach_data['icon']
    )
    db.add(achievement)
    await db.commit()
    
    logger.info(f"Granted achievement {achievement_type} to user {user_id}")


async def notify_achievement(bot, user_id: int, achievement_type: str):
    """Send achievement notification"""
    ach_data = ACHIEVEMENTS.get(achievement_type)
    if not ach_data:
        return
    
    text = f"🏆 <b>Новое достижение!</b>\n\n"
    text += f"{ach_data['icon']} <b>{ach_data['title']}</b>\n"
    text += f"{ach_data['description']}\n\n"
    text += "Продолжайте в том же духе! 💪"
    
    try:
        await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending achievement notification: {e}")


# ============================================================================
# Habit management commands
# ============================================================================

@router.message(Command("add_habit"))
async def cmd_add_habit(message: Message, state: FSMContext):
    """Start adding new habit"""
    await message.answer(
        "🎯 <b>Новая привычка</b>\n\n"
        "Введите название привычки:"
    )
    await state.set_state(AddHabitFSM.name)


@router.message(AddHabitFSM.name)
async def process_habit_name(message: Message, state: FSMContext):
    """Process habit name"""
    await state.update_data(name=message.text.strip())
    await message.answer(
        "📝 Введите описание (или отправьте '-' чтобы пропустить):"
    )
    await state.set_state(AddHabitFSM.description)


@router.message(AddHabitFSM.description)
async def process_habit_description(message: Message, state: FSMContext):
    """Process habit description"""
    description = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=description)
    
    await message.answer(
        "⏰ Введите время напоминания (ЧЧ:ММ) или '-' чтобы пропустить:\n"
        "<i>Например: 09:00</i>",
        parse_mode="HTML"
    )
    await state.set_state(AddHabitFSM.reminder_time)


@router.message(AddHabitFSM.reminder_time)
async def process_habit_time(message: Message, state: FSMContext):
    """Process reminder time"""
    time_text = message.text.strip()
    
    if time_text != "-":
        try:
            datetime.strptime(time_text, "%H:%M")
            await state.update_data(reminder_time=time_text)
        except ValueError:
            await message.answer("❌ Неверный формат. Используйте ЧЧ:ММ")
            return
    else:
        await state.update_data(reminder_time=None)
    
    await message.answer(
        "😀 Выберите эмодзи для привычки (или отправьте '-'):\n"
        "<i>Например: 🏃 📚 💧</i>",
        parse_mode="HTML"
    )
    await state.set_state(AddHabitFSM.emoji)


@router.message(AddHabitFSM.emoji)
async def process_habit_emoji(message: Message, state: FSMContext, db: AsyncSession):
    """Process emoji and save habit"""
    emoji = message.text.strip()
    if emoji == "-":
        emoji = "✅"
    
    await state.update_data(emoji=emoji)
    data = await state.get_data()
    
    try:
        habit = Habit(
            user_id=message.from_user.id,
            name=data['name'],
            description=data.get('description'),
            reminder_time=data.get('reminder_time'),
            emoji=emoji,
            is_active=True
        )
        db.add(habit)
        await db.commit()
        
        # Add to cache
        cache_habit(habit.id, message.from_user.id, {
            'id': habit.id,
            'name': habit.name,
            'emoji': habit.emoji,
            'current_streak': 0,
            'best_streak': 0,
            'target_days': None,
        })
        
        await message.answer(
            f"✅ <b>Привычка добавлена!</b>\n\n"
            f"{emoji} {data['name']}\n"
            f"{'⏰ Напоминание: ' + data['reminder_time'] if data.get('reminder_time') else '🔕 Без напоминания'}\n\n"
            f"Ваши привычки: /my_habits",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error adding habit: {e}")
        await message.answer("❌ Ошибка при сохранении. Попробуйте позже.")
    
    await state.clear()


@router.message(Command("my_habits"))
async def cmd_my_habits(message: Message, db: AsyncSession):
    """Show user's habits"""
    user_id = message.from_user.id
    
    result = await db.execute(
        select(Habit).where(
            and_(
                Habit.user_id == user_id,
                Habit.is_active == True
            )
        ).order_by(Habit.created_at)
    )
    habits = result.scalars().all()
    
    if not habits:
        await message.answer(
            "🎯 У вас пока нет привычек.\n\n"
            "Добавить: /add_habit"
        )
        return
    
    text = "🎯 <b>Ваши привычки</b>\n\n"
    
    # Get today's logs
    today = date.today()
    logs_result = await db.execute(
        select(HabitLog.habit_id).where(
            and_(
                HabitLog.user_id == user_id,
                HabitLog.completed_date == today,
                HabitLog.status == 'completed'
            )
        )
    )
    completed_today = {row[0] for row in logs_result.all()}
    
    kb = InlineKeyboardBuilder()
    
    for habit in habits:
        is_done = habit.id in completed_today
        status = "✅" if is_done else "⭕"
        streak = habit.current_streak or 0
        
        text += f"{habit.emoji} <b>{habit.name}</b> {status}\n"
        text += f"   🔥 Серия: {streak} дней"
        if habit.target_days:
            progress = min(100, int((streak / habit.target_days) * 100))
            text += f" ({progress}%)"
        text += "\n\n"
        
        if not is_done:
            kb.button(
                text=f"{habit.emoji} {habit.name[:20]}",
                callback_data=f"done:{habit.id}"
            )
    
    kb.adjust(1)
    kb.button(text="➕ Добавить", callback_data="habit:add")
    
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


# ============================================================================
# Other handlers
# ============================================================================

@router.callback_query(F.data == "show:next_habit")
async def show_next_habit(callback: CallbackQuery, db: AsyncSession):
    """Show next habit to complete"""
    user_id = callback.from_user.id
    today = date.today()
    
    # Get incomplete habits
    logs_result = await db.execute(
        select(HabitLog.habit_id).where(
            and_(
                HabitLog.user_id == user_id,
                HabitLog.completed_date == today,
                HabitLog.status == 'completed'
            )
        )
    )
    completed_ids = {row[0] for row in logs_result.all()}
    
    result = await db.execute(
        select(Habit).where(
            and_(
                Habit.user_id == user_id,
                Habit.is_active == True,
                Habit.id.notin_(list(completed_ids)) if completed_ids else True
            )
        ).order_by(Habit.reminder_time)
    )
    habits = result.scalars().all()
    
    if not habits:
        await callback.message.edit_text(
            "🎉 <b>Все привычки выполнены!</b>\n\n"
            "Отличная работа! 💪",
            parse_mode="HTML"
        )
        return
    
    # Show first incomplete habit
    habit = habits[0]
    text = format_habit_card(habit, [], today)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Выполнено", callback_data=f"done:{habit.id}")
    kb.button(text="➡️ Следующая", callback_data="show:next_habit")
    kb.adjust(2)
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "habit:add")
async def habit_add_callback(callback: CallbackQuery, state: FSMContext):
    """Add habit from callback"""
    await cmd_add_habit(callback.message, state)
    await callback.answer()


def format_habit_card(habit: Habit, logs: List[HabitLog], today: date = None) -> str:
    """Format beautiful habit card"""
    if today is None:
        today = date.today()
    
    text = f"{habit.emoji or '✅'} <b>{habit.name}</b>\n"
    text += "─" * 20 + "\n"
    
    # Streak progress
    streak = habit.current_streak or 0
    best = habit.best_streak or 0
    
    if streak > 0:
        fire = "🔥" if streak >= 7 else "⚡"
        text += f"{fire} Серия: {streak} дней"
        if streak == best:
            text += " (рекорд!)"
        text += "\n"
    
    # Week progress
    week_progress = get_week_progress(logs, today)
    text += f"📊 Неделя: {week_progress}\n"
    
    # Reminder
    if habit.reminder_time:
        text += f"⏰ Напоминание: {habit.reminder_time}\n"
    
    # Target progress
    if habit.target_days:
        progress = min(100, int((streak / habit.target_days) * 100))
        bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
        text += f"🎯 Цель: {streak}/{habit.target_days} дней\n"
        text += f"[{bar}] {progress}%\n"
    
    return text


def get_week_progress(logs: List[HabitLog], today: date = None) -> str:
    """Get week progress as emoji string"""
    if today is None:
        today = date.today()
    
    # Build completed dates set
    completed_dates = {
        log.completed_date for log in logs 
        if log.status == 'completed'
    }
    
    week_days = []
    for i in range(6, -1, -1):  # Last 7 days
        check_date = today - timedelta(days=i)
        is_done = check_date in completed_dates
        
        if check_date == today:
            week_days.append("◉" if is_done else "◯")  # Today
        elif check_date > today:
            week_days.append("·")  # Future
        else:
            week_days.append("✓" if is_done else "✗")  # Past
    
    return "".join(week_days)


# ============================================================================
# Stats command
# ============================================================================

@router.message(Command("stats"))
async def cmd_stats(message: Message, db: AsyncSession):
    """Show user statistics"""
    user_id = message.from_user.id
    
    # Get user stats
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        return
    
    # Get habit stats
    habits_result = await db.execute(
        select(
            func.count(Habit.id).label('total'),
            func.sum(Habit.total_completions).label('completions')
        ).where(Habit.user_id == user_id)
    )
    habit_stats = habits_result.first()
    
    # Get achievements
    ach_result = await db.execute(
        select(Achievement).where(Achievement.user_id == user_id)
    )
    achievements = ach_result.scalars().all()
    
    text = f"📊 <b>Статистика</b>\n\n"
    text += f"🔥 Текущая серия: {user.current_streak or 0} дней\n"
    text += f"🏆 Лучшая серия: {user.best_streak or 0} дней\n"
    text += f"📋 Всего привычек: {habit_stats.total or 0}\n"
    text += f"✅ Всего выполнено: {habit_stats.completions or 0}\n"
    
    if achievements:
        text += f"\n🏅 Достижения ({len(achievements)}):\n"
        for ach in achievements:
            text += f"{ach.icon} {ach.title}\n"
    
    await message.answer(text, parse_mode="HTML")


# ============================================================================
# Achievements command
# ============================================================================

@router.message(Command("achievements"))
async def cmd_achievements(message: Message, db: AsyncSession):
    """Show user achievements"""
    user_id = message.from_user.id
    
    result = await db.execute(
        select(Achievement).where(
            Achievement.user_id == user_id
        ).order_by(Achievement.unlocked_at.desc())
    )
    achievements = result.scalars().all()
    
    if not achievements:
        await message.answer(
            "🏅 <b>Достижения</b>\n\n"
            "Пока нет разблокированных достижений.\n"
            "Продолжайте выполнять привычки! 💪",
            parse_mode="HTML"
        )
        return
    
    text = f"🏅 <b>Ваши достижения</b> ({len(achievements)})\n\n"
    
    for ach in achievements:
        text += f"{ach.icon} <b>{ach.title}</b>\n"
        text += f"   {ach.description}\n"
        text += f"   <i>Получено: {ach.unlocked_at.strftime('%d.%m.%Y')}</i>\n\n"
    
    await message.answer(text, parse_mode="HTML")
