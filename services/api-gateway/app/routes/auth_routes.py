# -*- coding: utf-8 -*-
"""
Auth Routes for API Gateway
Маршруты аутентификации и авторизации
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional
import logging

from ..core.security import verify_token, create_access_token
from ..services.service_registry import get_service_registry

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/login")
async def login_proxy(credentials: Dict[str, Any]):
    """Прокси для авторизации через User Service"""
    registry = get_service_registry()
    
    # Проксируем запрос к User Service
    user_service_url = await registry.get_service_url("user-service")
    if not user_service_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not available"
        )
    
    # В реальной реализации здесь был бы HTTP запрос к user-service
    # Пока возвращаем заглушку
    return {
        "message": "Login proxy - implement HTTP call to user-service",
        "service_url": user_service_url
    }

@router.post("/refresh")
async def refresh_token_proxy(refresh_data: Dict[str, Any]):
    """Прокси для обновления токенов"""
    registry = get_service_registry()
    
    user_service_url = await registry.get_service_url("user-service")
    if not user_service_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not available"
        )
    
    return {
        "message": "Refresh token proxy - implement HTTP call to user-service",
        "service_url": user_service_url
    }

@router.get("/me")
async def get_current_user(current_user: Dict[str, Any] = Depends(verify_token)):
    """Получение информации о текущем пользователе"""
    return {
        "user": current_user,
        "authenticated_via": "gateway"
    }

@router.post("/logout") 
async def logout(current_user: Dict[str, Any] = Depends(verify_token)):
    """Выход из системы"""
    # В реальной реализации здесь была бы логика выхода
    return {
        "message": "Successfully logged out",
        "user_id": current_user.get("user_id")
    }

@router.get("/check")
async def check_auth(user_data: Optional[Dict[str, Any]] = Depends(verify_token)):
    """Проверка валидности токена"""
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return {
        "valid": True,
        "user": user_data
    }