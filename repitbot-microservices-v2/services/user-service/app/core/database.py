from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Generator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings


Base = declarative_base()


@lru_cache
def _get_engine():
    settings = get_settings()
    return create_engine(settings.database_url, future=True)


@lru_cache
def _get_session_factory():
    return sessionmaker(bind=_get_engine(), autoflush=False, autocommit=False)


@contextmanager
def session_scope() -> Generator:
    """Provide a transactional scope around a series of operations."""

    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_migrations() -> None:
    """Apply the latest Alembic migrations."""

    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(alembic_cfg, "head")


def init_db() -> None:
    run_migrations()
