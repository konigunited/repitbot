from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    api_gateway_url: str = Field(default="http://api-gateway:8080/api")
    log_level: str = Field(default="INFO")
    tutor_menu: list[str] = ["Students", "Homework", "Payments", "Schedule"]
    student_menu: list[str] = ["My lessons", "Homework", "Progress"]
    parent_menu: list[str] = ["Child status", "Balance"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()
