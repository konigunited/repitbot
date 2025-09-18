import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[3]
shared_path = BASE_DIR / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from repitbot_shared.logging import configure_logging  # noqa: E402

from .api.v1.routes import router  # noqa: E402
from .core.config import get_settings  # noqa: E402
from .core.database import init_db  # noqa: E402

settings = get_settings()
logger = configure_logging(settings.service_name)

app = FastAPI(
    title="RepitBot Notification Service",
    version="1.0.0",
    openapi_url=f"{settings.api_prefix}/notifications/openapi.json",
    docs_url=f"{settings.api_prefix}/notifications/docs" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Starting notification-service")
    init_db()


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "healthy", "service": settings.service_name}


app.include_router(router, prefix=settings.api_prefix)
