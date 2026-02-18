"""
Хендлеры для управления привычками.
CRUD операции с использованием FSM.
"""

import logging
from datetime import datetime, time

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)
router = Router()


# ==================== FSM States ====================

class AddHabitFSM(StatesGroup):
    """Состояния для добавления привычки."""
    name = State()
    description = State()
    emoji = State()
    frequency = State()
    reminder_time = State()
    confirm = State()


class EditHabitFSM(StatesGroup):
    """Состояния для редактирования привычки."""
    select_field = State()
    new_value = State()


# ==================== Команды ====================

@router.message(Command("add_habit"))
async def cmd_add_habit(message: types.Message, state: FSMContext) -> None:
    """Начало добавления привычки."""
    await state.set_state(AddHabitFSM.name)
    await message.answer(
        "📝 <b>Добавление новой привычки</b>\n\n"
        "Шаг 1/5: Введи название привычки\n"
        "<i>Например: 'Утренняя зарядка' или 'Читать 30 минут'</i>",
        parse_mode="HTML"
    )


@router.message(Command("my_habits"))
async def cmd_my_habits(message: types.Message, db: DatabaseService) -> None:
    """Показать список привычек."""
    habits = await db.get_user_habits(message.from_user.id, active_only=True)
    
    if not habits:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить первую привычку",
                    callback_data="add_habit"
                )
            ]
        ])
        await message.answer(
            "📝 У тебя пока нет активных привычек.\n\n"
            "Добавь первую, и начни путь к лучшей версии себя! 💪",
            reply_markup=keyboard
        )
        return
    
    text = "📋 <b>Твои привычки:</b>\n\n"
    
    for i, habit in enumerate(habits, 1):
        status = "✅" if habit.is_completed_today else "⏳"
        streak = f"🔥 {habit.current_streak}" if habit.current_streak > 0 else "🆕"
        reminder = f"⏰ {habit.reminder_time.strftime('%H:%M')}" if habit.reminder_time else ""
        
        text += (
            f"{i}. {habit.emoji} <b>{habit.name}</b> {status}\n"
            f"   {streak} серия | {habit.progress_percentage:.0f}% цели {reminder}\n\n"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Добавить",
                callback_data="add_habit"
            ),
            InlineKeyboardButton(
                text="📊 Прогресс",
                callback_data="show_progress"
            )
        ],
        [
            InlineKeyboardButton(
                text="« Назад",
                callback_data="back_to_menu"
            )
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("my_progress"))
async def cmd_my_progress(message: types.Message, db: DatabaseService) -> None:
    """Показать статистику прогресса."""
    stats = await db.get_user_stats(message.from_user.id)
    user = await db.get_user(message.from_user.id)
    
    text = (
        f"📊 <b>Твой прогресс</b>\n\n"
        f"📌 Всего привычек: <b>{stats['total_habits']}</b>\n"
        f"✅ Активных: <b>{stats['active_habits']}</b>\n"
        f"🎯 Всего выполнено: <b>{stats['total_completions']}</b>\n"
        f"🔥 Лучшая серия: <b>{stats['best_streak']}</b> дней\n\n"
    )
    
    # Добавляем мотивацию
    if stats['total_completions'] == 0:
        text += "💪 Время начать! Добавь свою первую привычку."
    elif stats['best_streak'] < 7:
        text += "🌱 Отличное начало! Продолжай в том же духе."
    elif stats['best_streak'] < 21:
        text += "🚀 Хороший прогресс! Привычка уже формируется."
    else:
        text += "⭐ Впечатляюще! Ты настоящий мастер привычек!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📋 Мои привычки",
                callback_data="list_habits"
            ),
            InlineKeyboardButton(
                text="🤖 AI-анализ",
                callback_data="ai_advice"
            )
        ],
        [
            InlineKeyboardButton(
                text="« Назад",
                callback_data="back_to_menu"
            )
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== FSM Handlers - Add Habit ====================

@router.callback_query(F.data == "add_habit")
async def callback_add_habit(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Начало добавления привычки через callback."""
    await callback.answer()
    await state.set_state(AddHabitFSM.name)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_add_habit"
            )
        ]
    ])
    
    await callback.message.edit_text(
        "📝 <b>Добавление новой привычки</b>\n\n"
        "Шаг 1/5: Введи название привычки\n"
        "<i>Например: 'Утренняя зарядка' или 'Читать 30 минут'</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cancel_add_habit")
async def callback_cancel_add_habit(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Отмена добавления привычки."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Добавление привычки отменено.\n\n"
        "Выбери другое действие:"
    )
    await callback.answer("Отменено")


@router.message(AddHabitFSM.name)
async def process_habit_name(message: types.Message, state: FSMContext) -> None:
    """Обработка названия привычки."""
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 100:
        await message.answer(
            "❌ Название должно быть от 2 до 100 символов.\n"
            "Попробуй ещё раз:"
        )
        return
    
    await state.update_data(name=name)
    await state.set_state(AddHabitFSM.description)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Пропустить »",
                callback_data="skip_description"
            )
        ]
    ])
    
    await message.answer(
        f"✅ Название: <b>{name}</b>\n\n"
        f"Шаг 2/5: Добавь описание (необязательно)\n"
        f"<i>Например: 'Делаю 15 приседаний и 10 отжиманий'</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "skip_description", AddHabitFSM.description)
async def callback_skip_description(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Пропуск описания."""
    await state.update_data(description=None)
    await state.set_state(AddHabitFSM.emoji)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅", callback_data="emoji:✅"),
            InlineKeyboardButton(text="💪", callback_data="emoji:💪"),
            InlineKeyboardButton(text="🏃", callback_data="emoji:🏃"),
            InlineKeyboardButton(text="📚", callback_data="emoji:📚"),
        ],
        [
            InlineKeyboardButton(text="💧", callback_data="emoji:💧"),
            InlineKeyboardButton(text="🧘", callback_data="emoji:🧘"),
            InlineKeyboardButton(text="🥗", callback_data="emoji:🥗"),
            InlineKeyboardButton(text="💊", callback_data="emoji:💊"),
        ],
        [
            InlineKeyboardButton(text="🎯", callback_data="emoji:🎯"),
            InlineKeyboardButton(text="⭐", callback_data="emoji:⭐"),
            InlineKeyboardButton(text="🔥", callback_data="emoji:🔥"),
            InlineKeyboardButton(text="❤️", callback_data="emoji:❤️"),
        ]
    ])
    
    await callback.message.edit_text(
        "Шаг 3/5: Выбери эмодзи для привычки:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(AddHabitFSM.description)
async def process_habit_description(message: types.Message, state: FSMContext) -> None:
    """Обработка описания привычки."""
    description = message.text.strip()
    
    if len(description) > 500:
        await message.answer("❌ Описание слишком длинное (макс. 500 символов). Попробуй ещё раз:")
        return
    
    await state.update_data(description=description)
    await state.set_state(AddHabitFSM.emoji)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅", callback_data="emoji:✅"),
            InlineKeyboardButton(text="💪", callback_data="emoji:💪"),
            InlineKeyboardButton(text="🏃", callback_data="emoji:🏃"),
            InlineKeyboardButton(text="📚", callback_data="emoji:📚"),
        ],
        [
            InlineKeyboardButton(text="💧", callback_data="emoji:💧"),
            InlineKeyboardButton(text="🧘", callback_data="emoji:🧘"),
            InlineKeyboardButton(text="🥗", callback_data="emoji:🥗"),
            InlineKeyboardButton(text="💊", callback_data="emoji:💊"),
        ],
        [
            InlineKeyboardButton(text="🎯", callback_data="emoji:🎯"),
            InlineKeyboardButton(text="⭐", callback_data="emoji:⭐"),
            InlineKeyboardButton(text="🔥", callback_data="emoji:🔥"),
            InlineKeyboardButton(text="❤️", callback_data="emoji:❤️"),
        ]
    ])
    
    await message.answer(
        "✅ Описание сохранено!\n\n"
        "Шаг 3/5: Выбери эмодзи для привычки:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("emoji:"), AddHabitFSM.emoji)
async def process_habit_emoji(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора эмодзи."""
    emoji = callback.data.split(":")[1]
    await state.update_data(emoji=emoji)
    await state.set_state(AddHabitFSM.frequency)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📅 Каждый день",
                callback_data="freq:daily"
            )
        ],
        [
            InlineKeyboardButton(
                text="📆 По будням",
                callback_data="freq:weekdays"
            ),
            InlineKeyboardButton(
                text="🎉 По выходным",
                callback_data="freq:weekends"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗓 Раз в неделю",
                callback_data="freq:weekly"
            )
        ]
    ])
    
    await callback.message.edit_text(
        f"{emoji} Отлично!\n\n"
        f"Шаг 4/5: Выбери частоту выполнения:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("freq:"), AddHabitFSM.frequency)
async def process_habit_frequency(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора частоты."""
    frequency = callback.data.split(":")[1]
    await state.update_data(frequency=frequency)
    await state.set_state(AddHabitFSM.reminder_time)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🌅 Утро (07:00)",
                callback_data="time:07:00"
            ),
            InlineKeyboardButton(
                text="🌇 Вечер (20:00)",
                callback_data="time:20:00"
            )
        ],
        [
            InlineKeyboardButton(
                text="Без напоминания",
                callback_data="time:none"
            )
        ]
    ])
    
    await callback.message.edit_text(
        "Шаг 5/5: Когда напоминать о привычке?\n"
        "<i>Или введи время в формате ЧЧ:ММ (например: 08:30)</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("time:"), AddHabitFSM.reminder_time)
async def process_reminder_time_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    db: DatabaseService
) -> None:
    """Обработка выбора времени через callback."""
    time_str = callback.data.split(":", 1)[1]
    
    if time_str == "none":
        await state.update_data(reminder_time=None)
    else:
        hours, minutes = map(int, time_str.split(":"))
        await state.update_data(reminder_time=f"{hours:02d}:{minutes:02d}")
    
    await save_habit(callback, state, db)


