# -*- coding: utf-8 -*-
"""
Auth Service - Security Utilities
Утилиты для работы с JWT, хэшированием и безопасностью
"""
import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from passlib.context import CryptContext
from jose import JWTError
import uuid

# Настройки JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Контекст для хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityManager:
    """Менеджер безопасности для Auth Service"""
    
    def __init__(self):
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM
    
    def create_access_token(
        self, 
        user_id: int, 
        user_role: str,
        scopes: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> tuple[str, str, datetime]:
        """
        Создание access токена
        
        Returns:
            tuple: (token, token_id, expires_at)
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        token_id = str(uuid.uuid4())
        
        payload = {
            "sub": str(user_id),  # subject
            "jti": token_id,      # JWT ID
            "exp": expire,        # expiration time
            "iat": datetime.utcnow(),  # issued at
            "type": "access",
            "role": user_role,
            "scopes": scopes or []
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, token_id, expire
    
    def create_refresh_token(
        self, 
        user_id: int,
        expires_delta: Optional[timedelta] = None
    ) -> tuple[str, str, datetime]:
        """
        Создание refresh токена
        
        Returns:
            tuple: (token, token_id, expires_at)
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        token_id = str(uuid.uuid4())
        
        payload = {
            "sub": str(user_id),
            "jti": token_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, token_id, expire
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Декодирование JWT токена
        
        Returns:
            dict: Payload токена или None при ошибке
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            print(f"JWT decode error: {e}")
            return None
    
    def validate_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        Валидация токена с проверкой типа
        
        Args:
            token: JWT токен
            token_type: Тип токена (access, refresh)
            
        Returns:
            dict: Payload если токен валидный, None иначе
        """
        payload = self.decode_token(token)
        
        if not payload:
            return None
        
        # Проверяем тип токена
        if payload.get("type") != token_type:
            return None
        
        # Проверяем истечение
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return None
        
        return payload
    
    def get_token_id(self, token: str) -> Optional[str]:
        """Получение ID токена (jti claim)"""
        payload = self.decode_token(token)
        return payload.get("jti") if payload else None
    
    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """Получение user_id из токена"""
        payload = self.validate_token(token)
        if payload:
            try:
                return int(payload.get("sub"))
            except (ValueError, TypeError):
                return None
        return None
    
    def hash_token(self, token: str) -> str:
        """Хэширование токена для безопасного хранения"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def generate_access_code(self, length: int = 8) -> str:
        """Генерация кода доступа"""
        return secrets.token_urlsafe(length)[:length].upper()
    
    def generate_api_key(self) -> tuple[str, str]:
        """
        Генерация API ключа
        
        Returns:
            tuple: (api_key, key_id)
        """
        key_id = str(uuid.uuid4())
        key_secret = secrets.token_urlsafe(32)
        api_key = f"rpb_{key_id}_{key_secret}"
        return api_key, key_id
    
    def hash_password(self, password: str) -> str:
        """Хэширование пароля"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверка пароля"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_session_id(self) -> str:
        """Создание ID сессии"""
        return secrets.token_urlsafe(32)

class PermissionManager:
    """Менеджер прав доступа"""
    
    # Определение ролей и их прав
    ROLE_PERMISSIONS = {
        "tutor": [
            "users:read",
            "users:create", 
            "users:update",
            "users:delete",
            "lessons:read",
            "lessons:create",
            "lessons:update", 
            "lessons:delete",
            "homework:read",
            "homework:create",
            "homework:update",
            "homework:check",
            "materials:read",
            "materials:create",
            "materials:update",
            "materials:delete",
            "payments:read",
            "payments:create",
            "analytics:read",
            "dashboard:access"
        ],
        "student": [
            "lessons:read:own",
            "homework:read:own",
            "homework:submit",
            "materials:read",
            "progress:read:own",
            "achievements:read:own"
        ],
        "parent": [
            "lessons:read:children",
            "homework:read:children", 
            "materials:read",
            "progress:read:children",
            "payments:read:children",
            "achievements:read:children"
        ]
    }
    
    def __init__(self):
        pass
    
    def get_role_permissions(self, role: str) -> List[str]:
        """Получение прав роли"""
        return self.ROLE_PERMISSIONS.get(role, [])
    
    def check_permission(
        self, 
        user_role: str, 
        resource: str, 
        action: str,
        user_id: Optional[int] = None,
        resource_owner_id: Optional[int] = None
    ) -> bool:
        """
        Проверка права доступа
        
        Args:
            user_role: Роль пользователя
            resource: Ресурс (users, lessons, homework, etc.)
            action: Действие (read, create, update, delete)
            user_id: ID пользователя
            resource_owner_id: ID владельца ресурса
        """
        permissions = self.get_role_permissions(user_role)
        
        # Полное право
        full_permission = f"{resource}:{action}"
        if full_permission in permissions:
            return True
        
        # Право на собственные ресурсы
        own_permission = f"{resource}:{action}:own"
        if own_permission in permissions and user_id == resource_owner_id:
            return True
        
        # Право родителя на ресурсы детей (нужна дополнительная проверка)
        children_permission = f"{resource}:{action}:children"
        if children_permission in permissions:
            # Здесь должна быть проверка, что resource_owner_id - ребенок user_id
            # Для упрощения возвращаем True (в реальности нужен запрос к User Service)
            return True
        
        return False
    
    def filter_permissions_by_scopes(
        self, 
        permissions: List[str], 
        scopes: List[str]
    ) -> List[str]:
        """Фильтрация прав по скоупам"""
        if not scopes:
            return permissions
        
        filtered = []
        for perm in permissions:
            for scope in scopes:
                if perm.startswith(scope):
                    filtered.append(perm)
                    break
        
        return filtered

# Глобальные экземпляры
security_manager = SecurityManager()
permission_manager = PermissionManager()

# Вспомогательные функции
def create_tokens_for_user(user_id: int, user_role: str) -> Dict[str, Any]:
    """Создание пары access/refresh токенов для пользователя"""
    access_token, access_token_id, access_expires = security_manager.create_access_token(
        user_id=user_id,
        user_role=user_role
    )
    
    refresh_token, refresh_token_id, refresh_expires = security_manager.create_refresh_token(
        user_id=user_id
    )
    
    return {
        "access_token": access_token,
        "access_token_id": access_token_id,
        "access_expires_at": access_expires,
        "refresh_token": refresh_token,
        "refresh_token_id": refresh_token_id,
        "refresh_expires_at": refresh_expires,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

def hash_string(text: str) -> str:
    """Хэширование строки"""
    return hashlib.sha256(text.encode()).hexdigest()

def generate_secure_random_string(length: int = 32) -> str:
    """Генерация безопасной случайной строки"""
    return secrets.token_urlsafe(length)