# -*- coding: utf-8 -*-
"""
User Service - FastAPI Application
Микросервис управления пользователями
"""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import time
import os

from .database.connection import init_db, close_db
from .api.v1.users import router as users_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events для FastAPI приложения"""
    # Startup
    logger.info("Starting User Service...")
    await init_db()
    logger.info("Database initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down User Service...")
    await close_db()
    logger.info("Database connections closed")

# Создание FastAPI приложения
app = FastAPI(
    title="User Service",
    description="Микросервис управления пользователями для RepitBot",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React frontend
        "http://localhost:8080",  # API Gateway
        "http://telegram-bot:8000",  # Telegram bot service
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Логируем входящий запрос
    logger.info(f"Incoming request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Вычисляем время обработки
    process_time = time.time() - start_time
    
    # Логируем ответ
    logger.info(
        f"Request completed: {request.method} {request.url} - "
        f"Status: {response.status_code} - Time: {process_time:.4f}s"
    )
    
    # Добавляем заголовок с временем обработки
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Обработчик ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации Pydantic"""
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "Переданные данные не прошли валидацию"
        }
    )

# Общий обработчик исключений
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Общий обработчик исключений"""
    logger.error(f"Unhandled exception on {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "Произошла внутренняя ошибка сервера"
        }
    )

# Подключение роутеров
app.include_router(users_router)

# Корневой endpoint
@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "User Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Простой health check"""
    return {
        "status": "healthy",
        "service": "user-service",
        "timestamp": time.time()
    }

# Metrics endpoint (для мониторинга)
@app.get("/metrics")
async def metrics():
    """Метрики сервиса (заглушка для Prometheus)"""
    return {
        "service": "user-service",
        "metrics": {
            "requests_total": "counter",
            "request_duration_seconds": "histogram",
            "active_connections": "gauge"
        }
    }

if __name__ == "__main__":
    # Получаем настройки из переменных окружения
    host = os.getenv("USER_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("USER_SERVICE_PORT", "8001"))
    
    # Запуск в режиме разработки
    logger.info(f"Starting User Service on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="info"
    )