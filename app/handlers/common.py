# -*- coding: utf-8 -*-
"""
Common handlers - main menu, start, help
"""
import logging
from datetime import date
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.habit import Habit, HabitLog
from app.models.payment import Payment
from app.models.achievement import Achievement

logger = logging.getLogger(__name__)
router = Router()


class QuickStats:
    """Quick statistics for dashboard"""
    def __init__(self):
        self.total_today = 0
        self.completed_today = 0
        self.current_streak = 0
        self.upcoming_payments = 0
        self.new_achievements = 0


async def get_quick_stats(db: AsyncSession, user_id: int) -> QuickStats:
    """Get quick statistics for user dashboard"""
    stats = QuickStats()
    today = date.today()
    
    # Get active habits count
    habits_result = await db.execute(
        select(func.count(Habit.id)).where(
            and_(
                Habit.user_id == user_id,
                Habit.is_active == True
            )
        )
    )
    stats.total_today = habits_result.scalar() or 0
    
    # Get completed today
    completed_result = await db.execute(
        select(func.count(HabitLog.id)).where(
            and_(
                HabitLog.user_id == user_id,
                HabitLog.completed_date == today,
                HabitLog.status == 'completed'
            )
        )
    )
    stats.completed_today = completed_result.scalar() or 0
    
    # Get user streak
    user_result = await db.execute(
        select(User.current_streak).where(User.id == user_id)
    )
    stats.current_streak = user_result.scalar() or 0
    
    # Get upcoming payments (next 7 days)
    payments_result = await db.execute(
        select(func.count(Payment.id)).where(
            and_(
                Payment.user_id == user_id,
                Payment.is_completed == False,
                Payment.date <= today + date.resolution * 7,
                Payment.date >= today
            )
        )
    )
    stats.upcoming_payments = payments_result.scalar() or 0
    
    return stats


