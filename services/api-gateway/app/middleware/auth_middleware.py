# -*- coding: utf-8 -*-
"""
Authentication Middleware for API Gateway
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import logging
from typing import Optional

from ..core.security import verify_jwt_token

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware для обработки аутентификации"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Маршруты, не требующие авторизации
        self.public_paths = {
            "/",
            "/docs", 
            "/redoc",
            "/openapi.json",
            "/health",
            "/health/",
            "/health/ready",
            "/health/live",
            "/health/detailed",
            "/gateway/info",
            "/auth/login",
            "/auth/refresh",
        }
        
        # Префиксы публичных путей
        self.public_prefixes = [
            "/health",
            "/gateway",
            "/auth/login",
            "/auth/refresh",
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Основная логика middleware"""
        
        # Проверяем, является ли путь публичным
        if self.is_public_path(request.url.path):
            return await call_next(request)
        
        # Извлекаем токен из заголовков
        auth_header = request.headers.get("Authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Убираем "Bearer "
        
        # Если токен есть, пытаемся его проверить
        user_data = None
        if token:
            try:
                user_data = verify_jwt_token(token)
                # Добавляем информацию о пользователе в request
                request.state.user = user_data
                request.state.authenticated = True
            except Exception as e:
                logger.warning(f"Token verification failed: {e}")
                request.state.user = None
                request.state.authenticated = False
        else:
            request.state.user = None
            request.state.authenticated = False
        
        # Проверяем, требует ли маршрут аутентификации
        if self.requires_auth(request.url.path) and not user_data:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication required",
                    "message": "This endpoint requires authentication",
                    "path": request.url.path
                }
            )
        
        return await call_next(request)
    
    def is_public_path(self, path: str) -> bool:
        """Проверяет, является ли путь публичным"""
        # Точное совпадение
        if path in self.public_paths:
            return True
        
        # Проверяем префиксы
        for prefix in self.public_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def requires_auth(self, path: str) -> bool:
        """Проверяет, требует ли путь аутентификации"""
        # Большинство API путей требуют авторизации
        if path.startswith("/api/v1/"):
            # Исключения для некоторых публичных API
            public_api_prefixes = [
                "/api/v1/auth/login",
                "/api/v1/auth/refresh",
                "/api/v1/users/register",
            ]
            
            for public_prefix in public_api_prefixes:
                if path.startswith(public_prefix):
                    return False
            
            return True
        
        return False