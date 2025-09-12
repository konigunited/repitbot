# -*- coding: utf-8 -*-
"""
Auth Service - Database Connection
Подключение к базе данных с поддержкой async/await
"""
import os
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from ..models.auth import Base

# Database configuration
DATABASE_URL = os.getenv(
    "AUTH_SERVICE_DATABASE_URL", 
    "sqlite+aiosqlite:///./auth_service.db"
)

# For SQLite - use StaticPool to handle threading issues
if "sqlite" in DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        echo=bool(os.getenv("DEBUG", False)),
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
else:
    # For PostgreSQL/MySQL
    engine = create_async_engine(
        DATABASE_URL,
        echo=bool(os.getenv("DEBUG", False)),
        pool_size=10,
        max_overflow=20
    )

# Async session factory
async_session_local = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения асинхронной сессии базы данных
    """
    async with async_session_local() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """
    Инициализация базы данных - создание всех таблиц
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """
    Закрытие соединения с базой данных
    """
    await engine.dispose()

async def check_db_connection() -> bool:
    """
    Проверка соединения с базой данных
    """
    try:
        async with async_session_local() as session:
            await session.execute("SELECT 1")
            return True
    except Exception:
        return False

# Health check function
async def get_db_health() -> dict:
    """
    Получение статуса здоровья базы данных
    """
    try:
        is_connected = await check_db_connection()
        return {
            "status": "healthy" if is_connected else "unhealthy",
            "database_url": DATABASE_URL.split("://")[0] + "://***",  # Hide credentials
            "connected": is_connected
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "connected": False
        }

# Context manager for database sessions
class DatabaseManager:
    """
    Контекстный менеджер для работы с базой данных
    """
    
    def __init__(self):
        self.session: AsyncSession = None
    
    async def __aenter__(self) -> AsyncSession:
        self.session = async_session_local()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()

# Migration utilities
async def run_migrations():
    """
    Запуск миграций базы данных
    """
    # В продакшене здесь будет использоваться Alembic
    await init_db()
    print("Auth Service database migrations completed successfully")

if __name__ == "__main__":
    # Test database connection
    async def test_connection():
        health = await get_db_health()
        print(f"Database health: {health}")
        
        if health["connected"]:
            print("✅ Auth Service database connection successful")
            await init_db()
            print("✅ Auth Service database tables created")
        else:
            print("❌ Auth Service database connection failed")
    
    asyncio.run(test_connection())