from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Notification Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8006
    
    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "repitbot"
    POSTGRES_PASSWORD: str = "repitbot_password"
    POSTGRES_DB: str = "notification_service"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
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
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_API_URL: str = "https://api.telegram.org"
    
    # Email SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    FROM_EMAIL: Optional[str] = None
    
    # Push Notifications (FCM)
    FCM_SERVER_KEY: Optional[str] = None
    FCM_PROJECT_ID: Optional[str] = None
    
    # Template Settings
    TEMPLATE_DIR: str = "templates"
    DEFAULT_LANGUAGE: str = "ru"
    SUPPORTED_LANGUAGES: list = ["ru", "en"]
    
    # Notification Settings
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY_SECONDS: int = 60
    BATCH_SIZE: int = 100
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # External Services
    USER_SERVICE_URL: str = "http://user-service:8001"
    LESSON_SERVICE_URL: str = "http://lesson-service:8002"
    HOMEWORK_SERVICE_URL: str = "http://homework-service:8003"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8004"
    MATERIAL_SERVICE_URL: str = "http://material-service:8005"
    
    # JWT
    JWT_SECRET_KEY: str = "notification-service-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()