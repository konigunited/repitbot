from functools import lru_cache
from pydantic import Field

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
shared_path = BASE_DIR / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from repitbot_shared.config import Settings as SharedSettings  # noqa: E402


class AuthServiceSettings(SharedSettings):
    """Configuration overrides specific to the auth service."""

    service_name: str = "auth-service"
    database_url: str = Field(
        default="postgresql+psycopg://repitbot:repitbot@postgres:5432/repitbot_auth",
        validation_alias="AUTH_SERVICE_DATABASE_URL",
        alias="AUTH_SERVICE_DATABASE_URL",
    )
    jwt_secret: str = Field(default="repitbot-secret", alias="AUTH_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="AUTH_JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, alias="AUTH_JWT_EXP_MINUTES")


@lru_cache
def get_settings() -> AuthServiceSettings:
    return AuthServiceSettings()
