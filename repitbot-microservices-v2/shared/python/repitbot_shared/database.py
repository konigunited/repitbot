from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings


Base = declarative_base()
_engine_cache = None
_SessionLocal = None


def get_engine():
    """Create (or reuse) synchronous SQLAlchemy engine per service."""

    global _engine_cache
    if _engine_cache is None:
        settings = get_settings()
        _engine_cache = create_engine(settings.database_url, future=True)
    return _engine_cache


def get_session_factory():
    """Return a configured session factory."""

    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


@contextmanager
def session_scope() -> Generator:
    """Provide transactional scope for SQLAlchemy operations."""

    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database():
    """Create database tables based on SQLAlchemy metadata."""

    Base.metadata.create_all(bind=get_engine())