@router.message(CommandStart())
async def cmd_start(message: Message, db: AsyncSession):
    """Enhanced main menu"""
    user_id = message.from_user.id
    
    # Create or update user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        db.add(user)
        await db.commit()
        logger.info(f"New user registered: {user_id}")
    
    # Get statistics
    stats = await get_quick_stats(db, user_id)
    
    # Build welcome message
    text = f"👋 <b>Привет, {message.from_user.first_name}!</b>\n\n"
    
    # Today's progress
    progress_percent = 0
    if stats.total_today > 0:
        progress_percent = int((stats.completed_today / stats.total_today) * 100)
    
    text += f"📊 Сегодня: {stats.completed_today}/{stats.total_today} привычек"
    if stats.total_today > 0:
        bar = "█" * (progress_percent // 20) + "░" * (5 - progress_percent // 20)
        text += f"\n[{bar}] {progress_percent}%"
    text += "\n"
    
    if stats.current_streak > 0:
        text += f"🔥 Общая серия: {stats.current_streak} дней\n"
    
    # Financial reminders
    if stats.upcoming_payments > 0:
        text += f"💰 Платежей скоро: {stats.upcoming_payments}\n"
    
    text += "\n<b>🚀 Что будем делать?</b>"
    
    # Enhanced keyboard
    kb = InlineKeyboardBuilder()
    
    # Main actions
    kb.button(text="➕ Добавить привычку", callback_data="menu:add_habit")
    kb.button(text="🎯 Мои привычки", callback_data="menu:habits")
    kb.adjust(1)
    
    # Secondary actions
    kb.button(text="💰 Финансы", callback_data="menu:finances")
    kb.button(text="📊 Статистика", callback_data="menu:stats")
    kb.button(text="🤖 AI-совет", callback_data="menu:ai")
    kb.adjust(3)
    
    # Settings
    kb.button(text="⚙️ Настройки", callback_data="menu:settings")
    kb.button(text="❓ Помощь", callback_data="menu:help")
    kb.adjust(2)
    
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help message"""
    text = (
        "<b>📖 Помощь по HabitMax</b>\n\n"
        
        "<b>🎯 Привычки:</b>\n"
        "/add_habit — добавить новую привычку\n"
        "/my_habits — список ваших привычек\n"
        "/stats — ваша статистика\n"
        "/achievements — ваши достижения\n\n"
        
        "<b>💰 Финансы:</b>\n"
        "/add_payment — добавить платёж или вклад\n"
        "/my_finances — финансовые напоминания\n\n"
        
        "<b>⚙️ Другое:</b>\n"
        "/start — главное меню\n"
        "/help — эта справка\n\n"
        
        "<i>💡 Совет: Нажимайте кнопку ✅ как можно быстре после выполнения привычки!</i>"
    )
    await message.answer(text, parse_mode="HTML")


# ============================================================================
# Menu callbacks
# ============================================================================

@router.callback_query(F.data == "menu:add_habit")
async def menu_add_habit(callback: CallbackQuery, state: FSMContext):
    """Add habit from menu"""
    from app.handlers.habits import cmd_add_habit
    await cmd_add_habit(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "menu:habits")
async def menu_habits(callback: CallbackQuery, db: AsyncSession):
    """My habits from menu"""
    from app.handlers.habits import cmd_my_habits
    await cmd_my_habits(callback.message, db)
    await callback.answer()


@router.callback_query(F.data == "menu:finances")
async def menu_finances(callback: CallbackQuery, db: AsyncSession):
    """Finances from menu"""
    from app.handlers.finance import show_finances_list
    await show_finances_list(callback, db, callback.from_user.id, edit=True)
    await callback.answer()


@router.callback_query(F.data == "menu:stats")
async def menu_stats(callback: CallbackQuery, db: AsyncSession):
    """Stats from menu"""
    from app.handlers.habits import cmd_stats
    await cmd_stats(callback.message, db)
    await callback.answer()


@router.callback_query(F.data == "menu:ai")
async def menu_ai(callback: CallbackQuery):
    """AI advice from menu"""
    text = (
        "🤖 <b>AI-советник</b>\n\n"
        "<i>Функция в разработке...</i>\n\n"
        "Совет дня:\n"
        "💡 Начинайте с малого! Лучше 5 минут ежедневно, "
        "чем 2 часа раз в неделю."
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu:settings")
async def menu_settings(callback: CallbackQuery):
    """Settings from menu"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔔 Уведомления", callback_data="settings:notifications")
    kb.button(text="🌍 Часовой пояс", callback_data="settings:timezone")
    kb.button(text="🤖 AI-режим", callback_data="settings:ai")
    kb.button(text="« Назад", callback_data="menu:back")
    kb.adjust(1)
    
    text = (
        "⚙️ <b>Настройки</b>\n\n"
        "Выберите раздел для настройки:"
    )
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def menu_help(callback: CallbackQuery):
    """Help from menu"""
    await cmd_help(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu:back")
async def menu_back(callback: CallbackQuery, db: AsyncSession):
    """Back to main menu"""
    await cmd_start(callback.message, db)
    await callback.answer()


# ============================================================================
# Settings handlers
# ============================================================================

@router.callback_query(F.data == "settings:notifications")
async def settings_notifications(callback: CallbackQuery):
    """Notification settings"""
    text = (
        "🔔 <b>Уведомления</b>\n\n"
        "Настройка времени напоминаний о привычках.\n\n"
        "<i>Функция в разработке...</i>"
    )
    await callback.answer(text, show_alert=True)


@router.callback_query(F.data == "settings:timezone")
async def settings_timezone(callback: CallbackQuery):
    """Timezone settings"""
    text = (
        "🌍 <b>Часовой пояс</b>\n\n"
        "Текущий часовой пояс: Europe/Moscow\n\n"
        "<i>Функция в разработке...</i>"
    )
    await callback.answer(text, show_alert=True)


@router.callback_query(F.data == "settings:ai")
async def settings_ai(callback: CallbackQuery):
    """AI settings"""
    text = (
        "🤖 <b>AI-режим</b>\n\n"
        "Включить AI-рекомендации и анализ.\n\n"
        "<i>Функция в разработке...</i>"
    )
    await callback.answer(text, show_alert=True)
