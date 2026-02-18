"""
Клавиатуры для FSM (Finite State Machine) диалогов.
Стандартные кнопки Назад и Отмена для всех шагов.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_fsm_navigation_keyboard(
    show_back: bool = True,
    back_callback: str = "fsm:back",
    cancel_callback: str = "fsm:cancel"
) -> InlineKeyboardMarkup:
    """
    Клавиатура навигации FSM с кнопками Назад и Отмена.
    
    Args:
        show_back: Показывать ли кнопку Назад
        back_callback: Callback для кнопки Назад
        cancel_callback: Callback для кнопки Отмена
    
    Returns:
        InlineKeyboardMarkup с кнопками навигации
    """
    builder = InlineKeyboardBuilder()
    
    if show_back:
        builder.button(text="◀️ Назад", callback_data=back_callback)
    
    builder.button(text="❌ Отмена", callback_data=cancel_callback)
    
    # Если есть обе кнопки - располагаем в одну строку
    if show_back:
        builder.adjust(2)
    
    return builder.as_markup()


def get_fsm_cancel_only_keyboard(
    cancel_callback: str = "fsm:cancel"
) -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой Отмена (для первого шага)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_callback)]
    ])


def get_emoji_selection_keyboard(
    selected_emoji: str = None,
    back_callback: str = "fsm:back",
    cancel_callback: str = "fsm:cancel"
) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора эмодзи для привычки.
    
    Args:
        selected_emoji: Текущий выбранный эмодзи (для подсветки)
        back_callback: Callback для кнопки Назад
        cancel_callback: Callback для кнопки Отмена
    """
    emojis = [
        "✅", "💪", "🏃", "📚",
        "💧", "🧘", "🥗", "💊",
        "🎯", "⭐", "🔥", "❤️"
    ]
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки эмодзи (3 в ряд)
    for emoji in emojis:
        # Подсвечиваем выбранный эмодзи
        text = f"✓ {emoji}" if emoji == selected_emoji else emoji
        builder.button(text=text, callback_data=f"emoji:{emoji}")
    
    builder.adjust(4)
    
    # Кнопки навигации
    builder.button(text="◀️ Назад", callback_data=back_callback)
    builder.button(text="❌ Отмена", callback_data=cancel_callback)
    builder.adjust(2)
    
    return builder.as_markup()


def get_frequency_selection_keyboard(
    selected_frequency: str = None,
    back_callback: str = "fsm:back",
    cancel_callback: str = "fsm:cancel"
) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора частоты привычки.
    
    Args:
        selected_frequency: Текущая выбранная частота
        back_callback: Callback для кнопки Назад
        cancel_callback: Callback для кнопки Отмена
    """
    frequencies = [
        ("📅 Каждый день", "daily"),
        ("📆 По будням", "weekdays"),
        ("🎉 По выходным", "weekends"),
        ("🗓 Раз в неделю", "weekly"),
    ]
    
    builder = InlineKeyboardBuilder()
    
    for text, value in frequencies:
        # Подсвечиваем выбранную частоту
        btn_text = f"✓ {text}" if value == selected_frequency else text
        builder.button(text=btn_text, callback_data=f"freq:{value}")
    
    builder.adjust(1)  # По одной кнопке в строке
    
    # Кнопки навигации
    builder.button(text="◀️ Назад", callback_data=back_callback)
    builder.button(text="❌ Отмена", callback_data=cancel_callback)
    builder.adjust(2)
    
    return builder.as_markup()


def get_time_selection_keyboard(
    back_callback: str = "fsm:back",
    cancel_callback: str = "fsm:cancel"
) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора времени напоминания.
    """
    builder = InlineKeyboardBuilder()
    
    # Предустановленное время
    builder.button(text="🌅 Утро (07:00)", callback_data="time:07:00")
    builder.button(text="🌇 Вечер (20:00)", callback_data="time:20:00")
    builder.button(text="🕐 День (13:00)", callback_data="time:13:00")
    builder.button(text="🌙 Ночь (22:00)", callback_data="time:22:00")
    builder.adjust(2)
    
    builder.button(text="🚫 Без напоминания", callback_data="time:none")
    builder.adjust(1)
    
    builder.button(text="◀️ Назад", callback_data=back_callback)
    builder.button(text="❌ Отмена", callback_data=cancel_callback)
    builder.adjust(2)
    
    return builder.as_markup()


def get_confirmation_keyboard(
    confirm_callback: str = "fsm:confirm",
    back_callback: str = "fsm:back",
    cancel_callback: str = "fsm:cancel"
) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения создания привычки.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Создать привычку", callback_data=confirm_callback)],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback),
            InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_callback)
        ]
    ])


def get_invalid_input_keyboard(
    hint: str = None,
    back_callback: str = "fsm:back",
    cancel_callback: str = "fsm:cancel"
) -> InlineKeyboardMarkup:
    """
    Клавиатура при неверном вводе.
    Показывает подсказку и кнопки навигации.
    
    Args:
        hint: Подсказка о правильном формате ввода
        back_callback: Callback для кнопки Назад
        cancel_callback: Callback для кнопки Отмена
    """
    builder = InlineKeyboardBuilder()
    
    if hint:
        builder.button(text=f"💡 {hint}", callback_data="noop")
    
    builder.button(text="🔄 Попробовать снова", callback_data="fsm:retry")
    builder.button(text="◀️ Назад", callback_data=back_callback)
    builder.button(text="❌ Отмена", callback_data=cancel_callback)
    builder.adjust(1, 2)
    
    return builder.as_markup()
