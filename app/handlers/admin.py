"""
Админ-команды для управления ботом.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List

from aiogram import Bot, Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.services.database import DatabaseService
from app.utils.decorators import admin_required
from app.keyboards.reply_keyboards import (
    get_main_menu_keyboard,
    get_admin_menu_keyboard,
    remove_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()


# ==================== Admin Commands ====================

@router.message(Command("admin"))
@admin_required
async def cmd_admin(message: types.Message) -> None:
    """Главное меню администратора."""
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выбери действие:",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("admin_stats"))
@admin_required
async def cmd_admin_stats(
    message: types.Message,
    db: DatabaseService
) -> None:
    """Статистика бота."""
    await message.answer("📊 Собираю статистику...")
    
    try:
        stats = await get_bot_stats(db)
        
        stats_text = (
            f"📊 <b>Статистика HabitMax</b>\n"
            f"<i>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>\n\n"
            f"👥 <b>Пользователи:</b>\n"
            f"  • Всего: <b>{stats['total_users']}</b>\n"
            f"  • Активных сегодня: <b>{stats['active_today']}</b>\n"
            f"  • Новых за 7 дней: <b>{stats['new_last_7_days']}</b>\n\n"
            f"📋 <b>Привычки:</b>\n"
            f"  • Всего создано: <b>{stats['total_habits']}</b>\n"
            f"  • Активных: <b>{stats['active_habits']}</b>\n"
            f"  • Приостановленных: <b>{stats['paused_habits']}</b>\n\n"
            f"✅ <b>Выполнения:</b>\n"
            f"  • Сегодня: <b>{stats['completions_today']}</b>\n"
            f"  • За 7 дней: <b>{stats['completions_week']}</b>\n"
            f"  • Всего: <b>{stats['total_completions']}</b>\n\n"
            f"🔥 <b>Серии:</b>\n"
            f"  • Лучшая серия: <b>{stats['best_streak']}</b> дней\n"
            f"  • Средняя серия: <b>{stats['avg_streak']:.1f}</b> дней\n\n"
            f"🤖 <b>AI:</b>\n"
            f"  • AI включен у: <b>{stats['ai_enabled_count']}</b> пользователей\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:refresh_stats")],
            [InlineKeyboardButton(text="« Назад", callback_data="admin:menu")],
        ])
        
        await message.answer(stats_text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        await message.answer(f"❌ Ошибка при получении статистики: {e}")


@router.callback_query(F.data == "admin:refresh_stats")
@admin_required
async def callback_refresh_stats(
    callback: types.CallbackQuery,
    db: DatabaseService
) -> None:
    """Обновление статистики."""
    await callback.answer("🔄 Обновляю...")
    await cmd_admin_stats(callback.message, db)


@router.callback_query(F.data == "admin:menu")
@admin_required
async def callback_admin_menu(callback: types.CallbackQuery) -> None:
    """Возврат в меню админа."""
    await callback.message.edit_text(
        "🔧 <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="« Закрыть", callback_data="admin:close")],
        ]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:close")
async def callback_close_admin(callback: types.CallbackQuery) -> None:
    """Закрыть админ-панель."""
    await callback.message.delete()
    await callback.answer()


@router.message(Command("broadcast"))
@admin_required
async def cmd_broadcast(message: types.Message, state: FSMContext) -> None:
    """Начало рассылки сообщения всем пользователям."""
    await state.set_state(BroadcastFSM.message)
    
    await message.answer(
        "📢 <b>Рассылка сообщения</b>\n\n"
        "Введи текст сообщения для отправки всем пользователям:\n\n"
        "<i>Можно использовать HTML-разметку:</i>\n"
        "<code>&lt;b&gt;жирный&lt;/b&gt; &lt;i&gt;курсив&lt;/i&gt;</code>\n\n"
        "❌ Отправь /cancel для отмены",
        reply_markup=remove_keyboard(),
        parse_mode="HTML"
    )


# FSM для рассылки
class BroadcastFSM(StatesGroup):
    message = State()
    confirm = State()


@router.message(BroadcastFSM.message)
@admin_required
async def process_broadcast_message(
    message: types.Message,
    state: FSMContext,
    db: DatabaseService
) -> None:
    """Обработка текста рассылки."""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Рассылка отменена",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Сохраняем сообщение
    broadcast_text = message.text
    await state.update_data(broadcast_text=broadcast_text)
    
    # Получаем количество пользователей
    from sqlalchemy import func, select
    from app.models import User
    
    async with db.session_factory() as session:
        result = await session.execute(select(func.count(User.id)))
        user_count = result.scalar()
    
    # Предпросмотр
    preview = (
        f"📢 <b>Предпросмотр рассылки</b>\n"
        f"Получателей: <b>{user_count}</b>\n\n"
        f"---\n{broadcast_text}\n---\n\n"
        f"Отправить это сообщение?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:confirm")],
        [InlineKeyboardButton(text="✏️ Изменить", callback_data="broadcast:edit")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast:cancel")],
    ])
    
    await state.set_state(BroadcastFSM.confirm)
    await message.answer(preview, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "broadcast:confirm")
@admin_required
async def callback_broadcast_confirm(
    callback: types.CallbackQuery,
    state: FSMContext,
    db: DatabaseService,
    bot: Bot
) -> None:
    """Подтверждение и отправка рассылки."""
    await callback.answer("📤 Начинаю рассылку...")
    
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    
    # Получаем всех пользователей
    from sqlalchemy import select
    from app.models import User
    
    async with db.session_factory() as session:
        result = await session.execute(select(User.id))
        user_ids = [row[0] for row in result.all()]
    
    # Отправляем сообщения
    sent = 0
    failed = 0
    
    status_msg = await callback.message.edit_text(
        f"📤 Рассылка: 0/{len(user_ids)} отправлено..."
    )
    
    for i, user_id in enumerate(user_ids):
        try:
            await bot.send_message(
                chat_id=user_id,
                text=broadcast_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Failed to send broadcast to {user_id}: {e}")
        
        # Обновляем статус каждые 10 сообщений
        if (i + 1) % 10 == 0:
            try:
                await status_msg.edit_text(
                    f"📤 Рассылка: {i+1}/{len(user_ids)} отправлено...\n"
                    f"✅ Успешно: {sent}\n"
                    f"❌ Ошибок: {failed}"
                )
            except:
                pass
    
    await state.clear()
    
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 Результаты:\n"
        f"  • Всего пользователей: {len(user_ids)}\n"
        f"  • ✅ Доставлено: {sent}\n"
        f"  • ❌ Ошибок: {failed}",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "broadcast:edit")
@admin_required
async def callback_broadcast_edit(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Редактирование сообщения рассылки."""
    await state.set_state(BroadcastFSM.message)
    await callback.message.edit_text(
        "✏️ <b>Редактирование</b>\n\n"
        "Введи новый текст сообщения:\n\n"
        "❌ Отправь /cancel для отмены",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "broadcast:cancel")
