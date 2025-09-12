# -*- coding: utf-8 -*-
"""
Shared utilities package for RepitBot microservices.

This package provides common utilities used across all services including:
- Database utilities and connection management
- Common helper functions
- Validation utilities
- Serialization helpers
"""

from .database import (
    DatabaseConfig,
    DatabaseManager,
    Repository,
    AsyncRepository,
    get_database_manager,
    init_database,
    get_db,
    get_async_db,
)

__all__ = [
    # Database utilities
    "DatabaseConfig",
    "DatabaseManager", 
    "Repository",
    "AsyncRepository",
    "get_database_manager",
    "init_database", 
    "get_db",
    "get_async_db",
]