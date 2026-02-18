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
from app.middlewares.fsm_timeout import FSMStateHistory
from app.keyboards.fsm_keyboards import (
    get_fsm_cancel_only_keyboard,
    get_fsm_navigation_keyboard,
    get_emoji_selection_keyboard,
    get_frequency_selection_keyboard,
    get_time_selection_keyboard,
    get_confirmation_keyboard,
    get_invalid_input_keyboard
)

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
    # Очищаем предыдущие данные FSM
    await state.clear()
    
    # Устанавливаем состояние
    await state.set_state(AddHabitFSM.name)
    
    # Сохраняем начальное состояние в историю
    await FSMStateHistory.push_state(state, "name")
    
    keyboard = get_fsm_cancel_only_keyboard(cancel_callback="fsm:cancel")
    
    await message.answer(
        "📝 <b>Добавление новой привычки</b>\n\n"
        "Шаг 1/5: Введи название привычки\n"
        "<i>Например: 'Утренняя зарядка' или 'Читать 30 минут'</i>\n\n"
        "❌ Нажми 'Отмена' для выхода",
        reply_markup=keyboard,
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
    """Обработка названия привычки с улучшенной валидацией."""
    # Проверяем, не является ли сообщение командой
    if message.text and message.text.startswith('/'):
        await message.answer(
            "❌ Пожалуйста, сначала завершите добавление привычки или нажмите 'Отмена'",
            reply_markup=get_fsm_cancel_only_keyboard(cancel_callback="fsm:cancel")
        )
        return
    
    name = message.text.strip() if message.text else ""
    
    # Валидация
    errors = []
    if len(name) < 2:
        errors.append("• Название слишком короткое (минимум 2 символа)")
    if len(name) > 100:
        errors.append("• Название слишком длинное (максимум 100 символов)")
    if name.startswith('/') or name.startswith('!'):
        errors.append("• Название не должно начинаться со спецсимволов")
    
    if errors:
        error_text = "❌ <b>Ошибка в названии:</b>\n\n" + "\n".join(errors)
        error_text += "\n\nПожалуйста, введи другое название:"
        
        keyboard = get_invalid_input_keyboard(
            hint="2-100 символов",
            back_callback="fsm:cancel",
            cancel_callback="fsm:cancel"
        )
        await message.answer(error_text, reply_markup=keyboard, parse_mode="HTML")
        return
    
    # Сохраняем данные и переходим к следующему шагу
    await state.update_data(name=name)
    await state.set_state(AddHabitFSM.description)
    
    # Сохраняем состояние в историю
    await FSMStateHistory.push_state(state, "description", {"name": name})
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить »", callback_data="skip_description")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="fsm:cancel")]
    ])
    
    await message.answer(
        f"✅ Название: <b>{name}</b>\n\n"
        f"Шаг 2/5: Добавь описание (необязательно)\n"
        f"<i>Например: 'Делаю 15 приседаний и 10 отжиманий'</i>\n\n"
        f"Или нажми 'Пропустить' чтобы перейти дальше",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "skip_description", AddHabitFSM.description)
