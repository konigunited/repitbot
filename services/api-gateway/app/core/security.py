# -*- coding: utf-8 -*-
"""
Security utilities for API Gateway
Утилиты безопасности для API Gateway
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import settings

logger = logging.getLogger(__name__)

# Схемы для токенов
class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
    scopes: list = []

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

# Security схема
security = HTTPBearer(auto_error=False)

class JWTHandler:
    """Обработчик JWT токенов"""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Создание access токена"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Создание refresh токена"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_token_pair(self, user_data: Dict[str, Any]) -> TokenResponse:
        """Создание пары токенов (access + refresh)"""
        access_token = self.create_access_token(user_data)
        refresh_token = self.create_refresh_token({"user_id": user_data.get("user_id")})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60
        )
    
    def verify_token(self, token: str, token_type: str = "access") -> TokenData:
        """Проверка и декодирование токена"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Проверяем тип токена
            if payload.get("type") != token_type:
                raise JWTError("Invalid token type")
            
            # Проверяем срок действия
            exp = payload.get("exp")
            if exp is None or datetime.fromtimestamp(exp) < datetime.utcnow():
                raise JWTError("Token expired")
            
            return TokenData(
                user_id=payload.get("user_id"),
                username=payload.get("username"),
                role=payload.get("role", "user"),
                scopes=payload.get("scopes", [])
            )
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """Обновление access токена по refresh токену"""
        token_data = self.verify_token(refresh_token, "refresh")
        
        # Создаем новый access токен
        new_token_data = {
            "user_id": token_data.user_id,
            "username": token_data.username,
            "role": token_data.role,
            "scopes": token_data.scopes
        }
        
        return self.create_access_token(new_token_data)

# Глобальный экземпляр
jwt_handler = JWTHandler()

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[TokenData]:
    """Получение текущего пользователя из токена"""
    if not settings.ENABLE_AUTHENTICATION:
        # Если аутентификация отключена, возвращаем mock пользователя
        return TokenData(user_id=1, username="test_user", role="user")
    
    if not credentials:
        return None
    
    try:
        token_data = jwt_handler.verify_token(credentials.credentials)
        return token_data
    except HTTPException:
        return None

async def require_authentication(credentials: HTTPAuthorizationCredentials = security) -> TokenData:
    """Требование аутентификации"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return jwt_handler.verify_token(credentials.credentials)

async def require_role(required_role: str, user: TokenData) -> TokenData:
    """Проверка роли пользователя"""
    if user.role != required_role and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {required_role} required"
        )
    return user

async def require_scope(required_scope: str, user: TokenData) -> TokenData:
    """Проверка области доступа"""
    if required_scope not in user.scopes and "all" not in user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Scope {required_scope} required"
        )
    return user

class SecurityHeaders:
    """Класс для добавления заголовков безопасности"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Получение заголовков безопасности"""
        if not settings.SECURE_HEADERS:
            return {}
        
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
        }

def validate_trusted_host(request: Request) -> bool:
    """Проверка доверенного хоста"""
    if "*" in settings.TRUSTED_HOSTS:
        return True
    
    host = request.headers.get("host", "")
    return host in settings.TRUSTED_HOSTS

def extract_client_ip(request: Request) -> str:
    """Извлечение IP адреса клиента"""
    # Проверяем заголовки прокси
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback к клиентскому IP
    client_host = getattr(request.client, "host", "unknown")
    return client_host

def generate_correlation_id() -> str:
    """Генерация ID корреляции для трассировки запросов"""
    import uuid
    return str(uuid.uuid4())