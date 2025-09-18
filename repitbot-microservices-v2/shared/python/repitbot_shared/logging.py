import logging
from typing import Optional

from .config import get_settings


def configure_logging(service_name: Optional[str] = None) -> logging.Logger:
    """Configure logging format for the current process."""

    settings = get_settings()
    logger_name = service_name or settings.service_name
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    return logging.getLogger(logger_name)
