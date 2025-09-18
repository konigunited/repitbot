from functools import lru_cache
from pydantic import Field

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
shared_path = BASE_DIR / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from repitbot_shared.config import Settings as SharedSettings  # noqa: E402


class UserServiceSettings(SharedSettings):
    """Configuration overrides specific to the user service."""

    service_name: str = "user-service"
    database_url: str = Field(
        default="postgresql+psycopg://repitbot:repitbot@postgres:5432/repitbot_user",
        validation_alias="USER_SERVICE_DATABASE_URL",
        alias="USER_SERVICE_DATABASE_URL",
    )
    default_access_code_length: int = 8


@lru_cache
def get_settings() -> UserServiceSettings:
    return UserServiceSettings()
