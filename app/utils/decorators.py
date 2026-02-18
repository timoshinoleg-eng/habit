"""
Декораторы для хендлеров.
"""

import functools
import logging
from typing import Callable

from aiogram.types import Message, CallbackQuery

from app.config import settings

logger = logging.getLogger(__name__)


def admin_required(handler: Callable) -> Callable:
    """
    Декоратор для проверки прав администратора.
    
    Проверяет, есть ли ID пользователя в списке ADMIN_IDS.
    Если нет - отправляет сообщение об отказе в доступе.
    
    Usage:
        @router.message(Command("admin_stats"))
        @admin_required
        async def cmd_admin_stats(message: Message, db: DatabaseService):
            ...
    """
    @functools.wraps(handler)
    async def wrapper(event, *args, **kwargs):
        # Получаем user_id в зависимости от типа события
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        
        if not user_id:
            logger.warning("Admin check failed: no user_id")
            return None
        
        # Проверяем, есть ли пользователь в списке админов
        if user_id not in settings.admin_ids:
            logger.warning(f"Access denied for user {user_id}")
            
            # Отправляем сообщение об отказе
            deny_message = "🚫 <b>Доступ запрещён</b>\n\nЭта команда только для администраторов."
            
            try:
                if isinstance(event, Message):
                    await event.answer(deny_message, parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Доступ запрещён!", show_alert=True)
            except Exception as e:
                logger.error(f"Failed to send access denied message: {e}")
            
            return None
        
        # Пользователь админ - выполняем хендлер
        logger.debug(f"Admin access granted for user {user_id}")
        return await handler(event, *args, **kwargs)
    
    return wrapper


def log_execution_time(handler: Callable) -> Callable:
    """
    Декоратор для логирования времени выполнения хендлера.
    Полезно для отладки медленных операций.
    """
    @functools.wraps(handler)
    async def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        
        try:
            result = await handler(*args, **kwargs)
            return result
        finally:
            execution_time = (time.time() - start_time) * 1000
            logger.debug(
                f"Handler {handler.__name__} executed in {execution_time:.2f}ms"
            )
    
    return wrapper


def retry_on_error(max_retries: int = 3, exceptions: tuple = (Exception,)):
    """
    Декоратор для повторных попыток при ошибках.
    
    Args:
        max_retries: Максимальное количество попыток
        exceptions: Кортеж исключений для перехвата
    
    Usage:
        @retry_on_error(max_retries=3, exceptions=(NetworkError,))
        async def send_message_with_retry(bot, chat_id, text):
            await bot.send_message(chat_id, text)
    """
    def decorator(handler: Callable) -> Callable:
        @functools.wraps(handler)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    return await handler(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt}/{max_retries} failed for {handler.__name__}: {e}"
                    )
                    
                    if attempt < max_retries:
                        import asyncio
                        await asyncio.sleep(0.5 * attempt)  # Экспоненциальная задержка
            
            # Все попытки исчерпаны
            logger.error(
                f"All {max_retries} attempts failed for {handler.__name__}: {last_exception}"
            )
            raise last_exception
        
        return wrapper
    return decorator
