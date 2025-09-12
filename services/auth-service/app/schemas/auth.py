# -*- coding: utf-8 -*-
"""
Auth Service - Pydantic Schemas
Схемы для аутентификации и авторизации
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"

# === Базовые схемы ===

class TokenBase(BaseModel):
    """Базовая схема токена"""
    user_id: int
    token_type: TokenType
    expires_at: datetime

class TokenCreate(TokenBase):
    """Схема для создания токена"""
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None

class TokenInDB(TokenBase):
    """Схема токена в базе данных"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    token_id: str
    token_hash: str
    issued_at: datetime
    is_revoked: bool = False
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

# === Схемы аутентификации ===

class AccessCodeRequest(BaseModel):
    """Запрос с кодом доступа"""
    access_code: str = Field(..., min_length=6, max_length=10, description="Код доступа")
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    username: Optional[str] = Field(None, max_length=50, description="Username в Telegram")

class LoginResponse(BaseModel):
    """Ответ при успешной аутентификации"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Время жизни access token в секундах
    user_id: int
    user_role: str

class TokenRefreshRequest(BaseModel):
    """Запрос на обновление токена"""
    refresh_token: str = Field(..., description="Refresh токен")

class TokenValidationRequest(BaseModel):
    """Запрос на валидацию токена"""
    token: str = Field(..., description="JWT токен для валидации")

class TokenValidationResponse(BaseModel):
    """Ответ валидации токена"""
    valid: bool
    user_id: Optional[int] = None
    user_role: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[List[str]] = None
    error: Optional[str] = None

class LogoutRequest(BaseModel):
    """Запрос на выход"""
    token: str = Field(..., description="Access токен")
    refresh_token: Optional[str] = Field(None, description="Refresh токен (опционально)")

# === Схемы сессий ===

class SessionCreate(BaseModel):
    """Создание сессии"""
    user_id: int
    telegram_id: Optional[int] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    expires_in: int = 3600  # Время жизни в секундах

class Session(BaseModel):
    """Схема сессии"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    session_id: str
    user_id: int
    is_active: bool
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    telegram_id: Optional[int] = None

# === Схемы API ключей ===

class ApiKeyCreate(BaseModel):
    """Создание API ключа"""
    name: str = Field(..., min_length=1, max_length=100, description="Название ключа")
    description: Optional[str] = Field(None, max_length=500, description="Описание ключа")
    scopes: Optional[List[str]] = Field(default_factory=list, description="Разрешения")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Время жизни в днях")

class ApiKey(BaseModel):
    """Схема API ключа"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    key_id: str
    name: str
    description: Optional[str] = None
    scopes: List[str] = []
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    use_count: int = 0

class ApiKeyResponse(BaseModel):
    """Ответ при создании API ключа"""
    api_key: str  # Полный ключ (показывается только один раз)
    key_info: ApiKey

# === Схемы логирования ===

class AuthLogCreate(BaseModel):
    """Создание записи в журнале аутентификации"""
    user_id: Optional[int] = None
    event_type: str
    success: bool
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    telegram_id: Optional[int] = None

class AuthLog(BaseModel):
    """Схема записи журнала аутентификации"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: Optional[int] = None
    event_type: str
    success: bool
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    telegram_id: Optional[int] = None
    created_at: datetime

# === Схемы статистики ===

class AuthStats(BaseModel):
    """Статистика аутентификации"""
    total_active_sessions: int
    total_active_tokens: int
    total_api_keys: int
    successful_logins_24h: int
    failed_logins_24h: int
    unique_users_24h: int

class UserAuthInfo(BaseModel):
    """Информация об аутентификации пользователя"""
    user_id: int
    active_sessions: List[Session]
    active_tokens_count: int
    api_keys_count: int
    last_login: Optional[datetime] = None
    total_logins: int

# === Health Check ===

class HealthCheckResponse(BaseModel):
    """Ответ health check"""
    status: str = "healthy"
    timestamp: datetime
    version: str = "1.0.0"
    database_status: str = "connected"
    redis_status: Optional[str] = "not_configured"

# === Permissions ===

class PermissionCheck(BaseModel):
    """Проверка прав доступа"""
    user_id: int
    resource: str
    action: str

class PermissionResponse(BaseModel):
    """Ответ проверки прав"""
    allowed: bool
    reason: Optional[str] = None
    user_role: str
    scopes: List[str] = []

# === Bulk Operations ===

class BulkTokenRevoke(BaseModel):
    """Массовое отзыв токенов"""
    user_ids: Optional[List[int]] = None
    token_ids: Optional[List[str]] = None
    reason: str = "Bulk revocation"

class BulkSessionTerminate(BaseModel):
    """Массовое завершение сессий"""
    user_ids: Optional[List[int]] = None
    session_ids: Optional[List[str]] = None
    reason: str = "Bulk termination"