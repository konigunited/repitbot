# -*- coding: utf-8 -*-
"""
API Gateway - FastAPI Application
Единая точка входа для всех микросервисов RepitBot
"""
import uvicorn
import logging
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from .core.config import get_settings
from .core.security import verify_token
from .middleware.auth_middleware import AuthMiddleware
from .middleware.rate_limit_middleware import RateLimitMiddleware
from .middleware.logging_middleware import LoggingMiddleware
from .routes.proxy_routes import router as proxy_router
from .routes.auth_routes import router as auth_router
from .routes.health_routes import router as health_router
from .services.service_registry import ServiceRegistry
from .services.circuit_breaker import CircuitBreakerManager
from .utils.proxy_utils import ProxyUtils

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные сервисы
service_registry = ServiceRegistry()
circuit_breaker_manager = CircuitBreakerManager()
proxy_utils = ProxyUtils()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events для FastAPI приложения"""
    # Startup
    logger.info("Starting API Gateway...")
    
    # Инициализируем реестр сервисов
    await service_registry.initialize()
    logger.info("Service registry initialized")
    
    # Инициализируем circuit breakers
    circuit_breaker_manager.initialize()
    logger.info("Circuit breakers initialized")
    
    # Запускаем фоновые задачи
    health_check_task = asyncio.create_task(service_registry.start_health_checks())
    metrics_task = asyncio.create_task(circuit_breaker_manager.start_metrics_collection())
    
    try:
        yield
    finally:
        # Shutdown
        logger.info("Shutting down API Gateway...")
        
        # Останавливаем фоновые задачи
        health_check_task.cancel()
        metrics_task.cancel()
        
        try:
            await health_check_task
        except asyncio.CancelledError:
            pass
        
        try:
            await metrics_task
        except asyncio.CancelledError:
            pass
        
        await service_registry.cleanup()
        logger.info("API Gateway shutdown complete")

# Создание FastAPI приложения
settings = get_settings()

app = FastAPI(
    title="RepitBot API Gateway",
    description="Единая точка входа для всех микросервисов RepitBot",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React frontend
        "http://localhost:8080",  # Vue.js frontend
        "https://repitbot.com",   # Production frontend
        "https://app.repitbot.com",  # Production app
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time", "X-Service"]
)

# Добавляем middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# Middleware для добавления заголовков
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # Добавляем уникальный ID запроса
    request_id = f"req_{int(time.time() * 1000)}_{id(request)}"
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    # Добавляем заголовки
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Gateway-Version"] = "1.0.0"
    
    return response

# Обработчики исключений
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации"""
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "Переданные данные не прошли валидацию",
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений"""
    logger.warning(f"HTTP exception on {request.url}: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP {exc.status_code}",
            "message": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Общий обработчик исключений"""
    logger.error(f"Unhandled exception on {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "Произошла внутренняя ошибка сервера",
            "request_id": getattr(request.state, "request_id", None)
        }
    )

# Подключение роутеров
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(proxy_router, prefix="", tags=["proxy"])

# Корневой endpoint
@app.get("/")
async def root():
    """Корневой endpoint API Gateway"""
    services_status = await service_registry.get_services_status()
    
    return {
        "service": "RepitBot API Gateway",
        "version": "1.0.0",
        "status": "running",
        "timestamp": time.time(),
        "features": [
            "Request routing",
            "Load balancing", 
            "Authentication & Authorization",
            "Rate limiting",
            "Circuit breaker",
            "Service discovery",
            "Request/Response transformation",
            "Monitoring & Logging"
        ],
        "services": services_status,
        "docs": "/docs" if settings.debug else "disabled",
        "endpoints": {
            "health": "/health",
            "auth": "/auth",
            "services": {
                "user": "/api/v1/users/*",
                "lesson": "/api/v1/lessons/*", 
                "homework": "/api/v1/homework/*",
                "payment": "/api/v1/payments/*",
                "material": "/api/v1/materials/*",
                "notification": "/api/v1/notifications/*",
                "analytics": "/api/v1/analytics/*",
                "student": "/api/v1/students/*"
            }
        }
    }

# Gateway info endpoint
@app.get("/gateway/info")
async def gateway_info():
    """Информация о шлюзе и подключенных сервисах"""
    return {
        "gateway": {
            "name": "RepitBot API Gateway",
            "version": "1.0.0",
            "uptime": time.time(),  # В реальной реализации должно быть время работы
            "environment": settings.environment,
            "debug": settings.debug
        },
        "services": await service_registry.get_detailed_services_info(),
        "circuit_breakers": circuit_breaker_manager.get_status(),
        "load_balancing": {
            "strategy": "round_robin",
            "health_check_interval": 30,
            "timeout": 5
        },
        "security": {
            "jwt_enabled": True,
            "rate_limiting": True,
            "cors_enabled": True
        }
    }

# Metrics endpoint для мониторинга
@app.get("/gateway/metrics")
async def gateway_metrics():
    """Метрики Gateway для мониторинга"""
    return {
        "timestamp": time.time(),
        "requests": {
            "total": "counter",
            "errors": "counter",
            "success_rate": "gauge"
        },
        "latency": {
            "p50": "histogram",
            "p95": "histogram", 
            "p99": "histogram"
        },
        "services": {
            "available": len(await service_registry.get_healthy_services()),
            "unhealthy": len(await service_registry.get_unhealthy_services())
        },
        "circuit_breakers": {
            service_name: breaker.get_metrics()
            for service_name, breaker in circuit_breaker_manager.get_all_breakers().items()
        }
    }

# Service discovery endpoint
@app.get("/gateway/services")
async def list_services():
    """Список всех зарегистрированных сервисов"""
    return {
        "services": await service_registry.get_all_services(),
        "healthy": await service_registry.get_healthy_services(),
        "unhealthy": await service_registry.get_unhealthy_services(),
        "last_updated": service_registry.last_health_check
    }

# Configuration endpoint
@app.get("/gateway/config")
async def gateway_config():
    """Конфигурация Gateway (только для админов)"""
    return {
        "rate_limiting": {
            "requests_per_minute": settings.rate_limit_per_minute,
            "burst_size": settings.rate_limit_burst
        },
        "timeouts": {
            "request_timeout": settings.request_timeout,
            "connect_timeout": settings.connect_timeout
        },
        "circuit_breaker": {
            "failure_threshold": settings.circuit_breaker_failure_threshold,
            "recovery_timeout": settings.circuit_breaker_recovery_timeout
        },
        "load_balancing": {
            "strategy": settings.load_balancer_strategy,
            "health_check_interval": settings.health_check_interval
        }
    }

if __name__ == "__main__":
    # Получаем настройки
    settings = get_settings()
    
    logger.info(f"Starting API Gateway on {settings.host}:{settings.port}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
        access_log=True,
        server_header=False,  # Скрываем версию сервера
        date_header=False     # Убираем дату из заголовков
    )