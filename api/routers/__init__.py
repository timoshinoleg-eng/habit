from .habits import router as habits_router
from .ai import router as ai_router
from .user import router as user_router

__all__ = ['habits_router', 'ai_router', 'user_router']
