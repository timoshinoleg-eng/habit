"""
Rate limiting для AI-запросов и других операций.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RateLimitEntry:
    """Запись для отслеживания rate limit."""
    count: int = 0
    window_start: datetime = field(default_factory=datetime.utcnow)
    last_request: datetime = field(default_factory=datetime.utcnow)


class RateLimiter:
    """
    Rate limiter с поддержкой per-user и global limits.
    In-memory реализация (для продакшена лучше Redis).
    """
    
    def __init__(
        self,
        user_limit: int = 10,  # запросов в минуту на пользователя
        user_window: int = 60,  # секунд
        global_limit: int = 100,  # глобальных запросов в минуту
        global_window: int = 60  # секунд
    ):
        self.user_limit = user_limit
        self.user_window = timedelta(seconds=user_window)
        self.global_limit = global_limit
        self.global_window = timedelta(seconds=global_window)
        
        # Хранилище: user_id -> RateLimitEntry
        self._user_limits: Dict[int, RateLimitEntry] = {}
        
        # Глобальный счетчик
        self._global_limit = RateLimitEntry()
        
        logger.info(
            f"RateLimiter initialized: user_limit={user_limit}/{user_window}s, "
            f"global_limit={global_limit}/{global_window}s"
        )
    
    def _cleanup_old_entries(self):
        """Очистка устаревших записей."""
        now = datetime.utcnow()
        
        # Очистка пользователей
        expired = [
            user_id for user_id, entry in self._user_limits.items()
            if now - entry.window_start > self.user_window
        ]
        for user_id in expired:
            del self._user_limits[user_id]
        
        # Очистка глобального счетчика
        if now - self._global_limit.window_start > self.global_window:
            self._global_limit = RateLimitEntry()
    
    def check_rate_limit(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Проверка rate limit для пользователя.
        
        Returns:
            Tuple[allowed: bool, reason: Optional[str]]
        """
        now = datetime.utcnow()
        self._cleanup_old_entries()
        
        # Проверка глобального лимита
        if now - self._global_limit.window_start > self.global_window:
            self._global_limit = RateLimitEntry(window_start=now)
        
        if self._global_limit.count >= self.global_limit:
            logger.warning(f"Global rate limit exceeded: {self._global_limit.count}/{self.global_limit}")
            return False, "🌐 Слишком много запросов. Попробуйте позже."
        
        # Проверка пользовательского лимита
        if user_id not in self._user_limits:
            self._user_limits[user_id] = RateLimitEntry(window_start=now)
        
        user_entry = self._user_limits[user_id]
        
        # Сброс окна если прошло достаточно времени
        if now - user_entry.window_start > self.user_window:
            user_entry = RateLimitEntry(window_start=now)
            self._user_limits[user_id] = user_entry
        
        if user_entry.count >= self.user_limit:
            remaining = self.user_window - (now - user_entry.window_start)
            logger.warning(f"User {user_id} rate limit exceeded: {user_entry.count}/{self.user_limit}")
            return False, f"⏳ Слишком много запросов. Попробуйте через {remaining.seconds} секунд."
        
        return True, None
    
    def record_request(self, user_id: int):
        """Запись успешного запроса."""
        now = datetime.utcnow()
        
        # Обновляем глобальный счетчик
        self._global_limit.count += 1
        self._global_limit.last_request = now
        
        # Обновляем пользовательский счетчик
        if user_id not in self._user_limits:
            self._user_limits[user_id] = RateLimitEntry(window_start=now)
        
        self._user_limits[user_id].count += 1
        self._user_limits[user_id].last_request = now
        
        logger.debug(f"Rate limit recorded for user {user_id}: {self._user_limits[user_id].count}/{self.user_limit}")
    
    def get_status(self, user_id: int) -> Dict:
        """Получение текущего статуса rate limit для пользователя."""
        now = datetime.utcnow()
        
        if user_id not in self._user_limits:
            return {
                "user_limit": self.user_limit,
                "user_used": 0,
                "user_remaining": self.user_limit,
                "global_limit": self.global_limit,
                "global_used": self._global_limit.count
            }
        
        user_entry = self._user_limits[user_id]
        
        # Если окно истекло, показываем полный лимит
        if now - user_entry.window_start > self.user_window:
            user_used = 0
        else:
            user_used = user_entry.count
        
        return {
            "user_limit": self.user_limit,
            "user_used": user_used,
            "user_remaining": max(0, self.user_limit - user_used),
            "user_reset_in": max(0, (self.user_window - (now - user_entry.window_start)).seconds),
            "global_limit": self.global_limit,
            "global_used": self._global_limit.count,
            "global_remaining": max(0, self.global_limit - self._global_limit.count)
        }


# Глобальный экземпляр rate limiter для AI
ai_rate_limiter = RateLimiter(
    user_limit=10,      # 10 запросов в минуту на пользователя
    user_window=60,     # окно 60 секунд
    global_limit=100,   # 100 запросов в минуту глобально
    global_window=60
)
