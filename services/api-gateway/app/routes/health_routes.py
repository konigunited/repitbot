# -*- coding: utf-8 -*-
"""
Health Check Routes for API Gateway
"""
from fastapi import APIRouter, HTTPException, status
import time
import logging

from ..services.service_registry import get_service_registry
from ..services.circuit_breaker import get_circuit_breaker_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
async def gateway_health():
    """Основная проверка здоровья Gateway"""
    registry = get_service_registry()
    cb_manager = get_circuit_breaker_manager()
    
    # Проверяем сервисы
    healthy_services = await registry.get_healthy_services()
    unhealthy_services = await registry.get_unhealthy_services()
    
    # Проверяем circuit breakers
    open_breakers = [
        name for name, breaker in cb_manager.get_all_breakers().items()
        if breaker.is_open()
    ]
    
    # Определяем общий статус
    critical_services = ["user-service", "lesson-service", "payment-service"]
    critical_unhealthy = [s for s in unhealthy_services if s in critical_services]
    
    if critical_unhealthy:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "unhealthy"
    elif len(healthy_services) == 0:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "critical"
    elif unhealthy_services:
        status_code = status.HTTP_200_OK
        overall_status = "degraded"
    else:
        status_code = status.HTTP_200_OK
        overall_status = "healthy"
    
    health_data = {
        "status": overall_status,
        "timestamp": time.time(),
        "gateway": {
            "version": "1.0.0",
            "uptime": time.time()  # Заменить на реальное время работы
        },
        "services": {
            "total": len(await registry.get_all_services()),
            "healthy": len(healthy_services),
            "unhealthy": len(unhealthy_services),
            "healthy_list": healthy_services,
            "unhealthy_list": unhealthy_services
        },
        "circuit_breakers": {
            "open": len(open_breakers),
            "open_list": open_breakers
        }
    }
    
    if status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status_code, detail=health_data)
    
    return health_data

@router.get("/ready")
async def readiness_check():
    """Проверка готовности к обслуживанию запросов"""
    registry = get_service_registry()
    
    # Проверяем критически важные сервисы
    critical_services = ["user-service", "lesson-service", "payment-service"]
    
    for service in critical_services:
        if not await registry.is_service_available(service):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Critical service {service} is not available"
            )
    
    return {
        "status": "ready",
        "timestamp": time.time(),
        "critical_services": critical_services
    }

@router.get("/live")
async def liveness_check():
    """Проверка жизнеспособности Gateway"""
    return {
        "status": "alive",
        "timestamp": time.time()
    }

@router.get("/detailed")
async def detailed_health():
    """Детальная информация о здоровье системы"""
    registry = get_service_registry()
    cb_manager = get_circuit_breaker_manager()
    
    return {
        "timestamp": time.time(),
        "gateway": {
            "status": "running",
            "version": "1.0.0"
        },
        "services": await registry.get_detailed_services_info(),
        "circuit_breakers": cb_manager.get_metrics(),
        "last_health_check": registry.last_health_check.isoformat() if registry.last_health_check else None
    }