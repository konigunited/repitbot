# -*- coding: utf-8 -*-
"""
API Gateway Configuration
Конфигурация для API Gateway
"""
from pydantic_settings import BaseSettings
from typing import Dict, List
import os


class Settings(BaseSettings):
    """Настройки API Gateway"""
    
    # Основные настройки
    APP_NAME: str = "API Gateway"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Настройки сервера
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # JWT настройки
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Redis для кеширования и rate limiting
    REDIS_URL: str = "redis://redis:6379/6"
    
    # URLs микросервисов
    USER_SERVICE_URL: str = "http://user-service:8001"
    LESSON_SERVICE_URL: str = "http://lesson-service:8002"
    HOMEWORK_SERVICE_URL: str = "http://homework-service:8003"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8004"
    MATERIAL_SERVICE_URL: str = "http://material-service:8005"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8006"
    ANALYTICS_SERVICE_URL: str = "http://analytics-service:8007"
    STUDENT_SERVICE_URL: str = "http://student-service:8008"
    
    # Карта маршрутизации сервисов
    SERVICE_ROUTES: Dict[str, str] = {
        "/api/v1/auth": "USER_SERVICE_URL",
        "/api/v1/users": "USER_SERVICE_URL",
        "/api/v1/lessons": "LESSON_SERVICE_URL",
        "/api/v1/homework": "HOMEWORK_SERVICE_URL",
        "/api/v1/payments": "PAYMENT_SERVICE_URL",
        "/api/v1/materials": "MATERIAL_SERVICE_URL",
        "/api/v1/notifications": "NOTIFICATION_SERVICE_URL",
        "/api/v1/analytics": "ANALYTICS_SERVICE_URL",
        "/api/v1/students": "STUDENT_SERVICE_URL",
        "/api/v1/achievements": "STUDENT_SERVICE_URL",
        "/api/v1/progress": "STUDENT_SERVICE_URL"
    }
    
    # Настройки CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React frontend
        "http://localhost:3001",  # Admin frontend
        "https://repitbot.com",   # Production frontend
    ]
    
    # Rate limiting настройки
    RATE_LIMIT_REQUESTS: int = 100  # Запросов на пользователя
    RATE_LIMIT_WINDOW: int = 60     # Окно в секундах
    RATE_LIMIT_BURST: int = 20      # Всплеск запросов
    
    # Circuit breaker настройки
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5    # Порог ошибок
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60    # Время восстановления
    CIRCUIT_BREAKER_EXPECTED_EXCEPTION: tuple = (Exception,)
    
    # Timeout настройки
    SERVICE_TIMEOUT: int = 30       # Таймаут запросов к сервисам
    GATEWAY_TIMEOUT: int = 60       # Общий таймаут Gateway
    
    # Retry настройки
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    RETRY_BACKOFF: float = 2.0
    
    # Health check настройки
    HEALTH_CHECK_INTERVAL: int = 30  # Интервал проверки сервисов
    HEALTH_CHECK_TIMEOUT: int = 5    # Таймаут проверки
    
    # Load balancing настройки
    LOAD_BALANCING_STRATEGY: str = "round_robin"  # round_robin, least_connections, random
    SERVICE_INSTANCES: Dict[str, List[str]] = {
        # Можно добавить несколько инстансов каждого сервиса
        "user-service": ["http://user-service:8001"],
        "lesson-service": ["http://lesson-service:8002"],
        "homework-service": ["http://homework-service:8003"],
        "payment-service": ["http://payment-service:8004"],
        "material-service": ["http://material-service:8005"],
        "notification-service": ["http://notification-service:8006"],
        "analytics-service": ["http://analytics-service:8007"],
        "student-service": ["http://student-service:8008"]
    }
    
    # Настройки безопасности
    TRUSTED_HOSTS: List[str] = ["*"]  # В продакшене указать конкретные хосты
    SECURE_HEADERS: bool = True
    
    # Monitoring настройки
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    ENABLE_ACCESS_LOG: bool = True
    ENABLE_CORRELATION_ID: bool = True
    
    # Feature flags
    ENABLE_AUTHENTICATION: bool = True
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_CIRCUIT_BREAKER: bool = True
    ENABLE_REQUEST_CACHING: bool = True
    ENABLE_RESPONSE_COMPRESSION: bool = True
    
    # Кеширование
    CACHE_TTL_DEFAULT: int = 300     # 5 минут
    CACHE_TTL_USERS: int = 600       # 10 минут
    CACHE_TTL_LESSONS: int = 1800    # 30 минут
    CACHE_TTL_MATERIALS: int = 3600  # 1 час
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_service_url(self, service_name: str) -> str:
        """Получение URL сервиса"""
        return getattr(self, f"{service_name.upper().replace('-', '_')}_URL", "")
    
    def get_service_instances(self, service_name: str) -> List[str]:
        """Получение списка инстансов сервиса"""
        return self.SERVICE_INSTANCES.get(service_name, [])


# Глобальный экземпляр настроек
settings = Settings()