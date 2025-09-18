from functools import lru_cache
from pydantic import Field

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
shared_path = BASE_DIR / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from repitbot_shared.config import Settings as SharedSettings  # noqa: E402


class PaymentServiceSettings(SharedSettings):
    """Configuration overrides specific to the payment service."""

    service_name: str = "payment-service"
    database_url: str = Field(
        default="postgresql+psycopg://repitbot:repitbot@postgres:5432/repitbot_payment",
        validation_alias="PAYMENT_SERVICE_DATABASE_URL",
        alias="PAYMENT_SERVICE_DATABASE_URL",
    )
    currency: str = Field(default="RUB", alias="PAYMENT_SERVICE_CURRENCY")


@lru_cache
def get_settings() -> PaymentServiceSettings:
    return PaymentServiceSettings()