@router.message(AddHabitFSM.reminder_time)
async def process_reminder_time_message(
    message: types.Message,
    state: FSMContext,
    db: DatabaseService
) -> None:
    """Обработка ввода времени вручную."""
    time_str = message.text.strip()
    
    try:
        hours, minutes = map(int, time_str.split(":"))
        if not (0 <= hours < 24 and 0 <= minutes < 60):
            raise ValueError
        
        await state.update_data(reminder_time=f"{hours:02d}:{minutes:02d}")
        await save_habit_message(message, state, db)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат времени.\n"
            "Введи время в формате ЧЧ:ММ (например: 08:30):"
        )


async def save_habit(
    callback: types.CallbackQuery,
    state: FSMContext,
    db: DatabaseService
) -> None:
    """Сохранение привычки (из callback)."""
    data = await state.get_data()
    
    # Преобразуем время
    reminder_time = None
    if data.get("reminder_time"):
        hours, minutes = map(int, data["reminder_time"].split(":"))
        reminder_time = time(hours, minutes)
    
    # Создаём привычку
    habit = await db.create_habit(
        user_id=callback.from_user.id,
        name=data["name"],
        description=data.get("description"),
        emoji=data.get("emoji", "✅"),
        reminder_time=datetime.combine(datetime.today(), reminder_time) if reminder_time else None,
        frequency=data.get("frequency", "daily")
    )
    
    await state.clear()
    
    # Формируем сообщение
    reminder_text = f"⏰ Напоминание: {data.get('reminder_time', 'нет')}" if data.get("reminder_time") else "🔕 Без напоминания"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📋 Мои привычки",
                callback_data="list_habits"
            ),
            InlineKeyboardButton(
                text="➕ Ещё одна",
                callback_data="add_habit"
            )
        ],
        [
            InlineKeyboardButton(
                text="« В меню",
                callback_data="back_to_menu"
            )
        ]
    ])
    
    await callback.message.edit_text(
        f"🎉 <b>Привычка создана!</b>\n\n"
        f"{habit.emoji} <b>{habit.name}</b>\n"
        f"{reminder_text}\n\n"
        f"Ты молодец! Теперь отслеживай выполнение каждый день. 💪",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer("Привычка создана!")


async def save_habit_message(
    message: types.Message,
    state: FSMContext,
    db: DatabaseService
) -> None:
    """Сохранение привычки (из message)."""
    data = await state.get_data()
    
    # Преобразуем время
    reminder_time = None
    if data.get("reminder_time"):
        hours, minutes = map(int, data["reminder_time"].split(":"))
        reminder_time = time(hours, minutes)
    
    # Создаём привычку
    habit = await db.create_habit(
        user_id=message.from_user.id,
        name=data["name"],
        description=data.get("description"),
        emoji=data.get("emoji", "✅"),
        reminder_time=datetime.combine(datetime.today(), reminder_time) if reminder_time else None,
        frequency=data.get("frequency", "daily")
    )
    
    await state.clear()
    
    # Формируем сообщение
    reminder_text = f"⏰ Напоминание: {data.get('reminder_time', 'нет')}" if data.get("reminder_time") else "🔕 Без напоминания"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📋 Мои привычки",
                callback_data="list_habits"
            ),
            InlineKeyboardButton(
                text="➕ Ещё одна",
                callback_data="add_habit"
            )
        ],
        [
            InlineKeyboardButton(
                text="« В меню",
                callback_data="back_to_menu"
            )
        ]
    ])
    
    await message.answer(
        f"🎉 <b>Привычка создана!</b>\n\n"
        f"{habit.emoji} <b>{habit.name}</b>\n"
        f"{reminder_text}\n\n"
        f"Ты молодец! Теперь отслеживай выполнение каждый день. 💪",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ==================== Callback Handlers ====================

@router.callback_query(F.data == "list_habits")
async def callback_list_habits(callback: types.CallbackQuery, db: DatabaseService) -> None:
    """Показать список привычек через callback."""
    await callback.answer()
    habits = await db.get_user_habits(callback.from_user.id, active_only=True)
    
    if not habits:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить первую привычку",
                    callback_data="add_habit"
                )
            ]
        ])
        await callback.message.edit_text(
            "📝 У тебя пока нет активных привычек.\n\n"
            "Добавь первую, и начни путь к лучшей версии себя! 💪",
            reply_markup=keyboard
        )
        return
    
    text = "📋 <b>Твои привычки:</b>\n\n"
    
    for i, habit in enumerate(habits, 1):
        status = "✅" if habit.is_completed_today else "⏳"
        streak = f"🔥 {habit.current_streak}" if habit.current_streak > 0 else "🆕"
        reminder = f"⏰ {habit.reminder_time.strftime('%H:%M')}" if habit.reminder_time else ""
        
        text += (
            f"{i}. {habit.emoji} <b>{habit.name}</b> {status}\n"
            f"   {streak} серия | {habit.progress_percentage:.0f}% цели {reminder}\n\n"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Добавить",
                callback_data="add_habit"
            ),
            InlineKeyboardButton(
                text="📊 Прогресс",
                callback_data="show_progress"
            )
        ],
        [
            InlineKeyboardButton(
                text="« Назад",
                callback_data="back_to_menu"
            )
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "show_progress")
async def callback_show_progress(callback: types.CallbackQuery, db: DatabaseService) -> None:
    """Показать прогресс через callback."""
    await callback.answer()
    stats = await db.get_user_stats(callback.from_user.id)
    user = await db.get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("Ошибка! Сначала запустите /start", show_alert=True)
        return
    
    text = (
        f"📊 <b>Твой прогресс</b>\n\n"
        f"📌 Всего привычек: <b>{stats['total_habits']}</b>\n"
        f"✅ Активных: <b>{stats['active_habits']}</b>\n"
        f"🎯 Всего выполнено: <b>{stats['total_completions']}</b>\n"
        f"🔥 Лучшая серия: <b>{stats['best_streak']}</b> дней\n\n"
    )
    
    # Добавляем мотивацию
    if stats['total_completions'] == 0:
        text += "💪 Время начать! Добавь свою первую привычку."
    elif stats['best_streak'] < 7:
        text += "🌱 Отличное начало! Продолжай в том же духе."
    elif stats['best_streak'] < 21:
        text += "🚀 Хороший прогресс! Привычка уже формируется."
    else:
        text += "⭐ Впечатляюще! Ты настоящий мастер привычек!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📋 Мои привычки",
                callback_data="list_habits"
            ),
            InlineKeyboardButton(
                text="🤖 AI-анализ",
                callback_data="ai_advice"
            )
        ],
        [
            InlineKeyboardButton(
                text="« Назад",
                callback_data="back_to_menu"
            )
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== Обработка действий с привычками ====================

@router.callback_query(F.data.startswith("complete:"))
async def callback_complete_habit(
    callback: types.CallbackQuery,
    db: DatabaseService
) -> None:
    """Отметить привычку выполненной."""
    habit_id = int(callback.data.split(":")[1])
    
    # Создаём лог
    log = await db.log_habit_completion(
        habit_id=habit_id,
        user_id=callback.from_user.id,
        status="completed"
    )
    
    # Получаем обновлённую привычку
    habit = await db.get_habit(habit_id, callback.from_user.id)
    
    if habit:
        await callback.answer(f"✅ Отлично! Серия: {habit.current_streak} дней! 🔥")
        
        # Обновляем сообщение
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Уже выполнено",
                    callback_data="done"
                )
            ]
        ])
        
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except Exception:
            pass
    else:
        await callback.answer("Ошибка! Привычка не найдена.")


@router.callback_query(F.data.startswith("skip:"))
async def callback_skip_habit(
    callback: types.CallbackQuery,
    db: DatabaseService
) -> None:
    """Пропустить привычку."""
    habit_id = int(callback.data.split(":")[1])
    
    await db.log_habit_completion(
        habit_id=habit_id,
        user_id=callback.from_user.id,
        status="skipped"
    )
    
    await callback.answer("📊 Записано. Не сдавайся!")


@router.callback_query(F.data.startswith("snooze:"))
async def callback_snooze_habit(
    callback: types.CallbackQuery,
    db: DatabaseService
) -> None:
    """Отложить напоминание."""
    habit_id = int(callback.data.split(":")[1])
    
    habit = await db.get_habit(habit_id, callback.from_user.id)
    
    if habit:
        await callback.answer("⏰ Напомним через час!")
        # Здесь можно добавить логику отложенного напоминания
    else:
        await callback.answer("Ошибка!")


@router.callback_query(F.data == "done")
async def callback_already_done(callback: types.CallbackQuery) -> None:
    """Привычка уже выполнена."""
    await callback.answer("Уже отмечено! 💪")
