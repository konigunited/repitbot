# -*- coding: utf-8 -*-
"""
Student Service Configuration
Конфигурация для микросервиса студентов
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки сервиса
    APP_NAME: str = "Student Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Настройки сервера
    HOST: str = "0.0.0.0"
    PORT: int = 8008
    
    # База данных
    DATABASE_URL: str = "postgresql+asyncpg://repitbot:repitbot_password@postgres:5432/student_service"
    
    # RabbitMQ для событий
    RABBITMQ_URL: str = "amqp://repitbot:repitbot_password@rabbitmq:5672/"
    
    # Redis для кеширования
    REDIS_URL: str = "redis://redis:6379/5"
    
    # JWT настройки
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # URLs других сервисов
    USER_SERVICE_URL: str = "http://user-service:8001"
    LESSON_SERVICE_URL: str = "http://lesson-service:8002"
    HOMEWORK_SERVICE_URL: str = "http://homework-service:8003"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8004"
    MATERIAL_SERVICE_URL: str = "http://material-service:8005"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8006"
    ANALYTICS_SERVICE_URL: str = "http://analytics-service:8007"
    
    # Настройки геймификации
    DEFAULT_LEVEL_XP_THRESHOLD: int = 1000  # XP для первого уровня
    XP_MULTIPLIER: float = 1.5  # Множитель для следующих уровней
    MAX_LEVEL: int = 100
    
    # Очки за действия
    XP_LESSON_COMPLETED: int = 100
    XP_HOMEWORK_SUBMITTED: int = 50
    XP_HOMEWORK_PERFECT: int = 150  # Бонус за отличную работу
    XP_MATERIAL_STUDIED: int = 25
    XP_STREAK_BONUS: int = 20  # Бонус за регулярность
    XP_ACHIEVEMENT_BONUS: int = 200
    
    # Настройки достижений
    STREAK_REQUIRED_DAYS: int = 7  # Дней для достижения "стрик"
    PERFECTIONIST_REQUIRED: int = 10  # Идеальных работ для "перфекциониста"
    ACTIVE_LEARNER_HOURS: int = 50  # Часов обучения для "активного ученика"
    
    # Настройки рекомендаций
    RECOMMENDATION_CACHE_TTL: int = 3600  # 1 час
    MAX_RECOMMENDATIONS: int = 10
    ML_MODEL_UPDATE_INTERVAL: int = 86400  # 24 часа
    
    # Настройки событий
    EVENT_PROCESSING_ENABLED: bool = True
    EVENT_RETRY_ATTEMPTS: int = 3
    EVENT_RETRY_DELAY: int = 300  # секунд
    
    # Настройки производительности
    CONNECTION_POOL_SIZE: int = 10
    CONNECTION_POOL_MAX_OVERFLOW: int = 20
    QUERY_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Глобальный экземпляр настроек
settings = Settings()