async def callback_skip_description(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Пропуск описания."""
    await callback.answer()
    
    # Получаем текущие данные
    data = await state.get_data()
    
    await state.update_data(description=None)
    await state.set_state(AddHabitFSM.emoji)
    
    # Сохраняем состояние в историю
    await FSMStateHistory.push_state(state, "emoji", {**data, "description": None})
    
    keyboard = get_emoji_selection_keyboard(
        back_callback="fsm:back",
        cancel_callback="fsm:cancel"
    )
    
    await callback.message.edit_text(
        "Шаг 3/5: Выбери эмодзи для привычки:\n\n"
        "<i>Или используй кнопки навигации</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(AddHabitFSM.description)
async def process_habit_description(message: types.Message, state: FSMContext) -> None:
    """Обработка описания привычки с улучшенной валидацией."""
    # Проверяем, не является ли сообщение командой
    if message.text and message.text.startswith('/'):
        await message.answer(
            "❌ Пожалуйста, используй кнопки или введи описание",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Пропустить »", callback_data="skip_description")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="fsm:cancel")]
            ])
        )
        return
    
    description = message.text.strip() if message.text else ""
    
    # Валидация описания
    if len(description) > 500:
        keyboard = get_invalid_input_keyboard(
            hint="Максимум 500 символов",
            back_callback="fsm:back",
            cancel_callback="fsm:cancel"
        )
        await message.answer(
            "❌ <b>Описание слишком длинное</b>\n\n"
            f"У тебя {len(description)} символов, максимум 500.\n"
            "Пожалуйста, сократи описание:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    # Получаем текущие данные
    data = await state.get_data()
    
    await state.update_data(description=description)
    await state.set_state(AddHabitFSM.emoji)
    
    # Сохраняем состояние в историю
    await FSMStateHistory.push_state(state, "emoji", {**data, "description": description})
    
    keyboard = get_emoji_selection_keyboard(
        back_callback="fsm:back",
        cancel_callback="fsm:cancel"
    )
    
    await message.answer(
        "✅ Описание сохранено!\n\n"
        "Шаг 3/5: Выбери эмодзи для привычки:\n\n"
        "<i>Используй кнопки навигации если нужно</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("emoji:"), AddHabitFSM.emoji)
async def process_habit_emoji(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора эмодзи."""
    await callback.answer()
    
    emoji = callback.data.split(":")[1]
    
    # Получаем текущие данные
    data = await state.get_data()
    
    await state.update_data(emoji=emoji)
    await state.set_state(AddHabitFSM.frequency)
    
    # Сохраняем состояние в историю
    await FSMStateHistory.push_state(state, "frequency", {**data, "emoji": emoji})
    
    keyboard = get_frequency_selection_keyboard(
        back_callback="fsm:back",
        cancel_callback="fsm:cancel"
    )
    
    await callback.message.edit_text(
        f"{emoji} Отлично!\n\n"
        f"Шаг 4/5: Выбери частоту выполнения:\n\n"
        f"<i>Можно вернуться назад если передумал</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("freq:"), AddHabitFSM.frequency)
async def process_habit_frequency(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора частоты."""
    await callback.answer()
    
    frequency = callback.data.split(":")[1]
    
    # Получаем текущие данные
    data = await state.get_data()
    
    await state.update_data(frequency=frequency)
    await state.set_state(AddHabitFSM.reminder_time)
    
    # Сохраняем состояние в историю
    await FSMStateHistory.push_state(state, "reminder_time", {**data, "frequency": frequency})
    
    keyboard = get_time_selection_keyboard(
        back_callback="fsm:back",
        cancel_callback="fsm:cancel"
    )
    
    await callback.message.edit_text(
        "Шаг 5/5: Когда напоминать о привычке?\n\n"
        "<i>• Выбери готовое время или</i>\n"
        "<i>• Введи вручную в формате ЧЧ:ММ (например: 08:30)</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ==================== FSM Navigation Handlers ====================

@router.callback_query(F.data == "fsm:cancel")
async def callback_fsm_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Отмена FSM диалога."""
    current_state = await state.get_state()
    
    if current_state:
        # Очищаем FSM
        await state.clear()
        await callback.message.edit_text(
            "❌ Добавление привычки отменено.\n\n"
            "Все данные сброшены. Начни заново если хочешь создать привычку!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить привычку", callback_data="add_habit")],
                [InlineKeyboardButton(text="« В меню", callback_data="back_to_menu")]
            ])
        )
    else:
        await callback.answer("Нечего отменять", show_alert=True)


