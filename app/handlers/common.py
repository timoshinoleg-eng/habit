"""
Общие команды и хендлеры.
/start, /help, /settings, и т.д.
"""

import logging

from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, db: DatabaseService) -> None:
    """Обработчик команды /start."""
    user = message.from_user
    
    # Регистрация пользователя
    await db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Приветственное сообщение
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я <b>HabitMax</b> - твой персональный помощник по формированию "
        f"полезных привычек! 🎯\n\n"
        f"Со мной ты сможешь:\n"
        f"✅ Отслеживать свои привычки\n"
        f"📊 Анализировать прогресс\n"
        f"🤖 Получать AI-рекомендации\n"
        f"🔔 Настраивать умные напоминания\n\n"
        f"Давай начнём! Выбери действие ниже 👇"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Добавить привычку",
                callback_data="add_habit"
            ),
            InlineKeyboardButton(
                text="📋 Мои привычки",
                callback_data="list_habits"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Прогресс",
                callback_data="show_progress"
            ),
            InlineKeyboardButton(
                text="🤖 AI-совет",
                callback_data="ai_advice"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Настройки",
                callback_data="settings"
            ),
            InlineKeyboardButton(
                text="❓ Помощь",
                callback_data="help"
            )
        ]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Обработчик команды /help."""
    help_text = (
        "📚 <b>Команды HabitMax:</b>\n\n"
        
        "<b>Основные:</b>\n"
        "/start - Начать работу с ботом\n"
        "/add_habit - Добавить новую привычку\n"
        "/my_habits - Список моих привычек\n"
        "/my_progress - Посмотреть прогресс\n\n"
        
        "<b>AI-функции:</b>\n"
        "/ai_advice - Получить AI-рекомендацию\n"
        "/analyze_patterns - Анализировать мои паттерны\n\n"
        
        "<b>Настройки:</b>\n"
        "/settings - Настройки бота\n"
        "/toggle_ai - Вкл/Выкл AI-напоминания\n\n"
        
        "<b>Управление привычками:</b>\n"
        "• Нажимай ✅ в напоминаниях, чтобы отметить выполнение\n"
        "• Используй кнопки под привычками для редактирования\n"
        "• Каждый день без пропуска = +1 к серии 🔥\n\n"
        
        "Нужна помощь? Пиши @support_habitmax"
    )
    
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("settings"))
async def cmd_settings(message: types.Message, db: DatabaseService) -> None:
    """Обработчик команды /settings."""
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("Сначала запустите бота командой /start")
        return
    
    ai_status = "✅ Включены" if user.ai_enabled else "❌ Выключены"
    notifications_status = "✅ Включены" if user.notification_enabled else "❌ Выключены"
    
    settings_text = (
        f"⚙️ <b>Настройки</b>\n\n"
        f"👤 Имя: {user.full_name}\n"
        f"🌐 Часовой пояс: {user.timezone}\n\n"
        f"🤖 AI-напоминания: {ai_status}\n"
        f"🔔 Уведомления: {notifications_status}\n"
        f"📊 Всего выполнено: {user.total_completions}\n"
        f"🔥 Текущая серия: {user.streak_days} дней\n\n"
        f"Выбери, что хочешь изменить:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🤖 AI: " + ("Выключить" if user.ai_enabled else "Включить"),
                callback_data="toggle_ai"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔔 Уведомления: " + ("Выключить" if user.notification_enabled else "Включить"),
                callback_data="toggle_notifications"
            )
        ],
        [
            InlineKeyboardButton(
                text="🌍 Изменить часовой пояс",
                callback_data="change_timezone"
            )
        ],
        [
            InlineKeyboardButton(
                text="« Назад в меню",
                callback_data="back_to_menu"
            )
        ]
    ])
    
    await message.answer(settings_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: types.CallbackQuery) -> None:
    """Возврат в главное меню."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Добавить привычку",
                callback_data="add_habit"
            ),
            InlineKeyboardButton(
                text="📋 Мои привычки",
                callback_data="list_habits"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Прогресс",
                callback_data="show_progress"
            ),
            InlineKeyboardButton(
                text="🤖 AI-совет",
                callback_data="ai_advice"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Настройки",
                callback_data="settings"
            )
        ]
    ])
    
    await callback.message.edit_text(
        "👋 <b>Главное меню</b>\n\n"
        "Выбери действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def callback_help(callback: types.CallbackQuery) -> None:
    """Показать помощь через callback."""
    await callback.answer()
    
    help_text = (
        "📚 <b>Как пользоваться HabitMax:</b>\n\n"
        
        "1️⃣ <b>Добавь привычку</b> - нажми 'Добавить привычку'\n"
        "2️⃣ <b>Настрой время</b> - выбери, когда напоминать\n"
        "3️⃣ <b>Выполняй</b> - отмечай привычки ежедневно\n"
        "4️⃣ <b>Следи за прогрессом</b> - смотри статистику\n"
        "5️⃣ <b>AI-помощь</b> - получай персональные советы\n\n"
        
        "💡 <b>Совет:</b> Начни с 1-2 простых привычек, "
        "а не с десятка сложных!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="« Назад",
                callback_data="back_to_menu"
            )
        ]
    ])
    
    await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "settings")
