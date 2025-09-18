from functools import lru_cache
from pydantic import Field

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
shared_path = BASE_DIR / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from repitbot_shared.config import Settings as SharedSettings  # noqa: E402


class NotificationServiceSettings(SharedSettings):
    """Configuration overrides specific to the notification service."""

    service_name: str = "notification-service"
    database_url: str = Field(
        default="postgresql+psycopg://repitbot:repitbot@postgres:5432/repitbot_notification",
        validation_alias="NOTIFICATION_SERVICE_DATABASE_URL",
        alias="NOTIFICATION_SERVICE_DATABASE_URL",
    )
    provider_api_key: str = Field(default="dev-key", alias="NOTIFICATION_PROVIDER_API_KEY")


@lru_cache
def get_settings() -> NotificationServiceSettings:
    return NotificationServiceSettings()
