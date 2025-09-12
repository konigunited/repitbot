# -*- coding: utf-8 -*-
"""
Database utilities for RepitBot microservices.
Provides common database patterns, connection management, and utilities.
"""
import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Dict, Generator, List, Optional, Type, TypeVar, Union
from urllib.parse import urlparse

from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy.sql import text

from ..models.base import Base

logger = logging.getLogger(__name__)

# Type variables
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class DatabaseConfig:
    """Database configuration settings."""
    
    def __init__(
        self,
        url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        enable_logging: bool = True
    ):
        self.url = url
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.enable_logging = enable_logging
        
        # Parse database type from URL
        parsed = urlparse(url)
        self.db_type = parsed.scheme.split('+')[0]
        self.is_sqlite = self.db_type == 'sqlite'
        self.is_async = 'asyncpg' in parsed.scheme or 'aiosqlite' in parsed.scheme


class DatabaseManager:
    """Database manager with connection pooling and session management."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup database query logging."""
        if self.config.enable_logging:
            logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    
    @property
    def engine(self):
        """Get synchronous database engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    @property
    def async_engine(self):
        """Get asynchronous database engine."""
        if self._async_engine is None:
            self._async_engine = self._create_async_engine()
        return self._async_engine
    
    @property
    def session_factory(self):
        """Get synchronous session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
        return self._session_factory
    
    @property
    def async_session_factory(self):
        """Get asynchronous session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._async_session_factory
    
    def _create_engine(self):
        """Create synchronous database engine."""
        engine_kwargs = {
            'echo': self.config.echo,
        }
        
        # Add pooling configuration for non-SQLite databases
        if not self.config.is_sqlite:
            engine_kwargs.update({
                'poolclass': QueuePool,
                'pool_size': self.config.pool_size,
                'max_overflow': self.config.max_overflow,
                'pool_timeout': self.config.pool_timeout,
                'pool_recycle': self.config.pool_recycle,
                'pool_pre_ping': self.config.pool_pre_ping,
            })
        
        engine = create_engine(self.config.url, **engine_kwargs)
        
        # Add event listeners
        self._add_engine_listeners(engine)
        
        return engine
    
    def _create_async_engine(self):
        """Create asynchronous database engine."""
        # Convert sync URL to async URL if needed
        async_url = self.config.url
        if not self.config.is_async:
            if self.config.is_sqlite:
                async_url = self.config.url.replace('sqlite://', 'sqlite+aiosqlite://')
            elif 'postgresql' in self.config.url:
                async_url = self.config.url.replace('postgresql://', 'postgresql+asyncpg://')
        
        engine_kwargs = {
            'echo': self.config.echo,
        }
        
        # Add pooling configuration for non-SQLite databases
        if not self.config.is_sqlite:
            engine_kwargs.update({
                'pool_size': self.config.pool_size,
                'max_overflow': self.config.max_overflow,
                'pool_timeout': self.config.pool_timeout,
                'pool_recycle': self.config.pool_recycle,
                'pool_pre_ping': self.config.pool_pre_ping,
            })
        
        return create_async_engine(async_url, **engine_kwargs)
    
    def _add_engine_listeners(self, engine):
        """Add event listeners for connection management."""
        
        @event.listens_for(engine, "connect")
        def do_connect(dbapi_connection, connection_record):
            logger.debug("Database connection established")
        
        @event.listens_for(engine, "checkout")
        def do_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(engine, "checkin")
        def do_checkin(dbapi_connection, connection_record):
            logger.debug("Connection returned to pool")
        
        @event.listens_for(engine, "invalidate")
        def do_invalidate(dbapi_connection, connection_record, exception):
            logger.warning(f"Connection invalidated: {exception}")
    
    @contextmanager
    def get_db_session(self) -> Generator[Session, None, None]:
        """Get database session context manager."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_db_session(self) -> AsyncSession:
        """Get async database session context manager."""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Async database session error: {e}")
                raise
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    async def create_tables_async(self):
        """Create all database tables asynchronously."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully (async)")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create tables (async): {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    async def drop_tables_async(self):
        """Drop all database tables asynchronously."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully (async)")
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop tables (async): {e}")
            raise
    
    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self.get_db_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def async_health_check(self) -> bool:
        """Check database connectivity asynchronously."""
        try:
            async with self.get_async_db_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Async database health check failed: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get database connection information."""
        return {
            "database_type": self.config.db_type,
            "is_sqlite": self.config.is_sqlite,
            "pool_size": self.config.pool_size if not self.config.is_sqlite else "N/A",
            "max_overflow": self.config.max_overflow if not self.config.is_sqlite else "N/A",
            "echo": self.config.echo,
        }
    
    def close(self):
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database engine disposed")
        
        if self._async_engine:
            asyncio.create_task(self._async_engine.aclose())
            logger.info("Async database engine disposed")


class Repository:
    """Base repository pattern implementation."""
    
    def __init__(self, session: Session, model_class: Type[ModelType]):
        self.session = session
        self.model_class = model_class
    
    def get(self, id: Any) -> Optional[ModelType]:
        """Get entity by ID."""
        return self.session.query(self.model_class).filter(
            self.model_class.id == id
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all entities with pagination."""
        return self.session.query(self.model_class).offset(skip).limit(limit).all()
    
    def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create new entity."""
        obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in
        db_obj = self.model_class(**obj_data)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj
    
    def update(self, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """Update existing entity."""
        obj_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in
        for field, value in obj_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj
    
    def delete(self, id: Any) -> bool:
        """Delete entity by ID."""
        obj = self.get(id)
        if obj:
            self.session.delete(obj)
            self.session.commit()
            return True
        return False
    
    def count(self) -> int:
        """Count total entities."""
        return self.session.query(self.model_class).count()


class AsyncRepository:
    """Async repository pattern implementation."""
    
    def __init__(self, session: AsyncSession, model_class: Type[ModelType]):
        self.session = session
        self.model_class = model_class
    
    async def get(self, id: Any) -> Optional[ModelType]:
        """Get entity by ID."""
        result = await self.session.get(self.model_class, id)
        return result
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all entities with pagination."""
        from sqlalchemy import select
        stmt = select(self.model_class).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create new entity."""
        obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in
        db_obj = self.model_class(**obj_data)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def update(self, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """Update existing entity."""
        obj_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in
        for field, value in obj_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: Any) -> bool:
        """Delete entity by ID."""
        obj = await self.get(id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()
            return True
        return False
    
    async def count(self) -> int:
        """Count total entities."""
        from sqlalchemy import select, func
        stmt = select(func.count(self.model_class.id))
        result = await self.session.execute(stmt)
        return result.scalar()


# Singleton database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        raise RuntimeError("Database manager not initialized. Call init_database() first.")
    return _db_manager

def init_database(config: DatabaseConfig) -> DatabaseManager:
    """Initialize global database manager."""
    global _db_manager
    _db_manager = DatabaseManager(config)
    return _db_manager

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    db_manager = get_database_manager()
    with db_manager.get_db_session() as session:
        yield session

async def get_async_db() -> AsyncSession:
    """FastAPI dependency for async database session.""" 
    db_manager = get_database_manager()
    async with db_manager.get_async_db_session() as session:
        yield session


# TODO: Add more database utilities:
# - Migration utilities
# - Database backup utilities
# - Connection monitoring
# - Query performance tracking
# - Distributed transaction support