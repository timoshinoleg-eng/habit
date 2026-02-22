# -*- coding: utf-8 -*-
"""
Handlers package
"""
from aiogram import Router

from app.handlers.common import router as common_router
from app.handlers.habits import router as habits_router
from app.handlers.finance import router as finance_router


def get_all_routers() -> list[Router]:
    """Get all handlers routers"""
    return [
        common_router,
        habits_router,
        finance_router,
    ]


__all__ = [
    'get_all_routers',
    'common_router',
    'habits_router',
    'finance_router',
]
