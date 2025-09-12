# -*- coding: utf-8 -*-
"""
Конфигурация для Lesson Service.
Управляет настройками подключения к БД, RabbitMQ, и другими параметрами.
"""

import os
from functools import lru_cache
from typing import List
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Основные настройки приложения
    APP_NAME: str = "Lesson Service"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    
    # База данных
    DATABASE_URL: str = "sqlite:///./lessons.db"
    DATABASE_ECHO: bool = False
    
    # RabbitMQ для событий
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    EVENT_EXCHANGE_NAME: str = "repitbot_events"
    LESSON_EVENT_ROUTING_KEY: str = "lesson"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # JWT Secret для аутентификации (shared с User Service)
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # External services
    USER_SERVICE_URL: str = "http://localhost:8001"
    HOMEWORK_SERVICE_URL: str = "http://localhost:8003"
    
    # File storage
    FILE_STORAGE_PATH: str = "./storage/lessons"
    MAX_FILE_SIZE_MB: int = 10
    
    # Scheduler settings
    SCHEDULER_ENABLED: bool = True
    REMINDER_HOURS_BEFORE: int = 24
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Health check
    HEALTH_CHECK_TIMEOUT: int = 5
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Получить настройки приложения (с кешированием)."""
    return Settings()