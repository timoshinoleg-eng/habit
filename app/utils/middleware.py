# -*- coding: utf-8 -*-
"""
Middleware for dependency injection
"""
from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import AsyncSessionLocal


class DatabaseMiddleware(BaseMiddleware):
    """Middleware to inject database session into handlers"""
    
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["db"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                raise
            finally:
                await session.close()


class CallbackDatabaseMiddleware(BaseMiddleware):
    """Middleware to inject database session into callback handlers"""
    
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any]
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["db"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                raise
            finally:
                await session.close()
