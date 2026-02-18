"""
HabitMax Telegram Bot
Мигрировано с Max Messenger на Telegram с AI интеграцией

Точка входа приложения.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import settings
from app.handlers import common_router, habits_router, ai_router, admin_router
from app.middlewares import ServicesMiddleware
from app.middlewares.fsm_timeout import FSMTimeoutMiddleware
from app.services import DatabaseService, AIService, ReminderService
from app.utils import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная функция запуска бота."""
    
    # Настройка логирования
    setup_logging()
    logger.info("Starting HabitMax Telegram Bot...")
    
    # Проверка обязательных настроек
    if not settings.bot_token:
        logger.error("BOT_TOKEN не задан!")
        print("\n" + "="*60)
        print("[ERROR] BOT_TOKEN не задан!")
        print("="*60)
        print("\n1. Скопируйте файл .env.example в .env:")
        print("   Windows: copy .env.example .env")
        print("   Linux/Mac: cp .env.example .env")
        print("\n2. Отредактируйте .env и добавьте:")
        print("   BOT_TOKEN=your_telegram_bot_token_here")
        print("   OPENROUTER_API_KEY=your_openrouter_api_key_here")
        print("\nПолучить BOT_TOKEN: https://t.me/BotFather")
        print("Получить OPENROUTER_API_KEY: https://openrouter.ai/keys")
        print("="*60 + "\n")
        return
    
    if not settings.openrouter_api_key:
        logger.warning("OPENROUTER_API_KEY не задан! AI-функции будут недоступны.")
    
    # Инициализация сервисов
    db_service = DatabaseService()
    await db_service.init_db()
    logger.info("Database initialized")
    
    # Создание бота и диспетчера
    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Инициализация AI-сервиса
    ai_service = AIService(db_service)
    logger.info(f"AI Service initialized with model: {settings.openrouter_model}")
    
    # Инициализация сервиса напоминаний
    reminder_service = ReminderService(bot, db_service, ai_service)
    await reminder_service.start()
    logger.info("Reminder service started")
    
    # Регистрация middleware
    # FSM таймаут (должен быть первым для проверки истечения)
    dp.message.middleware(FSMTimeoutMiddleware(timeout_minutes=10))
    dp.callback_query.middleware(FSMTimeoutMiddleware(timeout_minutes=10))
    
    # DI сервисы
    dp.message.middleware(
        ServicesMiddleware(db_service, ai_service, reminder_service)
    )
    dp.callback_query.middleware(
        ServicesMiddleware(db_service, ai_service, reminder_service)
    )
    logger.info("Middleware registered")
    
    # Регистрация роутеров
    dp.include_router(common_router)
    dp.include_router(habits_router)
    dp.include_router(ai_router)
    dp.include_router(admin_router)
    logger.info("Routers registered")
    
    # Установка команд бота
    await bot.set_my_commands([
        BotCommand(command="start", description="Zapustit bota / Glavnoe menu"),
        BotCommand(command="add_habit", description="Dobavit novuyu privychku"),
        BotCommand(command="my_habits", description="Spisok moih privychek"),
        BotCommand(command="my_progress", description="Moi progress i statistika"),
        BotCommand(command="ai_advice", description="Poluchit AI-rekomendaciyu"),
        BotCommand(command="analyze_patterns", description="Analizirovat moi patterny"),
        BotCommand(command="settings", description="Nastroiki bota"),
        BotCommand(command="help", description="Pomosh i instrukciya"),
    ])
    logger.info("Bot commands set")
    
    # Запуск поллинга
    logger.info("Bot is running!")
    try:
        await dp.start_polling(bot)
    finally:
        # Graceful shutdown
        logger.info("Shutting down...")
        await reminder_service.stop()
        await ai_service.close()
        await db_service.close()
        await bot.session.close()
        logger.info("Bot stopped gracefully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        raise
