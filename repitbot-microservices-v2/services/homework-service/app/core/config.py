from functools import lru_cache
from pydantic import Field

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
shared_path = BASE_DIR / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from repitbot_shared.config import Settings as SharedSettings  # noqa: E402


class HomeworkServiceSettings(SharedSettings):
    """Configuration overrides specific to the homework service."""

    service_name: str = "homework-service"
    database_url: str = Field(
        default="postgresql+psycopg://repitbot:repitbot@postgres:5432/repitbot_homework",
        validation_alias="HOMEWORK_SERVICE_DATABASE_URL",
        alias="HOMEWORK_SERVICE_DATABASE_URL",
    )
    default_deadline_hours: int = 48


@lru_cache
def get_settings() -> HomeworkServiceSettings:
    return HomeworkServiceSettings()
