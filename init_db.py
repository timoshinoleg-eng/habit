# -*- coding: utf-8 -*-
"""
Database initialization script
Run this to create all tables without using alembic
"""
import asyncio
import logging

from app.models import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Initialize database"""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully!")
    logger.info("You can now run the bot with: python main.py")


if __name__ == "__main__":
    asyncio.run(main())
