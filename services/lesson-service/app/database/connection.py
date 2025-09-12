# -*- coding: utf-8 -*-
"""
Подключение к базе данных для Lesson Service.
Async SQLAlchemy конфигурация с connection pooling и миграциями.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from alembic import command
from alembic.config import Config

from ..config.settings import get_settings
from ..models.lesson import Base

logger = logging.getLogger(__name__)
settings = get_settings()

# Создание async engine
if settings.DATABASE_URL.startswith("sqlite"):
    # Для SQLite используем aiosqlite
    database_url = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
    engine = create_async_engine(
        database_url,
        echo=settings.DATABASE_ECHO,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
        pool_pre_ping=True,
    )
else:
    # Для PostgreSQL используем asyncpg
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(
        database_url,
        echo=settings.DATABASE_ECHO,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

# Создание session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def init_database():
    """Инициализация базы данных и создание таблиц."""
    try:
        logger.info("Initializing database...")
        
        # Создание всех таблиц
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def run_migrations():
    """Запуск Alembic миграций."""
    try:
        # Настройка Alembic
        alembic_cfg = Config("alembic.ini")
        
        # Запуск миграций в отдельном thread pool
        def run_upgrade():
            command.upgrade(alembic_cfg, "head")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_upgrade)
        
        logger.info("Database migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения database session.
    Используется в FastAPI endpoints.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager для получения database session.
    Используется в сервисах и background tasks.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """Проверка подключения к базе данных."""
    try:
        async with get_db_session() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def get_database_info() -> dict:
    """Получение информации о базе данных."""
    try:
        async with get_db_session() as session:
            # Получение информации о соединении
            connection_info = {
                "url": str(engine.url).replace(engine.url.password or "", "***"),
                "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else None,
                "checked_out": engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else None,
                "checked_in": engine.pool.checkedin() if hasattr(engine.pool, 'checkedin') else None,
            }
            
            # Проверка версии SQLite/PostgreSQL
            if "sqlite" in settings.DATABASE_URL:
                result = await session.execute("SELECT sqlite_version()")
                version = result.scalar()
                connection_info["database_version"] = f"SQLite {version}"
            else:
                result = await session.execute("SELECT version()")
                version = result.scalar()
                connection_info["database_version"] = version
            
            return connection_info
            
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": str(e)}


class DatabaseManager:
    """Менеджер для управления жизненным циклом базы данных."""
    
    def __init__(self):
        self.engine = engine
        self.session_maker = AsyncSessionLocal
        self._is_initialized = False
    
    async def initialize(self):
        """Инициализация базы данных."""
        if self._is_initialized:
            return
        
        await init_database()
        self._is_initialized = True
        logger.info("Database manager initialized")
    
    async def close(self):
        """Закрытие соединений с базой данных."""
        await self.engine.dispose()
        logger.info("Database connections closed")
    
    async def health_check(self) -> dict:
        """Проверка состояния базы данных."""
        return {
            "database_connected": await check_database_connection(),
            "database_info": await get_database_info(),
            "is_initialized": self._is_initialized,
        }
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager для транзакций."""
        async with self.session_maker() as session:
            async with session.begin():
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise


# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()