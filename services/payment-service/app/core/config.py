# -*- coding: utf-8 -*-
"""
Payment Service Configuration
Environment-based configuration management
"""

import os
from decimal import Decimal
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Payment service settings"""
    
    # Service info
    SERVICE_NAME: str = "payment-service"
    SERVICE_VERSION: str = "1.0.0"
    API_VERSION: str = "v1"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8003
    DEBUG: bool = False
    
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/payment_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False
    
    # Redis settings (for caching and events)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 10
    
    # RabbitMQ settings (for event messaging)
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_EXCHANGE: str = "repitbot_events"
    RABBITMQ_QUEUE_PREFIX: str = "payment_service"
    
    # Payment settings
    DEFAULT_PRICE_PER_LESSON: Decimal = Decimal("1000.00")  # Default price in currency
    CURRENCY: str = "RUB"
    ENABLE_NEGATIVE_BALANCE: bool = False
    MAX_BALANCE: int = 1000  # Maximum lessons balance
    
    # Financial precision
    DECIMAL_PLACES: int = 2
    MAX_DIGITS: int = 10
    
    # Security settings
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # External services
    USER_SERVICE_URL: str = "http://localhost:8001"
    LESSON_SERVICE_URL: str = "http://localhost:8002"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8006"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # CORS settings
    CORS_ORIGINS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Invoice settings
    INVOICE_NUMBER_PREFIX: str = "INV"
    INVOICE_NUMBER_LENGTH: int = 8
    
    # Event processing
    EVENT_PROCESSING_ENABLED: bool = True
    EVENT_PROCESSING_BATCH_SIZE: int = 10
    EVENT_PROCESSING_INTERVAL: int = 5  # seconds
    
    # Background tasks
    BACKGROUND_TASK_ENABLED: bool = True
    BALANCE_SYNC_INTERVAL: int = 300  # 5 minutes
    
    # Development settings
    ENABLE_DOCS: bool = True
    ENABLE_REDOC: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create settings instance
settings = Settings()


# Development override
if os.getenv("ENVIRONMENT") == "development":
    settings.DATABASE_URL = "sqlite+aiosqlite:///./payment_service.db"
    settings.DEBUG = True
    settings.DATABASE_ECHO = True


# Test override  
if os.getenv("ENVIRONMENT") == "test":
    settings.DATABASE_URL = "sqlite+aiosqlite:///./test_payment_service.db"
    settings.DEBUG = True
    settings.DATABASE_ECHO = False


# Production checks
if os.getenv("ENVIRONMENT") == "production":
    if settings.SECRET_KEY == "your-super-secret-key-change-this-in-production":
        raise ValueError("SECRET_KEY must be changed in production!")
    settings.DEBUG = False
    settings.ENABLE_DOCS = False
    settings.ENABLE_REDOC = False