# -*- coding: utf-8 -*-
"""
Homework Service - FastAPI микросервис для управления домашними заданиями.
Реализует создание, проверку, загрузку файлов и статистику по ДЗ.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config.settings import get_settings
from .database.connection import get_db, init_database
from .api.v1 import homework
from .events.homework_events import HomeworkEventPublisher
from .services.health_service import HealthService
from .services.file_service import FileService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager для FastAPI приложения."""
    try:
        # Инициализация базы данных
        logger.info("Initializing database connection...")
        await init_database()
        
        # Инициализация event publisher
        logger.info("Initializing event publisher...")
        event_publisher = HomeworkEventPublisher()
        await event_publisher.initialize()
        app.state.event_publisher = event_publisher
        
        # Инициализация file service
        logger.info("Initializing file service...")
        file_service = FileService()
        await file_service.initialize()
        app.state.file_service = file_service
        
        # Инициализация health service
        logger.info("Initializing health service...")
        health_service = HealthService()
        app.state.health_service = health_service
        
        logger.info("Homework Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Homework Service: {e}")
        raise
    finally:
        # Cleanup
        if hasattr(app.state, 'event_publisher'):
            await app.state.event_publisher.close()
        if hasattr(app.state, 'file_service'):
            await app.state.file_service.cleanup()
        logger.info("Homework Service shutdown complete")


# Создание FastAPI приложения
app = FastAPI(
    title="Homework Service",
    description="Микросервис для управления домашними заданиями и файлами",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files для загруженных файлов
app.mount("/static", StaticFiles(directory=settings.FILE_STORAGE_PATH), name="static")


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": str(asyncio.get_event_loop().time())
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": str(asyncio.get_event_loop().time())
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint для мониторинга состояния сервиса."""
    try:
        health_service = app.state.health_service
        health_status = await health_service.check_health()
        
        status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return JSONResponse(
            status_code=status_code,
            content=health_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": str(asyncio.get_event_loop().time())
            }
        )


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Endpoint для получения метрик сервиса."""
    try:
        health_service = app.state.health_service
        metrics = await health_service.get_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )


# API роутеры
app.include_router(
    homework.router,
    prefix="/api/v1",
    tags=["homework"]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint с информацией о сервисе."""
    return {
        "service": "Homework Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
            "homework": "/api/v1/homework",
            "files": "/api/v1/files"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )