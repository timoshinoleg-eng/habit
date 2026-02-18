"""
Reply keyboards (кнопки внизу экрана) для бота.
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Главное меню с Reply кнопками.
    Постоянно доступно внизу экрана.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Добавить привычку"),
                KeyboardButton(text="📋 Мои привычки"),
            ],
            [
                KeyboardButton(text="📊 Прогресс"),
                KeyboardButton(text="🤖 AI"),
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,  # Кнопки подстраиваются под размер экрана
        input_field_placeholder="Выбери действие...",  # Текст в поле ввода
        selective=False,  # Показывать всем пользователям в чате
    )
    return keyboard


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой Отмена (для FSM)."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True,  # Скрыть после нажатия
    )


def get_confirm_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура подтверждения (Да/Нет)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да")],
            [KeyboardButton(text="❌ Нет")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Удалить Reply клавиатуру."""
    return ReplyKeyboardRemove(remove_keyboard=True)


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню для администраторов."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="📢 Рассылка"),
            ],
            [
                KeyboardButton(text="👥 Пользователи"),
                KeyboardButton(text="🔧 Настройки"),
            ],
            [KeyboardButton(text="« В главное меню")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Админ-панель...",
    )
