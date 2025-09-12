# -*- coding: utf-8 -*-
"""
Base configuration settings for RepitBot microservices.
Provides common configuration patterns and environment variable handling.
"""
import os
import secrets
from typing import Any, Dict, List, Optional, Union
from functools import lru_cache

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Base settings class for all microservices."""
    
    # Service identification
    service_name: str = Field(description="Name of the microservice")
    service_version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Environment (dev/staging/prod)")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    workers: int = Field(default=1, description="Number of worker processes")
    
    # Security
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    cors_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_methods: List[str] = Field(default=["*"], description="CORS allowed methods")
    cors_headers: List[str] = Field(default=["*"], description="CORS allowed headers")
    
    # Database
    database_url: str = Field(description="Database connection URL")
    database_echo: bool = Field(default=False, description="Echo SQL queries")
    database_pool_size: int = Field(default=5, description="Database pool size")
    database_max_overflow: int = Field(default=10, description="Database pool max overflow")
    database_pool_timeout: int = Field(default=30, description="Database pool timeout")
    database_pool_recycle: int = Field(default=3600, description="Database pool recycle time")
    
    # Redis (for caching and message broker)
    redis_url: Optional[str] = Field(None, description="Redis connection URL")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(None, description="Redis password")
    redis_ssl: bool = Field(default=False, description="Use SSL for Redis")
    
    # Message Broker (RabbitMQ/Kafka)
    message_broker_url: Optional[str] = Field(None, description="Message broker URL")
    message_broker_type: str = Field(default="redis", description="Message broker type (redis/rabbitmq/kafka)")
    message_exchange: str = Field(default="repitbot", description="Message exchange name")
    message_queue_prefix: str = Field(default="repitbot", description="Queue name prefix")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json/text)")
    log_file: Optional[str] = Field(None, description="Log file path")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    
    # API Documentation
    docs_url: str = Field(default="/docs", description="Swagger UI URL")
    redoc_url: str = Field(default="/redoc", description="ReDoc URL")
    openapi_url: str = Field(default="/openapi.json", description="OpenAPI schema URL")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per minute")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # Caching
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    cache_prefix: str = Field(default="repitbot", description="Cache key prefix")
    
    # External Services
    telegram_bot_token: Optional[str] = Field(None, description="Telegram bot token")
    telegram_webhook_url: Optional[str] = Field(None, description="Telegram webhook URL")
    
    # Service Discovery
    consul_host: Optional[str] = Field(None, description="Consul host")
    consul_port: int = Field(default=8500, description="Consul port")
    consul_token: Optional[str] = Field(None, description="Consul token")
    
    # JWT Settings
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expire_minutes: int = Field(default=30, description="JWT expiration time in minutes")
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed_envs = ['development', 'staging', 'production', 'testing']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of: {allowed_envs}')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {allowed_levels}')
        return v.upper()
    
    @validator('log_format')
    def validate_log_format(cls, v):
        """Validate log format."""
        allowed_formats = ['json', 'text']
        if v not in allowed_formats:
            raise ValueError(f'Log format must be one of: {allowed_formats}')
        return v
    
    @validator('message_broker_type')
    def validate_message_broker_type(cls, v):
        """Validate message broker type."""
        allowed_types = ['redis', 'rabbitmq', 'kafka']
        if v not in allowed_types:
            raise ValueError(f'Message broker type must be one of: {allowed_types}')
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == 'development'
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == 'production'
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == 'testing'
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration dictionary."""
        return {
            'url': self.database_url,
            'echo': self.database_echo,
            'pool_size': self.database_pool_size,
            'max_overflow': self.database_max_overflow,
            'pool_timeout': self.database_pool_timeout,
            'pool_recycle': self.database_pool_recycle,
            'pool_pre_ping': True,
            'enable_logging': self.debug,
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration dictionary."""
        return {
            'url': self.redis_url,
            'db': self.redis_db,
            'password': self.redis_password,
            'ssl': self.redis_ssl,
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration dictionary."""
        return {
            'allow_origins': self.cors_origins,
            'allow_credentials': self.cors_credentials,
            'allow_methods': self.cors_methods,
            'allow_headers': self.cors_headers,
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class DevelopmentSettings(BaseServiceSettings):
    """Development environment settings."""
    
    environment: str = "development"
    debug: bool = True
    database_echo: bool = True
    log_level: str = "DEBUG"


class ProductionSettings(BaseServiceSettings):
    """Production environment settings."""
    
    environment: str = "production"
    debug: bool = False
    database_echo: bool = False
    log_level: str = "INFO"
    workers: int = 4


class TestingSettings(BaseServiceSettings):
    """Testing environment settings."""
    
    environment: str = "testing"
    debug: bool = True
    database_url: str = "sqlite:///./test.db"
    redis_url: str = "redis://localhost:6379/1"
    log_level: str = "DEBUG"


# Factory function to get settings based on environment
def get_settings_class(environment: Optional[str] = None):
    """Get settings class based on environment."""
    env = environment or os.getenv("ENVIRONMENT", "development").lower()
    
    settings_map = {
        "development": DevelopmentSettings,
        "production": ProductionSettings,  
        "testing": TestingSettings,
    }
    
    return settings_map.get(env, DevelopmentSettings)


@lru_cache()
def get_settings() -> BaseServiceSettings:
    """Get cached settings instance."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    settings_class = get_settings_class(environment)
    return settings_class()


# Service-specific settings templates
class UserServiceSettings(BaseServiceSettings):
    """User service specific settings."""
    
    service_name: str = "user-service"
    port: int = 8001


class AuthServiceSettings(BaseServiceSettings):
    """Auth service specific settings."""
    
    service_name: str = "auth-service"
    port: int = 8002
    
    # JWT specific settings
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_refresh_expire_days: int = Field(default=7, description="JWT refresh token expiration in days")
    password_min_length: int = Field(default=8, description="Minimum password length")
    password_require_uppercase: bool = Field(default=True, description="Require uppercase in password")
    password_require_lowercase: bool = Field(default=True, description="Require lowercase in password")
    password_require_digits: bool = Field(default=True, description="Require digits in password")
    password_require_special: bool = Field(default=True, description="Require special characters in password")


class LessonServiceSettings(BaseServiceSettings):
    """Lesson service specific settings."""
    
    service_name: str = "lesson-service"
    port: int = 8003
    
    # Lesson specific settings
    default_lesson_duration: int = Field(default=60, description="Default lesson duration in minutes")
    reschedule_limit_hours: int = Field(default=24, description="Minimum hours before lesson to reschedule")
    auto_cancel_hours: int = Field(default=2, description="Auto-cancel lesson after hours of no-show")


class HomeworkServiceSettings(BaseServiceSettings):
    """Homework service specific settings."""
    
    service_name: str = "homework-service"
    port: int = 8004
    
    # Homework specific settings
    max_file_size_mb: int = Field(default=10, description="Maximum file size for homework in MB")
    supported_file_types: List[str] = Field(
        default=["jpg", "jpeg", "png", "pdf", "doc", "docx"],
        description="Supported file types for homework"
    )
    default_homework_deadline_days: int = Field(default=7, description="Default homework deadline in days")


class PaymentServiceSettings(BaseServiceSettings):
    """Payment service specific settings."""
    
    service_name: str = "payment-service" 
    port: int = 8005
    
    # Payment specific settings
    currency: str = Field(default="RUB", description="Default currency")
    payment_methods: List[str] = Field(
        default=["cash", "card", "transfer"],
        description="Supported payment methods"
    )


class NotificationServiceSettings(BaseServiceSettings):
    """Notification service specific settings."""
    
    service_name: str = "notification-service"
    port: int = 8006
    
    # Notification specific settings
    max_retries: int = Field(default=3, description="Maximum notification retry attempts")
    retry_delay_seconds: int = Field(default=60, description="Delay between retries in seconds")
    batch_size: int = Field(default=100, description="Notification batch size")


class MaterialServiceSettings(BaseServiceSettings):
    """Material service specific settings."""
    
    service_name: str = "material-service"
    port: int = 8007
    
    # Material specific settings
    max_materials_per_grade: int = Field(default=1000, description="Maximum materials per grade")
    material_cache_ttl: int = Field(default=3600, description="Material cache TTL in seconds")


class AnalyticsServiceSettings(BaseServiceSettings):
    """Analytics service specific settings."""
    
    service_name: str = "analytics-service"
    port: int = 8008
    
    # Analytics specific settings
    data_retention_days: int = Field(default=365, description="Data retention period in days")
    batch_processing_interval: int = Field(default=3600, description="Batch processing interval in seconds")


class AchievementServiceSettings(BaseServiceSettings):
    """Achievement service specific settings."""
    
    service_name: str = "achievement-service"
    port: int = 8009
    
    # Achievement specific settings
    points_per_lesson: int = Field(default=10, description="Points awarded per lesson")
    points_per_homework: int = Field(default=5, description="Points awarded per homework")
    streak_multiplier: float = Field(default=1.5, description="Points multiplier for streaks")


class SchedulerServiceSettings(BaseServiceSettings):
    """Scheduler service specific settings."""
    
    service_name: str = "scheduler-service"
    port: int = 8010
    
    # Scheduler specific settings
    job_check_interval: int = Field(default=60, description="Job check interval in seconds")
    max_concurrent_jobs: int = Field(default=10, description="Maximum concurrent jobs")
    job_timeout_minutes: int = Field(default=30, description="Job timeout in minutes")


# TODO: Add more service-specific settings as services are developed
# TODO: Add configuration validation and migration utilities
# TODO: Add environment-specific overrides