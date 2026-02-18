"""
Настройка логирования.
"""

import logging
import sys

from app.config import settings


def setup_logging() -> None:
    """Настройка формата и уровня логирования."""
    
    # Формат логов
    log_format = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Настройка базового логирования
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Уменьшаем шум от внешних библиотек
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # Наши модули логируем подробнее
    logging.getLogger("app").setLevel(getattr(logging, settings.log_level.upper()))
