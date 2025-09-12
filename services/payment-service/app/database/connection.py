# -*- coding: utf-8 -*-
"""
Payment Service Database Connection
Async SQLAlchemy connection and session management
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from ..core.config import settings
from ..models.payment import Base

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    poolclass=NullPool if "sqlite" in settings.DATABASE_URL else None,
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db() -> None:
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session
    Dependency for FastAPI routes
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """
    Get database session for services
    Use this in service classes
    """
    return AsyncSessionLocal()


class DatabaseManager:
    """Database connection manager for service classes"""
    
    def __init__(self):
        self.engine = engine
        self.session_maker = AsyncSessionLocal
    
    async def get_session(self) -> AsyncSession:
        """Get new database session"""
        return self.session_maker()
    
    async def close_session(self, session: AsyncSession) -> None:
        """Close database session"""
        await session.close()
    
    async def execute_in_transaction(self, func, *args, **kwargs):
        """Execute function in database transaction"""
        async with self.session_maker() as session:
            try:
                result = await func(session, *args, **kwargs)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"Transaction failed: {e}")
                raise
    
    async def health_check(self) -> bool:
        """Check database connection health"""
        try:
            async with self.session_maker() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()