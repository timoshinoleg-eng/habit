"""
Хендлеры для AI-функционала.
/ai_advice, анализ паттернов и т.д.
"""

import logging

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.services.database import DatabaseService
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("ai_advice"))
async def cmd_ai_advice(message: types.Message, db: DatabaseService, ai: AIService) -> None:
    """Получить AI-рекомендацию."""
    # Показываем, что AI "думает"
    thinking_msg = await message.answer("🤖 AI анализирует твои привычки...")
    
    try:
        user = await db.get_or_create_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Получаем рекомендацию
        recommendation = await ai.get_habit_recommendation(user)
        
        # Удаляем сообщение о загрузке
        await thinking_msg.delete()
        
        # Формируем ответ
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Мои привычки",
                    callback_data="list_habits"
                ),
                InlineKeyboardButton(
                    text="📊 Прогресс",
                    callback_data="show_progress"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Новый совет",
                    callback_data="ai_advice"
                ),
                InlineKeyboardButton(
                    text="« Назад",
                    callback_data="back_to_menu"
                )
            ]
        ])
        
        await message.answer(
            f"🤖 <b>AI-рекомендация:</b>\n\n"
            f"{recommendation}\n\n"
            f"<i>Совет основан на твоих данных и общих практиках "
            f"формирования привычек.</i>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in ai_advice: {e}")
        await thinking_msg.delete()
        await message.answer(
            "❌ Произошла ошибка при получении рекомендации.\n"
            "Попробуй позже или проверь настройки AI в /settings"
        )


@router.callback_query(F.data == "ai_advice")
async def callback_ai_advice(
    callback: types.CallbackQuery,
    db: DatabaseService,
    ai: AIService
) -> None:
    """AI-совет через callback."""
    await callback.answer("🤖 Думаю...")
    
    try:
        user = await db.get_or_create_user(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name
        )
        
        # Получаем рекомендацию
        recommendation = await ai.get_habit_recommendation(user)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Мои привычки",
                    callback_data="list_habits"
                ),
                InlineKeyboardButton(
                    text="📊 Прогресс",
                    callback_data="show_progress"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Новый совет",
                    callback_data="ai_advice"
                ),
                InlineKeyboardButton(
                    text="« Назад",
                    callback_data="back_to_menu"
                )
            ]
        ])
        
        await callback.message.edit_text(
            f"🤖 <b>AI-рекомендация:</b>\n\n"
            f"{recommendation}\n\n"
            f"<i>Совет основан на твоих данных и общих практиках.</i>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in callback_ai_advice: {e}")
        await callback.answer("Ошибка! Попробуй позже.", show_alert=True)


@router.message(Command("analyze_patterns"))
async def cmd_analyze_patterns(
    message: types.Message,
    db: DatabaseService,
    ai: AIService
) -> None:
    """Анализ паттернов пользователя."""
    analyzing_msg = await message.answer(
        "📊 Анализирую твои паттерны...\n"
        "Это может занять несколько секунд."
    )
    
    try:
        # Запускаем анализ
        patterns = await ai.analyze_user_patterns(message.from_user.id)
        
        await analyzing_msg.delete()
        
        if not patterns:
            await message.answer(
                "📊 Недостаточно данных для анализа.\n\n"
                "Продолжай отмечать привычки, и AI скоро выявит твои паттерны! 💪"
            )
            return
        
        # Формируем отчёт
        report = "📈 <b>Анализ твоих паттернов:</b>\n\n"
        
        if patterns.get("most_productive_day"):
            day_names = {
                "monday": "Понедельник",
                "tuesday": "Вторник",
                "wednesday": "Среда",
                "thursday": "Четверг",
                "friday": "Пятница",
                "saturday": "Суббота",
                "sunday": "Воскресенье"
            }
            day = day_names.get(patterns["most_productive_day"], patterns["most_productive_day"])
            report += f"🗓 <b>Самый продуктивный день:</b> {day}\n"
        
        if patterns.get("most_productive_time"):
            time_names = {
                "morning": "Утро 🌅",
                "afternoon": "День ☀️",
                "evening": "Вечер 🌙"
            }
            time_of_day = time_names.get(patterns["most_productive_time"], patterns["most_productive_time"])
            report += f"⏰ <b>Самое продуктивное время:</b> {time_of_day}\n"
        
        if patterns.get("struggling_habits"):
            report += f"\n⚠️ <b>Требуют внимания:</b>\n"
            for habit_name in patterns["struggling_habits"]:
                report += f"  • {habit_name}\n"
            report += "\n<i>Совет: попробуй упростить эти привычки или изменить время.</i>"
        
        report += "\n\n💡 Эти данные помогут AI давать более точные рекомендации!"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 Получить совет",
                    callback_data="ai_advice"
                ),
                InlineKeyboardButton(
                    text="« Назад",
                    callback_data="back_to_menu"
                )
            ]
        ])
        
        await message.answer(report, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in analyze_patterns: {e}")
        await analyzing_msg.delete()
        await message.answer("❌ Ошибка при анализе. Попробуй позже.")


@router.callback_query(F.data.startswith("ai_habit_advice:"))
async def callback_habit_ai_advice(
    callback: types.CallbackQuery,
    db: DatabaseService,
    ai: AIService
) -> None:
    """AI-совет для конкретной привычки."""
    habit_id = int(callback.data.split(":")[1])
    
    await callback.answer("🤖 Анализирую привычку...")
    
    try:
        user = await db.get_user(callback.from_user.id)
        habit = await db.get_habit(habit_id, callback.from_user.id)
        
        if not user or not habit:
            await callback.answer("Ошибка! Привычка не найдена.", show_alert=True)
            return
        
        # Получаем рекомендацию для конкретной привычки
        recommendation = await ai.get_habit_recommendation(user, habit)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Отметить выполнение",
                    callback_data=f"complete:{habit.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="« К привычкам",
                    callback_data="list_habits"
                )
            ]
        ])
        
        await callback.message.edit_text(
            f"{habit.emoji} <b>{habit.name}</b>\n\n"
            f"🤖 <b>AI-рекомендация:</b>\n"
            f"{recommendation}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in callback_habit_ai_advice: {e}")
        await callback.answer("Ошибка! Попробуй позже.", show_alert=True)


# ==================== Админ-команды для AI ====================

@router.message(Command("ai_status"))
async def cmd_ai_status(message: types.Message, ai: AIService) -> None:
    """Проверка статуса AI-сервиса."""
    # Проверяем доступность API с простым запросом
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'OK' only."}
    ]
    
    from app.config import settings
    
    status_text = (
        f"🤖 <b>Статус AI-сервиса:</b>\n\n"
        f"Модель: <code>{settings.openrouter_model}</code>\n"
        f"API URL: <code>{settings.openrouter_base_url}</code>\n"
    )
    
    try:
        # Делаем тестовый запрос
        response = await ai._make_request(test_messages, max_tokens=10)
        
        if response:
            status_text += f"\n✅ <b>Статус:</b> Работает\n"
            status_text += f"📝 <b>Тест:</b> {response[:50]}"
        else:
            status_text += f"\n❌ <b>Статус:</b> Не отвечает\n"
            
    except Exception as e:
        status_text += f"\n❌ <b>Ошибка:</b> {str(e)[:100]}"
    
    await message.answer(status_text, parse_mode="HTML")
