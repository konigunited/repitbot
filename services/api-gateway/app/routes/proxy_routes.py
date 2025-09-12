# -*- coding: utf-8 -*-
"""
Proxy Routes for API Gateway
Маршрутизация запросов к микросервисам
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import Response
import httpx
import logging
from typing import Any, Dict, Optional
import asyncio

from ..core.config import get_settings
from ..services.service_registry import get_service_registry
from ..services.circuit_breaker import get_circuit_breaker_manager
from ..core.security import verify_token_optional
from ..utils.proxy_utils import ProxyUtils

router = APIRouter()
logger = logging.getLogger(__name__)

# Service mapping configuration
SERVICE_ROUTES = {
    # User Service
    "/api/v1/users": {"service": "user-service", "port": 8001, "strip_prefix": False},
    "/api/v1/auth": {"service": "user-service", "port": 8001, "strip_prefix": False},
    
    # Lesson Service  
    "/api/v1/lessons": {"service": "lesson-service", "port": 8002, "strip_prefix": False},
    "/api/v1/schedule": {"service": "lesson-service", "port": 8002, "strip_prefix": False},
    
    # Homework Service
    "/api/v1/homework": {"service": "homework-service", "port": 8003, "strip_prefix": False},
    "/api/v1/assignments": {"service": "homework-service", "port": 8003, "strip_prefix": False},
    
    # Payment Service
    "/api/v1/payments": {"service": "payment-service", "port": 8004, "strip_prefix": False},
    "/api/v1/billing": {"service": "payment-service", "port": 8004, "strip_prefix": False},
    "/api/v1/balance": {"service": "payment-service", "port": 8004, "strip_prefix": False},
    
    # Material Service
    "/api/v1/materials": {"service": "material-service", "port": 8005, "strip_prefix": False},
    "/api/v1/library": {"service": "material-service", "port": 8005, "strip_prefix": False},
    "/api/v1/files": {"service": "material-service", "port": 8005, "strip_prefix": False},
    
    # Notification Service
    "/api/v1/notifications": {"service": "notification-service", "port": 8006, "strip_prefix": False},
    "/api/v1/messages": {"service": "notification-service", "port": 8006, "strip_prefix": False},
    
    # Analytics Service
    "/api/v1/analytics": {"service": "analytics-service", "port": 8007, "strip_prefix": False},
    "/api/v1/reports": {"service": "analytics-service", "port": 8007, "strip_prefix": False},
    "/api/v1/charts": {"service": "analytics-service", "port": 8007, "strip_prefix": False},
    
    # Student Service
    "/api/v1/students": {"service": "student-service", "port": 8008, "strip_prefix": False},
    "/api/v1/achievements": {"service": "student-service", "port": 8008, "strip_prefix": False},
    "/api/v1/gamification": {"service": "student-service", "port": 8008, "strip_prefix": False},
    "/api/v1/progress": {"service": "student-service", "port": 8008, "strip_prefix": False},
}

# Protected routes that require authentication
PROTECTED_ROUTES = [
    "/api/v1/users/profile",
    "/api/v1/users/settings", 
    "/api/v1/lessons",
    "/api/v1/homework",
    "/api/v1/payments",
    "/api/v1/materials",
    "/api/v1/notifications",
    "/api/v1/analytics",
    "/api/v1/students",
    "/api/v1/achievements",
]

# Admin-only routes
ADMIN_ROUTES = [
    "/api/v1/users/admin",
    "/api/v1/analytics/admin",
    "/api/v1/reports/admin",
]

def get_proxy_utils() -> ProxyUtils:
    """Dependency для получения ProxyUtils"""
    return ProxyUtils()

async def route_request(
    path: str,
    method: str,
    headers: Dict[str, str],
    query_params: str,
    body: bytes,
    user_data: Optional[Dict[str, Any]] = None
) -> httpx.Response:
    """Маршрутизация запроса к соответствующему сервису"""
    
    # Находим подходящий сервис для маршрута
    target_service = None
    target_config = None
    
    for route_prefix, config in SERVICE_ROUTES.items():
        if path.startswith(route_prefix):
            target_service = config["service"]
            target_config = config
            break
    
    if not target_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service not found for path: {path}"
        )
    
    # Получаем registry и circuit breaker manager
    registry = get_service_registry()
    cb_manager = get_circuit_breaker_manager()
    
    # Проверяем circuit breaker
    circuit_breaker = cb_manager.get_breaker(target_service)
    if circuit_breaker.is_open():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {target_service} is currently unavailable"
        )
    
    # Получаем URL сервиса
    service_url = await registry.get_service_url(target_service)
    if not service_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {target_service} is not available"
        )
    
    # Формируем полный URL
    target_path = path
    if target_config.get("strip_prefix"):
        for prefix in SERVICE_ROUTES.keys():
            if path.startswith(prefix):
                target_path = path[len(prefix):]
                break
    
    full_url = f"{service_url}{target_path}"
    if query_params:
        full_url += f"?{query_params}"
    
    # Подготавливаем заголовки
    forwarded_headers = {
        "X-Forwarded-For": headers.get("x-forwarded-for", "unknown"),
        "X-Forwarded-Proto": headers.get("x-forwarded-proto", "http"),
        "X-Gateway-Request-ID": headers.get("x-request-id", "unknown"),
        "Content-Type": headers.get("content-type", "application/json"),
    }
    
    # Добавляем информацию о пользователе
    if user_data:
        forwarded_headers["X-User-ID"] = str(user_data.get("user_id", ""))
        forwarded_headers["X-User-Role"] = user_data.get("role", "")
        forwarded_headers["X-User-Email"] = user_data.get("email", "")
    
    # Копируем авторизационные заголовки
    auth_header = headers.get("authorization")
    if auth_header:
        forwarded_headers["Authorization"] = auth_header
    
    try:
        # Выполняем запрос к сервису
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=full_url,
                headers=forwarded_headers,
                content=body,
            )
            
        # Записываем успешный вызов в circuit breaker
        await circuit_breaker.record_success()
        
        return response
        
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        # Записываем ошибку в circuit breaker
        await circuit_breaker.record_failure()
        
        logger.error(f"Error calling {target_service} at {full_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {target_service} is not responding"
        )
    except httpx.HTTPStatusError as e:
        # Не записываем HTTP ошибки как сбои сервиса
        logger.warning(f"HTTP error from {target_service}: {e.response.status_code}")
        return e.response
    except Exception as e:
        await circuit_breaker.record_failure()
        logger.error(f"Unexpected error calling {target_service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal gateway error"
        )

def is_route_protected(path: str) -> bool:
    """Проверяет, требует ли маршрут авторизации"""
    return any(path.startswith(protected) for protected in PROTECTED_ROUTES)

def is_admin_route(path: str) -> bool:
    """Проверяет, является ли маршрут административным"""
    return any(path.startswith(admin) for admin in ADMIN_ROUTES)

# Generic proxy endpoint that handles all API routes
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_request(
    request: Request,
    path: str,
    user_data: Optional[Dict[str, Any]] = Depends(verify_token_optional)
):
    """Главный proxy endpoint для всех API запросов"""
    
    # Получаем полный путь с префиксом
    full_path = "/" + path
    
    # Проверяем авторизацию для защищенных маршрутов
    if is_route_protected(full_path) and not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Проверяем права администратора для админских маршрутов
    if is_admin_route(full_path):
        if not user_data or user_data.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
    
    # Получаем тело запроса
    body = await request.body()
    
    # Получаем параметры запроса
    query_string = str(request.query_params)
    
    # Получаем заголовки
    headers = dict(request.headers)
    
    try:
        # Маршрутизируем запрос
        service_response = await route_request(
            path=full_path,
            method=request.method,
            headers=headers,
            query_params=query_string,
            body=body,
            user_data=user_data
        )
        
        # Подготавливаем заголовки ответа
        response_headers = {}
        for key, value in service_response.headers.items():
            # Исключаем системные заголовки
            if key.lower() not in ["content-length", "content-encoding", "transfer-encoding"]:
                response_headers[key] = value
        
        # Добавляем заголовки Gateway
        response_headers["X-Gateway"] = "RepitBot-API-Gateway"
        response_headers["X-Service"] = full_path.split("/")[3] if len(full_path.split("/")) > 3 else "unknown"
        
        return Response(
            content=service_response.content,
            status_code=service_response.status_code,
            headers=response_headers,
            media_type=service_response.headers.get("content-type")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Proxy error for {full_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gateway proxy error"
        )

# Health check proxy for services
@router.get("/services/{service_name}/health")
async def proxy_service_health(service_name: str):
    """Проверка здоровья конкретного сервиса"""
    registry = get_service_registry()
    
    service_url = await registry.get_service_url(service_name)
    if not service_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} not found"
        )
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service_url}/health")
            
        return {
            "service": service_name,
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds(),
            "details": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
        }
        
    except Exception as e:
        return {
            "service": service_name,
            "status": "unhealthy",
            "error": str(e),
            "response_time": None
        }

# Batch health check for all services
@router.get("/services/health")
async def check_all_services_health():
    """Проверка здоровья всех сервисов"""
    registry = get_service_registry()
    services = await registry.get_all_services()
    
    results = {}
    
    # Проверяем все сервисы параллельно
    tasks = []
    for service_name in services.keys():
        task = asyncio.create_task(proxy_service_health(service_name))
        tasks.append((service_name, task))
    
    for service_name, task in tasks:
        try:
            result = await task
            results[service_name] = result
        except Exception as e:
            results[service_name] = {
                "service": service_name,
                "status": "error",
                "error": str(e)
            }
    
    # Подсчитываем общую статистику
    healthy_count = sum(1 for r in results.values() if r.get("status") == "healthy")
    total_count = len(results)
    
    return {
        "timestamp": asyncio.get_event_loop().time(),
        "summary": {
            "total_services": total_count,
            "healthy_services": healthy_count,
            "unhealthy_services": total_count - healthy_count,
            "overall_status": "healthy" if healthy_count == total_count else "degraded"
        },
        "services": results
    }