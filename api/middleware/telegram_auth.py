"""
Middleware для валидации initData от Telegram Web App.
Проверка HMAC-SHA256 подписи.
"""

import hashlib
import hmac
import json
import logging
from typing import Optional
from urllib.parse import parse_qsl

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


class TelegramAuthMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки подлинности запросов от Telegram Mini App."""
    
    def __init__(self, app, bot_token: str):
        super().__init__(app)
        self.bot_token = bot_token
        # Создаем secret key из токена бота
        self.secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()
    
    async def dispatch(self, request: Request, call_next):
        """Проверка подписи для защищенных эндпоинтов."""
        
        # Пропускаем проверку для некоторых путей
        public_paths = ["/health", "/docs", "/openapi.json", "/api/health"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # Получаем initData из заголовка или query параметра
        init_data = request.headers.get("X-Telegram-Init-Data")
        
        if not init_data:
            # Пробуем получить из query для разработки
            init_data = request.query_params.get("init_data")
        
        if not init_data:
            logger.warning(f"Missing initData for {request.url.path}")
            raise HTTPException(status_code=401, detail="Missing Telegram auth data")
        
        # Валидируем подпись
        is_valid, user_data = self._validate_init_data(init_data)
        
        if not is_valid:
            logger.warning(f"Invalid signature for {request.url.path}")
            raise HTTPException(status_code=401, detail="Invalid Telegram auth signature")
        
        # Сохраняем данные пользователя в request.state
        request.state.telegram_user = user_data
        request.state.user_id = user_data.get("id")
        
        return await call_next(request)
    
    def _validate_init_data(self, init_data: str) -> tuple[bool, Optional[dict]]:
        """
        Валидация initData от Telegram.
        
        Args:
            init_data: Строка initData от Telegram WebApp
            
        Returns:
            tuple: (is_valid, user_data)
        """
        try:
            # Парсим параметры
            parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
            
            # Получаем hash
            received_hash = parsed_data.pop("hash", None)
            if not received_hash:
                return False, None
            
            # Сортируем параметры и создаем data_check_string
            data_check_string = "\n".join(
                f"{k}={v}" for k, v in sorted(parsed_data.items())
            )
            
            # Вычисляем HMAC
            computed_hash = hmac.new(
                key=self.secret_key,
                msg=data_check_string.encode(),
                digestmod=hashlib.sha256
            ).hexdigest()
            
            # Проверяем подпись
            if computed_hash != received_hash:
                return False, None
            
            # Проверяем срок действия (не старше 24 часов)
            import time
            auth_date = int(parsed_data.get("auth_date", 0))
            if time.time() - auth_date > 86400:
                return False, None
            
            # Извлекаем данные пользователя
            user_data = json.loads(parsed_data.get("user", "{}"))
            
            return True, user_data
            
        except Exception as e:
            logger.error(f"Error validating initData: {e}")
            return False, None


class TelegramAuth(HTTPBearer):
    """Dependency для получения данных пользователя в эндпоинтах."""
    
    async def __call__(self, request: Request) -> dict:
        """Возвращает данные пользователя Telegram."""
        user = getattr(request.state, "telegram_user", None)
        if not user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        return user


def get_current_user(request: Request) -> dict:
    """Dependency для получения текущего пользователя."""
    user = getattr(request.state, "telegram_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return user


def get_current_user_id(request: Request) -> int:
    """Dependency для получения ID текущего пользователя."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return int(user_id)
