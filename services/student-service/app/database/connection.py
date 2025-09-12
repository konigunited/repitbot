# -*- coding: utf-8 -*-
"""
Database Connection and Session Management
Управление подключением к базе данных
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager

from ..core.config import settings

logger = logging.getLogger(__name__)

# Создание асинхронного движка
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.CONNECTION_POOL_SIZE,
    max_overflow=settings.CONNECTION_POOL_MAX_OVERFLOW,
    poolclass=NullPool if "sqlite" in settings.DATABASE_URL else None,
    future=True
)

# Создание фабрики сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


async def init_db():
    """Инициализация базы данных"""
    try:
        logger.info("Initializing database...")
        
        # Импортируем все модели для создания таблиц
        from ..models import student, achievement, progress, gamification
        
        async with engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def close_db():
    """Закрытие соединений с базой данных"""
    try:
        logger.info("Closing database connections...")
        await engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise


@asynccontextmanager
async def get_db_session():
    """Контекстный менеджер для получения сессии БД"""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db():
    """Dependency для получения сессии БД в FastAPI"""
    async with get_db_session() as session:
        yield session