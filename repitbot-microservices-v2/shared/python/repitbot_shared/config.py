from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Shared application settings for RepitBot microservices."""

    service_name: str = "service"
    debug: bool = False
    environment: str = "development"
    database_url: str = "sqlite:///./data/service.db"
    event_bus_url: str = "amqp://guest:guest@rabbitmq:5672/"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "repitbot-secret"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
