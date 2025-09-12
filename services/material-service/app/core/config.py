# -*- coding: utf-8 -*-
"""
Material Service Configuration
Environment-based configuration management
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Material service settings"""
    
    # Service info
    SERVICE_NAME: str = "material-service"
    SERVICE_VERSION: str = "1.0.0"
    API_VERSION: str = "v1"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8004
    DEBUG: bool = False
    
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/material_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False
    
    # Redis settings (for caching)
    REDIS_URL: str = "redis://localhost:6379/1"
    REDIS_MAX_CONNECTIONS: int = 10
    CACHE_TTL: int = 3600  # 1 hour
    
    # RabbitMQ settings (for event messaging)
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_EXCHANGE: str = "repitbot_events"
    RABBITMQ_QUEUE_PREFIX: str = "material_service"
    
    # File storage settings
    STORAGE_TYPE: str = "local"  # local, s3, minio
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: List[str] = [
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "rtf",
        "jpg", "jpeg", "png", "gif", "bmp", "svg",
        "mp3", "mp4", "avi", "mov", "wav",
        "zip", "rar"
    ]
    THUMBNAIL_SIZE: tuple = (200, 200)
    PREVIEW_SIZE: tuple = (800, 600)
    
    # S3/MinIO settings (if using S3-compatible storage)
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "materials"
    S3_REGION: str = "us-east-1"
    
    # Content settings
    DEFAULT_GRADE: int = 5
    MAX_TAGS_PER_MATERIAL: int = 10
    ENABLE_REVIEWS: bool = True
    ENABLE_RATINGS: bool = True
    MIN_RATING: int = 1
    MAX_RATING: int = 5
    
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
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Search settings
    SEARCH_MIN_QUERY_LENGTH: int = 2
    SEARCH_MAX_RESULTS: int = 1000
    ENABLE_FULL_TEXT_SEARCH: bool = True
    
    # File processing
    ENABLE_THUMBNAIL_GENERATION: bool = True
    ENABLE_PREVIEW_GENERATION: bool = True
    ENABLE_FILE_COMPRESSION: bool = True
    ENABLE_VIRUS_SCANNING: bool = False
    
    # Background tasks
    BACKGROUND_TASK_ENABLED: bool = True
    FILE_CLEANUP_INTERVAL: int = 3600  # 1 hour
    STATS_UPDATE_INTERVAL: int = 300   # 5 minutes
    
    # Event processing
    EVENT_PROCESSING_ENABLED: bool = True
    EVENT_PROCESSING_BATCH_SIZE: int = 10
    EVENT_PROCESSING_INTERVAL: int = 5  # seconds
    
    # Analytics
    ENABLE_ACCESS_LOGGING: bool = True
    ENABLE_DOWNLOAD_TRACKING: bool = True
    ENABLE_VIEW_TRACKING: bool = True
    
    # Development settings
    ENABLE_DOCS: bool = True
    ENABLE_REDOC: bool = True
    MOCK_EXTERNAL_SERVICES: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create settings instance
settings = Settings()


# Development override
if os.getenv("ENVIRONMENT") == "development":
    settings.DATABASE_URL = "sqlite+aiosqlite:///./material_service.db"
    settings.DEBUG = True
    settings.DATABASE_ECHO = True
    settings.UPLOAD_DIR = "./dev_uploads"
    settings.MOCK_EXTERNAL_SERVICES = True


# Test override  
if os.getenv("ENVIRONMENT") == "test":
    settings.DATABASE_URL = "sqlite+aiosqlite:///./test_material_service.db"
    settings.DEBUG = True
    settings.DATABASE_ECHO = False
    settings.UPLOAD_DIR = "./test_uploads"
    settings.MOCK_EXTERNAL_SERVICES = True


# Production checks
if os.getenv("ENVIRONMENT") == "production":
    if settings.SECRET_KEY == "your-super-secret-key-change-this-in-production":
        raise ValueError("SECRET_KEY must be changed in production!")
    settings.DEBUG = False
    settings.ENABLE_DOCS = False
    settings.ENABLE_REDOC = False
    settings.MOCK_EXTERNAL_SERVICES = False