@admin_required
async def callback_broadcast_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Отмена рассылки."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Рассылка отменена",
        reply_markup=get_main_menu_keyboard()
    )


# ==================== Helper Functions ====================

async def get_bot_stats(db: DatabaseService) -> dict:
    """Получение полной статистики бота."""
    from sqlalchemy import func, select, and_
    from app.models import User, Habit, HabitLog
    
    async with db.session_factory() as session:
        # Пользователи
        total_users = await session.execute(select(func.count(User.id)))
        total_users = total_users.scalar()
        
        # Активные сегодня
        today = date.today()
        active_today = await session.execute(
            select(func.count(func.distinct(User.id)))
            .join(HabitLog)
            .where(HabitLog.completed_date == today)
        )
        active_today = active_today.scalar()
        
        # Новые за 7 дней
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_last_7_days = await session.execute(
            select(func.count(User.id))
            .where(User.created_at >= week_ago)
        )
        new_last_7_days = new_last_7_days.scalar()
        
        # Привычки
        total_habits = await session.execute(select(func.count(Habit.id)))
        total_habits = total_habits.scalar()
        
        active_habits = await session.execute(
            select(func.count(Habit.id))
            .where(and_(Habit.is_active == True, Habit.is_paused == False))
        )
        active_habits = active_habits.scalar()
        
        paused_habits = await session.execute(
            select(func.count(Habit.id))
            .where(Habit.is_paused == True)
        )
        paused_habits = paused_habits.scalar()
        
        # Выполнения
        completions_today = await session.execute(
            select(func.count(HabitLog.id))
            .where(and_(
                HabitLog.completed_date == today,
                HabitLog.status == "completed"
            ))
        )
        completions_today = completions_today.scalar()
        
        week_start = today - timedelta(days=7)
        completions_week = await session.execute(
            select(func.count(HabitLog.id))
            .where(and_(
                HabitLog.completed_date >= week_start,
                HabitLog.status == "completed"
            ))
        )
        completions_week = completions_week.scalar()
        
        total_completions = await session.execute(
            select(func.count(HabitLog.id))
            .where(HabitLog.status == "completed")
        )
        total_completions = total_completions.scalar()
        
        # Серии
        best_streak = await session.execute(
            select(func.max(Habit.best_streak))
        )
        best_streak = best_streak.scalar() or 0
        
        avg_streak = await session.execute(
            select(func.avg(Habit.current_streak))
        )
        avg_streak = avg_streak.scalar() or 0
        
        # AI
        ai_enabled_count = await session.execute(
            select(func.count(User.id))
            .where(User.ai_enabled == True)
        )
        ai_enabled_count = ai_enabled_count.scalar()
        
        return {
            "total_users": total_users,
            "active_today": active_today,
            "new_last_7_days": new_last_7_days,
            "total_habits": total_habits,
            "active_habits": active_habits,
            "paused_habits": paused_habits,
            "completions_today": completions_today,
            "completions_week": completions_week,
            "total_completions": total_completions,
            "best_streak": best_streak,
            "avg_streak": avg_streak,
            "ai_enabled_count": ai_enabled_count,
        }


