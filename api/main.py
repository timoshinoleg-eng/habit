"""
FastAPI приложение для HabitMax Mini App.
"""

import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from api.middleware.telegram_auth import TelegramAuthMiddleware, get_current_user_id
from api.models.base import engine, Base
from api.routers import habits, ai, user
from api.services.ai_service import AIService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="HabitMax Mini App API",
    description="API для Telegram Mini App трекера привычек",
    version="1.0.0"
)

# CORS для разработки (фронтенд на Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telegram Auth Middleware
app.add_middleware(
    TelegramAuthMiddleware,
    bot_token=settings.bot_token
)

# Dependency для AI сервиса
async def get_ai_service():
    return AIService()


@app.on_event("startup")
async def startup():
    """Инициализация при старте."""
    logger.info("Starting HabitMax Mini App API...")
    # Создаем таблицы для новых моделей
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


@app.on_event("shutdown")
async def shutdown():
    """Очистка при остановке."""
    logger.info("Shutting down...")


@app.get("/health")
async def health_check():
    """Проверка здоровья API."""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/me")
async def get_current_user(
    request: Request,
    user_id: int = Depends(get_current_user_id)
):
    """Получение данных текущего пользователя."""
    user_data = getattr(request.state, "telegram_user", {})
    return {
        "id": user_id,
        "first_name": user_data.get("first_name"),
        "last_name": user_data.get("last_name"),
        "username": user_data.get("username"),
        "photo_url": user_data.get("photo_url")
    }


# Подключаем роутеры
app.include_router(habits.router, prefix="/api/habits", tags=["habits"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(user.router, prefix="/api/user", tags=["user"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
