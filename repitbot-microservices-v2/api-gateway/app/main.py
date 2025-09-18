import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[3]
shared_path = BASE_DIR / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from repitbot_shared.logging import configure_logging  # noqa: E402

from .core.config import get_settings  # noqa: E402
from .routes.gateway import router as gateway_router  # noqa: E402
from .services.proxy import proxy_service  # noqa: E402

settings = get_settings()
logger = configure_logging(settings.service_name)

app = FastAPI(
    title="RepitBot API Gateway",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("API Gateway starting up")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("API Gateway shutting down")
    await proxy_service.close()


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": settings.service_name}


app.include_router(gateway_router, prefix=settings.api_prefix)
