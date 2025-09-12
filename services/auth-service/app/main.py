# -*- coding: utf-8 -*-
"""
Auth Service - FastAPI Application
Микросервис аутентификации и авторизации
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
from .api.v1.auth import router as auth_router

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
    logger.info("Starting Auth Service...")
    await init_db()
    logger.info("Auth Service database initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Auth Service...")
    await close_db()
    logger.info("Auth Service database connections closed")

# Создание FastAPI приложения
app = FastAPI(
    title="Auth Service",
    description="Микросервис аутентификации и авторизации для RepitBot",
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
        "http://user-service:8001",  # User service
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Не логируем содержимое токенов и паролей
    log_body = request.method in ["GET", "DELETE"]
    if request.url.path in ["/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/validate"]:
        log_body = False
    
    if log_body:
        logger.info(f"Incoming request: {request.method} {request.url}")
    else:
        logger.info(f"Incoming request: {request.method} {request.url.path} [body hidden]")
    
    response = await call_next(request)
    
    # Вычисляем время обработки
    process_time = time.time() - start_time
    
    # Логируем ответ
    logger.info(
        f"Request completed: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - Time: {process_time:.4f}s"
    )
    
    # Добавляем заголовки
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Service"] = "auth-service"
    
    return response

# Middleware для обеспечения безопасности
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Добавляем заголовки безопасности
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# Обработчик ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации Pydantic"""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
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
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "Произошла внутренняя ошибка сервера аутентификации"
        }
    )

# Подключение роутеров
app.include_router(auth_router)

# Корневой endpoint
@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "Auth Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "features": [
            "JWT Authentication",
            "Access Code Validation",
            "Token Refresh",
            "Session Management",
            "API Keys",
            "Permission Checking",
            "Audit Logging"
        ]
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Простой health check"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "timestamp": time.time()
    }

# Metrics endpoint (для мониторинга)
@app.get("/metrics")
async def metrics():
    """Метрики сервиса (заглушка для Prometheus)"""
    return {
        "service": "auth-service",
        "metrics": {
            "authentication_requests_total": "counter",
            "authentication_duration_seconds": "histogram", 
            "active_sessions": "gauge",
            "active_tokens": "gauge",
            "failed_login_attempts": "counter"
        }
    }

# Endpoint для проверки состояния JWT ключей
@app.get("/jwt-info")
async def jwt_info():
    """Информация о JWT конфигурации (без секретов)"""
    from .core.security import JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
    
    return {
        "algorithm": JWT_ALGORITHM,
        "access_token_expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
        "refresh_token_expire_days": REFRESH_TOKEN_EXPIRE_DAYS,
        "secret_key_configured": bool(os.getenv("JWT_SECRET_KEY")),
        "warning": "Ensure JWT_SECRET_KEY is set in production!"
    }

if __name__ == "__main__":
    # Получаем настройки из переменных окружения
    host = os.getenv("AUTH_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("AUTH_SERVICE_PORT", "8002"))
    
    # Запуск в режиме разработки
    logger.info(f"Starting Auth Service on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="info"
    )