@router.callback_query(F.data == "fsm:back")
async def callback_fsm_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Возврат к предыдущему шагу FSM."""
    from app.middlewares.fsm_timeout import FSMStateHistory
    
    # Получаем предыдущее состояние из истории
    previous = await FSMStateHistory.pop_state(state)
    
    if not previous:
        await callback.answer("Нельзя вернуться назад - это первый шаг", show_alert=True)
        return
    
    await callback.answer()
    
    prev_state = previous["state"]
    prev_data = previous.get("data", {})
    
    # Восстанавливаем данные
    await state.update_data(**prev_data)
    
    # Переходим в предыдущее состояние
    if prev_state == "name":
        await state.set_state(AddHabitFSM.name)
        keyboard = get_fsm_cancel_only_keyboard(cancel_callback="fsm:cancel")
        await callback.message.edit_text(
            "📝 <b>Добавление новой привычки</b>\n\n"
            "Шаг 1/5: Введи название привычки\n"
            "<i>Например: 'Утренняя зарядка' или 'Читать 30 минут'</i>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    elif prev_state == "description":
        await state.set_state(AddHabitFSM.description)
        name = prev_data.get("name", "")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить »", callback_data="skip_description")],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="fsm:back"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="fsm:cancel")
            ]
        ])
        await callback.message.edit_text(
            f"✅ Название: <b>{name}</b>\n\n"
            f"Шаг 2/5: Добавь описание (необязательно)\n"
            f"<i>Например: 'Делаю 15 приседаний и 10 отжиманий'</i>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    elif prev_state == "emoji":
        await state.set_state(AddHabitFSM.emoji)
        selected_emoji = prev_data.get("emoji")
        keyboard = get_emoji_selection_keyboard(
            selected_emoji=selected_emoji,
            back_callback="fsm:back",
            cancel_callback="fsm:cancel"
        )
        await callback.message.edit_text(
            "Шаг 3/5: Выбери эмодзи для привычки:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    elif prev_state == "frequency":
        await state.set_state(AddHabitFSM.frequency)
        emoji = prev_data.get("emoji", "✅")
        selected_freq = prev_data.get("frequency")
        keyboard = get_frequency_selection_keyboard(
            selected_frequency=selected_freq,
            back_callback="fsm:back",
            cancel_callback="fsm:cancel"
        )
        await callback.message.edit_text(
            f"{emoji} Отлично!\n\n"
            f"Шаг 4/5: Выбери частоту выполнения:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    elif prev_state == "reminder_time":
        await state.set_state(AddHabitFSM.reminder_time)
        keyboard = get_time_selection_keyboard(
            back_callback="fsm:back",
            cancel_callback="fsm:cancel"
        )
        await callback.message.edit_text(
            "Шаг 5/5: Когда напоминать о привычке?\n\n"
            "<i>• Выбери готовое время или</i>\n"
            "<i>• Введи вручную в формате ЧЧ:ММ (например: 08:30)</i>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.callback_query(F.data == "fsm:retry")
async def callback_fsm_retry(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Повторить текущий шаг после ошибки ввода."""
    current_state = await state.get_state()
    
    if not current_state:
        await callback.answer("Сессия завершена", show_alert=True)
        return
    
    await callback.answer("Попробуй снова")
    
    # Просто удаляем сообщение об ошибке и просим ввести снова
    # Текущее состояние не меняется
    state_name = current_state.split(":")[-1]
    
    hints = {
        "name": "Введи название привычки (2-100 символов):",
        "description": "Введи описание (или нажми Пропустить):",
        "reminder_time": "Введи время в формате ЧЧ:ММ (например: 08:30):"
    }
    
    hint = hints.get(state_name, "Попробуй снова:")
    
    keyboard = get_fsm_navigation_keyboard(
        show_back=state_name != "name",
        back_callback="fsm:back",
        cancel_callback="fsm:cancel"
    )
    
    await callback.message.edit_text(
        f"🔄 <b>Попробуем еще раз</b>\n\n{hint}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("time:"), AddHabitFSM.reminder_time)
async def process_reminder_time_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    db: DatabaseService
) -> None:
    """Обработка выбора времени через callback."""
    await callback.answer()
    
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
    """Обработка ввода времени вручную с улучшенной валидацией."""
    # Проверяем, не является ли сообщение командой
    if message.text and message.text.startswith('/'):
        await message.answer(
            "❌ Пожалуйста, используй кнопки или введи время вручную",
            reply_markup=get_time_selection_keyboard(
                back_callback="fsm:back",
                cancel_callback="fsm:cancel"
            )
        )
        return
    
    time_str = message.text.strip() if message.text else ""
    
    # Подробная валидация времени
    errors = []
    
    if not time_str:
        errors.append("Время не указано")
    else:
        # Проверяем формат
        if ":" not in time_str:
            errors.append("Используй разделитель ':' (например: 08:30)")
        else:
            parts = time_str.split(":")
            if len(parts) != 2:
                errors.append("Неверный формат. Используй: ЧЧ:ММ")
            else:
                try:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    
                    if not (0 <= hours <= 23):
                        errors.append(f"Часы должны быть от 0 до 23 (у тебя: {hours})")
                    if not (0 <= minutes <= 59):
                        errors.append(f"Минуты должны быть от 0 до 59 (у тебя: {minutes})")
                        
                except ValueError:
                    errors.append("Часы и минуты должны быть числами")
    
    if errors:
        error_text = "❌ <b>Ошибка в времени:</b>\n\n" + "\n".join(f"• {e}" for e in errors)
        error_text += "\n\nПожалуйста, введи время снова:"
        
        keyboard = get_invalid_input_keyboard(
            hint="Формат: ЧЧ:ММ (например: 08:30)",
            back_callback="fsm:back",
            cancel_callback="fsm:cancel"
        )
        await message.answer(error_text, reply_markup=keyboard, parse_mode="HTML")
        return
    
    # Парсим время
    hours, minutes = map(int, time_str.split(":"))
    
    # Сохраняем и создаем привычку
    await state.update_data(reminder_time=f"{hours:02d}:{minutes:02d}")
    await save_habit_message(message, state, db)


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
