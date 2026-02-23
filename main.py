# -*- coding: utf-8 -*-
"""
HabitMax Bot - Main entry point
Telegram bot for habit tracking with AI recommendations
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import BOT_TOKEN, LOG_LEVEL, FINANCE_REMINDER_HOUR, FINANCE_REMINDER_MINUTE
from app.models import init_db, get_db
from app.handlers import get_all_routers
from app.handlers.habits import preload_habits_cache
from app.services.finance_reminder import FinanceReminderService
from app.utils.middleware import DatabaseMiddleware, CallbackDatabaseMiddleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, dispatcher: Dispatcher, scheduler: AsyncIOScheduler):
    """Actions on bot startup"""
    logger.info("Starting HabitMax Bot...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Preload habits cache
    async for db in get_db():
        await preload_habits_cache(db)
        break
    logger.info("Cache preloaded")
    
    # Setup finance reminders
    finance_reminder = FinanceReminderService(bot, scheduler)
    finance_reminder.schedule(FINANCE_REMINDER_HOUR, FINANCE_REMINDER_MINUTE)
    logger.info(f"Finance reminders scheduled at {FINANCE_REMINDER_HOUR:02d}:{FINANCE_REMINDER_MINUTE:02d}")
    
    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")
    
    # Notify bot owner (optional)
    logger.info("Bot started successfully!")


async def on_shutdown():
    """Actions on bot shutdown"""
    logger.info("Bot is shutting down...")


async def main():
    """Main function"""
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Initialize scheduler
    scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
    
    # Register startup handler
    async def _on_startup(dispatcher: Dispatcher):
        await on_startup(bot, dispatcher, scheduler)
    
    async def _on_shutdown(dispatcher: Dispatcher):
        await on_shutdown()
    
    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)
    
    # Register middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(CallbackDatabaseMiddleware())
    logger.info("Middleware registered")
    
    # Register all handlers
    for router in get_all_routers():
        dp.include_router(router)
    logger.info("All handlers registered")
    
    # Delete webhook and start polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
        sys.exit(0)
