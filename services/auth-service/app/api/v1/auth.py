# -*- coding: utf-8 -*-
"""
Auth Service - REST API Endpoints
API для аутентификации и авторизации
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...services.auth_service import AuthService
from ...schemas.auth import (
    AccessCodeRequest, LoginResponse, TokenRefreshRequest, TokenValidationRequest,
    TokenValidationResponse, LogoutRequest, SessionCreate, ApiKeyCreate, ApiKeyResponse,
    AuthStats, HealthCheckResponse, PermissionCheck, PermissionResponse
)
from ...core.security import permission_manager

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
security = HTTPBearer()

def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Извлечение информации о клиенте из запроса"""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return client_ip, user_agent

@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Простая проверка соединения с БД
        await db.execute("SELECT 1")
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            database_status="connected"
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database_status": "disconnected",
                "error": str(e)
            }
        )

@router.post("/login", response_model=LoginResponse)
async def login_with_access_code(
    request: AccessCodeRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Аутентификация по коду доступа
    """
    try:
        client_ip, user_agent = get_client_info(http_request)
        auth_service = AuthService(db)
        
        result = await auth_service.authenticate_with_access_code(
            request, client_ip, user_agent
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access code or authentication failed"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление токена
    """
    try:
        client_ip, user_agent = get_client_info(http_request)
        auth_service = AuthService(db)
        
        result = await auth_service.refresh_token(
            request, client_ip, user_agent
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )

@router.post("/validate", response_model=TokenValidationResponse)
async def validate_token(
    request: TokenValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Валидация токена
    """
    try:
        auth_service = AuthService(db)
        return await auth_service.validate_token(request.token)
        
    except Exception as e:
        return TokenValidationResponse(
            valid=False,
            error=f"Token validation error: {str(e)}"
        )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: LogoutRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Выход из системы
    """
    try:
        client_ip, user_agent = get_client_info(http_request)
        auth_service = AuthService(db)
        
        success = await auth_service.logout(request, client_ip, user_agent)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Logout failed"
            )
        
        return {"message": "Successfully logged out"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Создание новой сессии
    """
    try:
        client_ip, user_agent = get_client_info(http_request)
        
        # Дополняем данные сессии информацией о клиенте
        if not session_data.client_ip:
            session_data.client_ip = client_ip
        if not session_data.user_agent:
            session_data.user_agent = user_agent
        
        auth_service = AuthService(db)
        session_id = await auth_service.create_session(session_data)
        
        return {"session_id": session_id, "message": "Session created successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session creation failed: {str(e)}"
        )

@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    api_key_data: ApiKeyCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание API ключа (требует аутентификации)
    """
    try:
        # Валидируем токен
        auth_service = AuthService(db)
        validation = await auth_service.validate_token(credentials.credentials)
        
        if not validation.valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Проверяем права на создание API ключей
        if not permission_manager.check_permission(
            validation.user_role, "api_keys", "create"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create API keys"
            )
        
        result = await auth_service.create_api_key(validation.user_id, api_key_data)
        
        return ApiKeyResponse(
            api_key=result["api_key"],
            key_info=result["key_info"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API key creation failed: {str(e)}"
        )

@router.get("/stats", response_model=AuthStats)
async def get_auth_stats(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение статистики аутентификации (только для администраторов)
    """
    try:
        # Валидируем токен
        auth_service = AuthService(db)
        validation = await auth_service.validate_token(credentials.credentials)
        
        if not validation.valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Проверяем права на просмотр статистики
        if not permission_manager.check_permission(
            validation.user_role, "analytics", "read"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view auth stats"
            )
        
        return await auth_service.get_auth_stats()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch auth stats: {str(e)}"
        )

@router.post("/check-permission", response_model=PermissionResponse)
async def check_permission(
    permission_check: PermissionCheck,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Проверка прав доступа
    """
    try:
        # Валидируем токен
        auth_service = AuthService(db)
        validation = await auth_service.validate_token(credentials.credentials)
        
        if not validation.valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Проверяем запрашиваемое право
        allowed = permission_manager.check_permission(
            validation.user_role,
            permission_check.resource,
            permission_check.action,
            validation.user_id,
            permission_check.user_id
        )
        
        return PermissionResponse(
            allowed=allowed,
            reason="Permission granted" if allowed else "Permission denied",
            user_role=validation.user_role,
            scopes=validation.scopes or []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Permission check failed: {str(e)}"
        )

@router.get("/me")
async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение информации о текущем пользователе
    """
    try:
        # Валидируем токен
        auth_service = AuthService(db)
        validation = await auth_service.validate_token(credentials.credentials)
        
        if not validation.valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return {
            "user_id": validation.user_id,
            "user_role": validation.user_role,
            "expires_at": validation.expires_at,
            "scopes": validation.scopes or [],
            "permissions": permission_manager.get_role_permissions(validation.user_role)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )

# Middleware endpoint для валидации токенов (для других сервисов)
@router.post("/internal/validate-token", response_model=TokenValidationResponse)
async def internal_validate_token(
    request: TokenValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Внутренний endpoint для валидации токенов (используется другими сервисами)
    """
    auth_service = AuthService(db)
    return await auth_service.validate_token(request.token)

# Endpoint для получения информации о пользователе по токену
@router.get("/internal/user-info/{user_id}")
async def get_user_info_internal(
    user_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Внутренний endpoint для получения информации о пользователе
    """
    try:
        auth_service = AuthService(db)
        validation = await auth_service.validate_token(credentials.credentials)
        
        if not validation.valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Здесь можно добавить дополнительную логику получения информации
        # Пока возвращаем базовую информацию из токена
        return {
            "user_id": user_id,
            "authenticated": True,
            "role": validation.user_role if validation.user_id == user_id else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )