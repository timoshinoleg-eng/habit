"""
Middleware для управления таймаутом FSM состояний.
Автоматически сбрасывает FSM при бездействии пользователя.
"""

import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Awaitable, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

logger = logging.getLogger(__name__)


class FSMTimeoutMiddleware(BaseMiddleware):
    """
    Middleware для автоматического сброса FSM по таймауту.
    
    Проверяет время последней активности и сбрасывает FSM,
    если пользователь неактивен дольше указанного времени.
    """
    
    def __init__(self, timeout_minutes: int = 10):
        """
        Args:
            timeout_minutes: Время бездействия в минутах для сброса FSM
        """
        super().__init__()
        self.timeout = timedelta(minutes=timeout_minutes)
        self.timeout_minutes = timeout_minutes
        logger.info(f"FSMTimeoutMiddleware initialized with timeout={timeout_minutes}min")
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Проверка таймаута FSM перед обработкой события.
        """
        # Получаем FSM context если он есть
        fsm_context: Optional[FSMContext] = data.get("state")
        
        if fsm_context:
            # Проверяем, истек ли таймаут
            is_expired, state_data = await self._check_timeout(fsm_context)
            
            if is_expired and state_data:
                # FSM истек - сбрасываем и отправляем уведомление
                await self._handle_timeout(event, fsm_context, data)
                
                # Обновляем data после сброса
                data["state"] = fsm_context
        
        # Обновляем время последней активности
        if fsm_context:
            await self._update_last_activity(fsm_context)
        
        return await handler(event, data)
    
    async def _check_timeout(self, fsm_context: FSMContext) -> tuple[bool, Optional[Dict]]:
        """
        Проверка, истек ли таймаут FSM.
        
        Returns:
            Tuple[expired: bool, state_data: dict]
        """
        try:
            state_data = await fsm_context.get_data()
            
            if not state_data:
                return False, None
            
            # Проверяем, есть ли состояние
            current_state = await fsm_context.get_state()
            if not current_state:
                return False, None
            
            # Получаем время последней активности
            last_activity = state_data.get("_last_activity")
            
            if not last_activity:
                # Нет записи о времени - считаем, что только начали
                return False, state_data
            
            # Парсим время (может быть строкой из JSON)
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity)
            
            # Проверяем таймаут
            if datetime.utcnow() - last_activity > self.timeout:
                return True, state_data
            
            return False, state_data
            
        except Exception as e:
            logger.error(f"Error checking FSM timeout: {e}")
            return False, None
    
    async def _handle_timeout(
        self,
        event: TelegramObject,
        fsm_context: FSMContext,
        data: Dict[str, Any]
    ) -> None:
        """Обработка истечения таймаута FSM."""
        # Сбрасываем FSM
        await fsm_context.clear()
        
        # Отправляем уведомление пользователю
        timeout_msg = (
            f"⏰ <b>Сессия завершена</b>\n\n"
            f"Прошло больше {self.timeout_minutes} минут бездействия.\n"
            f"Начни заново, если хочешь продолжить."
        )
        
        try:
            if isinstance(event, Message):
                await event.answer(timeout_msg, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.message.edit_text(timeout_msg, parse_mode="HTML")
                await event.answer("Сессия завершена", show_alert=True)
        except Exception as e:
            logger.error(f"Failed to send timeout notification: {e}")
    
    async def _update_last_activity(self, fsm_context: FSMContext) -> None:
        """Обновление времени последней активности в FSM."""
        try:
            await fsm_context.update_data(_last_activity=datetime.utcnow())
        except Exception as e:
            logger.error(f"Error updating FSM last activity: {e}")


class FSMStateHistory:
    """
    Класс для управления историей состояний FSM.
    Позволяет реализовать кнопку "Назад".
    """
    
    @staticmethod
    async def push_state(fsm_context: FSMContext, state: str, data: Dict = None) -> None:
        """
        Сохранение текущего состояния в историю.
        
        Args:
            fsm_context: Контекст FSM
            state: Текущее состояние
            data: Данные состояния (опционально)
        """
        if not fsm_context:
            return
        
        try:
            current_data = await fsm_context.get_data()
            history = current_data.get("_state_history", [])
            
            # Добавляем текущее состояние в историю
            history_entry = {
                "state": state,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            history.append(history_entry)
            
            # Ограничиваем историю последними 10 состояниями
            history = history[-10:]
            
            await fsm_context.update_data(_state_history=history)
            
        except Exception as e:
            logger.error(f"Error pushing state to history: {e}")
    
    @staticmethod
    async def pop_state(fsm_context: FSMContext) -> Optional[Dict]:
        """
        Возврат к предыдущему состоянию из истории.
        
        Returns:
            Данные предыдущего состояния или None если история пуста
        """
        if not fsm_context:
            return None
        
        try:
            current_data = await fsm_context.get_data()
            history = current_data.get("_state_history", [])
            
            if len(history) < 2:
                # Нет предыдущего состояния
                return None
            
            # Удаляем текущее состояние
            history.pop()
            
            # Получаем предыдущее состояние
            previous = history[-1] if history else None
            
            # Обновляем историю
            await fsm_context.update_data(_state_history=history)
            
            return previous
            
        except Exception as e:
            logger.error(f"Error popping state from history: {e}")
            return None
    
    @staticmethod
    async def get_history(fsm_context: FSMContext) -> list:
        """Получение всей истории состояний."""
        if not fsm_context:
            return []
        
        try:
            current_data = await fsm_context.get_data()
            return current_data.get("_state_history", [])
        except Exception:
            return []
    
    @staticmethod
    async def clear_history(fsm_context: FSMContext) -> None:
        """Очистка истории состояний."""
        if not fsm_context:
            return
        
        try:
            await fsm_context.update_data(_state_history=[])
        except Exception as e:
            logger.error(f"Error clearing state history: {e}")
