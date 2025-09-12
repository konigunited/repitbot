# -*- coding: utf-8 -*-
"""
Конфигурация для Homework Service.
Управляет настройками подключения к БД, RabbitMQ, файлового хранилища и другими параметрами.
"""

import os
from functools import lru_cache
from typing import List
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Основные настройки приложения
    APP_NAME: str = "Homework Service"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8003
    
    # База данных
    DATABASE_URL: str = "sqlite:///./homework.db"
    DATABASE_ECHO: bool = False
    
    # RabbitMQ для событий
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    EVENT_EXCHANGE_NAME: str = "repitbot_events"
    HOMEWORK_EVENT_ROUTING_KEY: str = "homework"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # JWT Secret для аутентификации (shared с User Service)
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # External services
    USER_SERVICE_URL: str = "http://localhost:8001"
    LESSON_SERVICE_URL: str = "http://localhost:8002"
    
    # File storage
    FILE_STORAGE_PATH: str = "./storage/homework"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: List[str] = [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain", "video/mp4", "audio/mpeg"
    ]
    
    # Image processing
    MAX_IMAGE_WIDTH: int = 4096
    MAX_IMAGE_HEIGHT: int = 4096
    THUMBNAIL_SIZE: int = 200
    COMPRESSED_MAX_SIZE: int = 1920
    JPEG_QUALITY: int = 80
    
    # Homework settings
    DEFAULT_DEADLINE_HOURS: int = 168  # 7 дней
    MAX_ATTEMPTS: int = 3
    AUTO_CHECK_ENABLED: bool = False
    
    # Notifications
    REMINDER_HOURS_BEFORE_DEADLINE: int = 24
    OVERDUE_CHECK_INTERVAL_HOURS: int = 6
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Health check
    HEALTH_CHECK_TIMEOUT: int = 5
    
    # Rate limiting
    UPLOAD_RATE_LIMIT: str = "10/minute"
    API_RATE_LIMIT: str = "100/minute"
    
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
    
    @validator("FILE_STORAGE_PATH")
    def validate_storage_path(cls, v):
        if not v:
            raise ValueError("FILE_STORAGE_PATH cannot be empty")
        # Создание директории если не существует
        os.makedirs(v, exist_ok=True)
        return v
    
    @validator("MAX_FILE_SIZE_MB")
    def validate_max_file_size(cls, v):
        if v <= 0 or v > 1000:
            raise ValueError("MAX_FILE_SIZE_MB must be between 1 and 1000")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Получить настройки приложения (с кешированием)."""
    return Settings()