# ==================== Reply Keyboard Handlers ====================

@router.message(F.text == "➕ Добавить привычку")
async def reply_add_habit(message: types.Message, state: FSMContext) -> None:
    """Обработка кнопки Добавить привычку."""
    # Вызываем существующий хендлер
    from app.handlers.habits import cmd_add_habit
    await cmd_add_habit(message, state)


@router.message(F.text == "📋 Мои привычки")
async def reply_my_habits(message: types.Message, db: DatabaseService) -> None:
    """Обработка кнопки Мои привычки."""
    from app.handlers.habits import cmd_my_habits
    await cmd_my_habits(message, db)


@router.message(F.text == "📊 Прогресс")
async def reply_progress(message: types.Message, db: DatabaseService) -> None:
    """Обработка кнопки Прогресс."""
    from app.handlers.habits import cmd_my_progress
    await cmd_my_progress(message, db)


@router.message(F.text == "🤖 AI")
async def reply_ai(message: types.Message, db: DatabaseService, ai) -> None:
    """Обработка кнопки AI."""
    from app.handlers.ai_handlers import cmd_ai_advice
    await cmd_ai_advice(message, db, ai)


@router.message(F.text == "⚙️ Настройки")
async def reply_settings(message: types.Message, db: DatabaseService) -> None:
    """Обработка кнопки Настройки."""
    from app.handlers.common import cmd_settings
    await cmd_settings(message, db)


@router.message(F.text == "❓ Помощь")
async def reply_help(message: types.Message) -> None:
    """Обработка кнопки Помощь."""
    from app.handlers.common import cmd_help
    await cmd_help(message)


@router.message(F.text == "« В главное меню")
async def reply_back_to_main(message: types.Message) -> None:
    """Возврат в главное меню."""
    await message.answer(
        "👋 <b>Главное меню</b>\n\nВыбери действие:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
