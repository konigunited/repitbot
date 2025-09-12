# -*- coding: utf-8 -*-
"""
Student Service - FastAPI Application
Микросервис управления студентами и геймификацией
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
from .api.v1.students import router as students_router
from .api.v1.achievements import router as achievements_router
from .api.v1.progress import router as progress_router
from .services.achievement_service import AchievementService

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
    logger.info("Starting Student Service...")
    await init_db()
    logger.info("Database initialized successfully")
    
    # Инициализируем стандартные достижения
    achievement_service = AchievementService()
    await achievement_service.initialize_default_achievements()
    logger.info("Default achievements initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Student Service...")
    await close_db()
    logger.info("Database connections closed")

# Создание FastAPI приложения
app = FastAPI(
    title="Student Service",
    description="Микросервис управления студентами и геймификацией для RepitBot",
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
        "http://localhost:8000",  # API Gateway
        "http://api-gateway:8000",  # API Gateway (внутри контейнера)
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
from .api.v1.recommendations import router as recommendations_router

app.include_router(students_router, prefix="/api/v1")
app.include_router(achievements_router, prefix="/api/v1")
app.include_router(progress_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")

# Корневой endpoint
@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "Student Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "features": [
            "Student profile management",
            "Achievement system",
            "Gamification",
            "Learning progress tracking",
            "Recommendations engine"
        ]
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Простой health check"""
    return {
        "status": "healthy",
        "service": "student-service",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

# Detailed health check
@app.get("/health/detailed")
async def detailed_health_check():
    """Детальная проверка здоровья сервиса"""
    try:
        # Проверяем подключение к базе данных
        from .database.connection import get_db_session
        async with get_db_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "student-service",
        "timestamp": time.time(),
        "version": "1.0.0",
        "checks": {
            "database": db_status,
            "memory": "healthy",  # Можно добавить реальную проверку
            "disk": "healthy"     # Можно добавить реальную проверку
        }
    }

# Metrics endpoint (для мониторинга)
@app.get("/metrics")
async def metrics():
    """Метрики сервиса (для Prometheus)"""
    return {
        "service": "student-service",
        "metrics": {
            "requests_total": "counter",
            "request_duration_seconds": "histogram",
            "active_connections": "gauge",
            "students_total": "gauge",
            "achievements_total": "gauge",
            "xp_transactions_total": "counter"
        }
    }

# Readiness probe
@app.get("/ready")
async def readiness_check():
    """Проверка готовности к обслуживанию запросов"""
    try:
        # Проверяем доступность базы данных
        from .database.connection import get_db_session
        async with get_db_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        
        return {"status": "ready", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "error": str(e)}
        )

# Liveness probe
@app.get("/live")
async def liveness_check():
    """Проверка жизнеспособности сервиса"""
    return {"status": "alive", "timestamp": time.time()}

if __name__ == "__main__":
    # Получаем настройки из переменных окружения
    host = os.getenv("STUDENT_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("STUDENT_SERVICE_PORT", "8008"))
    
    # Запуск в режиме разработки
    logger.info(f"Starting Student Service on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="info"
    )