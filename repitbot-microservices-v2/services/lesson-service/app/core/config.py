from functools import lru_cache
from pydantic import Field

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
shared_path = BASE_DIR / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from repitbot_shared.config import Settings as SharedSettings  # noqa: E402


class LessonServiceSettings(SharedSettings):
    """Configuration overrides specific to the lesson service."""

    service_name: str = "lesson-service"
    database_url: str = Field(
        default="postgresql+psycopg://repitbot:repitbot@postgres:5432/repitbot_lesson",
        validation_alias="LESSON_SERVICE_DATABASE_URL",
        alias="LESSON_SERVICE_DATABASE_URL",
    )
    default_duration_minutes: int = 60


@lru_cache
def get_settings() -> LessonServiceSettings:
    return LessonServiceSettings()
