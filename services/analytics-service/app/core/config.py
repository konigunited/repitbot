from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Analytics Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8007
    
    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "repitbot"
    POSTGRES_PASSWORD: str = "repitbot_password"
    POSTGRES_DB: str = "analytics_service"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 1  # Используем другую БД для аналитики
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "repitbot"
    RABBITMQ_PASSWORD: str = "repitbot_password"
    RABBITMQ_VHOST: str = "/"
    
    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"
    
    # External Services URLs
    USER_SERVICE_URL: str = "http://user-service:8001"
    LESSON_SERVICE_URL: str = "http://lesson-service:8002"
    HOMEWORK_SERVICE_URL: str = "http://homework-service:8003"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8004"
    MATERIAL_SERVICE_URL: str = "http://material-service:8005"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8006"
    
    # Analytics Settings
    CACHE_EXPIRATION_SECONDS: int = 3600  # 1 час
    MAX_DATA_POINTS: int = 10000
    DEFAULT_CHART_WIDTH: int = 800
    DEFAULT_CHART_HEIGHT: int = 600
    
    # Report Settings
    REPORTS_DIR: str = "reports"
    MAX_REPORT_SIZE_MB: int = 50
    REPORT_CLEANUP_DAYS: int = 30
    
    # Chart Settings
    CHART_THEME: str = "plotly_white"
    CHART_COLOR_PALETTE: list = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]
    
    # Performance Settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    ASYNC_BATCH_SIZE: int = 1000
    
    # JWT
    JWT_SECRET_KEY: str = "analytics-service-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()