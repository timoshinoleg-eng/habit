"""
Конфигурация приложения через Pydantic Settings.
Все чувствительные данные загружаются из переменных окружения.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Настройки приложения."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Игнорировать лишние переменные
    )
    
    # Telegram Bot
    bot_token: Optional[str] = Field(
        default=None,
        description="Токен Telegram бота от @BotFather"
    )
    
    # OpenRouter AI
    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="API ключ OpenRouter"
    )
    openrouter_model: str = Field(
        default="meta-llama/llama-3.1-8b-instruct",
        description="Модель OpenRouter (бесплатная tier)"
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="Базовый URL OpenRouter API"
    )
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./habitmax.db",
        description="URL базы данных (SQLite или PostgreSQL)"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Уровень логирования")
    
    # Admin
    admin_ids: List[int] = Field(
        default_factory=list,
        description="Список ID администраторов"
    )
    
    # Webhook (опционально)
    use_webhook: bool = Field(default=False, description="Использовать webhook")
    webhook_host: Optional[str] = Field(default=None, description="Хост webhook")
    webhook_path: str = Field(default="/webhook", description="Путь webhook")
    webhook_port: int = Field(default=8080, description="Порт webhook")
    
    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        """Парсинг списка ID администраторов из строки."""
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v or []
    
    @property
    def is_postgres(self) -> bool:
        """Проверка, используется ли PostgreSQL."""
        return "postgresql" in self.database_url.lower()
    
    @property
    def webhook_url(self) -> Optional[str]:
        """Полный URL webhook."""
        if self.webhook_host:
            return f"{self.webhook_host.rstrip('/')}{self.webhook_path}"
        return None


# Глобальный экземпляр настроек
settings = Settings()