async def callback_settings(callback: types.CallbackQuery, db: DatabaseService) -> None:
    """Настройки через callback."""
    await cmd_settings(callback.message, db)
    await callback.answer()


@router.callback_query(F.data == "toggle_ai")
async def callback_toggle_ai(callback: types.CallbackQuery, db: DatabaseService) -> None:
    """Включение/выключение AI."""
    user = await db.get_user(callback.from_user.id)
    
    if user:
        new_status = not user.ai_enabled
        await db.update_user(user.id, ai_enabled=new_status)
        
        status_text = "включены" if new_status else "выключены"
        await callback.answer(f"AI-напоминания {status_text}!")
        
        # Обновляем сообщение
        await cmd_settings(callback.message, db)
    else:
        await callback.answer("Ошибка! Сначала запустите /start")


@router.callback_query(F.data == "toggle_notifications")
async def callback_toggle_notifications(
    callback: types.CallbackQuery,
    db: DatabaseService
) -> None:
    """Включение/выключение уведомлений."""
    user = await db.get_user(callback.from_user.id)
    
    if user:
        new_status = not user.notification_enabled
        await db.update_user(user.id, notification_enabled=new_status)
        
        status_text = "включены" if new_status else "выключены"
        await callback.answer(f"Уведомления {status_text}!")
        
        # Обновляем сообщение
        await cmd_settings(callback.message, db)
    else:
        await callback.answer("Ошибка! Сначала запустите /start")


@router.callback_query(F.data == "change_timezone")
async def callback_change_timezone(callback: types.CallbackQuery) -> None:
    """Изменение часового пояса."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌍 UTC", callback_data="tz:UTC"),
            InlineKeyboardButton(text="🇷🇺 Москва (UTC+3)", callback_data="tz:Europe/Moscow")
        ],
        [
            InlineKeyboardButton(text="🇰🇿 Алматы (UTC+5)", callback_data="tz:Asia/Almaty"),
            InlineKeyboardButton(text="🇹🇭 Бангкок (UTC+7)", callback_data="tz:Asia/Bangkok")
        ],
        [
            InlineKeyboardButton(text="🇨🇳 Шанхай (UTC+8)", callback_data="tz:Asia/Shanghai"),
            InlineKeyboardButton(text="🇯🇵 Токио (UTC+9)", callback_data="tz:Asia/Tokyo")
        ],
        [
            InlineKeyboardButton(text="« Назад", callback_data="settings")
        ]
    ])
    
    await callback.message.edit_text(
        "🌍 <b>Выбор часового пояса</b>\n\n"
        "Выбери свой часовой пояс:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tz:"))
async def callback_set_timezone(
    callback: types.CallbackQuery,
    db: DatabaseService
) -> None:
    """Установка часового пояса."""
    timezone = callback.data.split(":")[1]
    
    await db.update_user(callback.from_user.id, timezone=timezone)
    await callback.answer(f"Часовой пояс изменён на {timezone}!")
    
    # Обновляем сообщение настроек
    await cmd_settings(callback.message, db)
