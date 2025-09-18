from functools import lru_cache
from typing import Dict

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
shared_path = BASE_DIR / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from pydantic import Field
from repitbot_shared.config import Settings as SharedSettings  # noqa: E402


class GatewaySettings(SharedSettings):
    service_name: str = "api-gateway"
    api_prefix: str = "/api"
    upstream_services: Dict[str, str] = Field(
        default_factory=lambda: {
            "auth": "http://auth-service:8000/api/v1",
            "users": "http://user-service:8001/api/v1",
            "lessons": "http://lesson-service:8002/api/v1",
            "homework": "http://homework-service:8003/api/v1",
            "payments": "http://payment-service:8004/api/v1",
            "notifications": "http://notification-service:8005/api/v1",
        }
    )
    request_timeout: float = 8.0


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()
