# -*- coding: utf-8 -*-
"""
Telegram Bot - Auth Service Client
HTTP клиент для взаимодействия с Auth Service
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from .api_client import BaseApiClient, ServiceUnavailableError, with_fallback, service_registry

logger = logging.getLogger(__name__)

class AuthServiceClient(BaseApiClient):
    """Клиент для взаимодействия с Auth Service"""
    
    def __init__(self):
        config = service_registry.get_service_config('auth')
        super().__init__(
            base_url=config.get('url', 'http://localhost:8002'),
            service_name='auth-service',
            timeout=config.get('timeout', 10),
            max_retries=config.get('retries', 3)
        )
    
    # === Authentication ===
    
    async def login_with_access_code(
        self, 
        access_code: str, 
        telegram_id: int,
        username: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Аутентификация по коду доступа"""
        try:
            data = {
                'access_code': access_code,
                'telegram_id': telegram_id
            }
            if username:
                data['username'] = username
            
            return await self.post('/api/v1/auth/login', data=data)
        except Exception as e:
            logger.error(f"Failed to login with access code: {e}")
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Обновление токена"""
        try:
            data = {'refresh_token': refresh_token}
            return await self.post('/api/v1/auth/refresh', data=data)
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            return None
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Валидация токена"""
        try:
            data = {'token': token}
            return await self.post('/api/v1/auth/validate', data=data)
        except Exception as e:
            logger.error(f"Failed to validate token: {e}")
            return {'valid': False, 'error': str(e)}
    
    async def logout(
        self, 
        access_token: str, 
        refresh_token: Optional[str] = None
    ) -> bool:
        """Выход из системы"""
        try:
            data = {'token': access_token}
            if refresh_token:
                data['refresh_token'] = refresh_token
            
            await self.post('/api/v1/auth/logout', data=data)
            return True
        except Exception as e:
            logger.error(f"Failed to logout: {e}")
            return False
    
    # === Session Management ===
    
    async def create_session(
        self, 
        user_id: int,
        telegram_id: Optional[int] = None,
        expires_in: int = 3600
    ) -> Optional[str]:
        """Создание сессии"""
        try:
            data = {
                'user_id': user_id,
                'telegram_id': telegram_id,
                'expires_in': expires_in
            }
            
            result = await self.post('/api/v1/auth/sessions', data=data)
            return result.get('session_id')
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None
    
    # === API Keys ===
    
    async def create_api_key(
        self, 
        name: str,
        description: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Создание API ключа"""
        try:
            data = {
                'name': name,
                'description': description,
                'scopes': scopes or [],
                'expires_in_days': expires_in_days
            }
            
            return await self.post('/api/v1/auth/api-keys', data=data)
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            return None
    
    # === Permissions ===
    
    async def check_permission(
        self, 
        user_id: int,
        resource: str,
        action: str
    ) -> bool:
        """Проверка прав доступа"""
        try:
            data = {
                'user_id': user_id,
                'resource': resource,
                'action': action
            }
            
            result = await self.post('/api/v1/auth/check-permission', data=data)
            return result.get('allowed', False)
        except Exception as e:
            logger.error(f"Failed to check permission: {e}")
            return False
    
    # === User Info ===
    
    async def get_current_user_info(self) -> Optional[Dict[str, Any]]:
        """Получение информации о текущем пользователе"""
        try:
            return await self.get('/api/v1/auth/me')
        except Exception as e:
            logger.error(f"Failed to get current user info: {e}")
            return None
    
    # === Statistics ===
    
    async def get_auth_stats(self) -> Dict[str, Any]:
        """Получение статистики аутентификации"""
        try:
            return await self.get('/api/v1/auth/stats')
        except Exception as e:
            logger.error(f"Failed to get auth stats: {e}")
            return {}

# Создаем экземпляр клиента
auth_service_client = AuthServiceClient()

# === Менеджер токенов ===

class TokenManager:
    """Менеджер токенов для Telegram бота"""
    
    def __init__(self):
        self.user_tokens: Dict[int, Dict[str, Any]] = {}  # user_id -> token_data
    
    def store_user_tokens(self, user_id: int, token_data: Dict[str, Any]):
        """Сохранение токенов пользователя"""
        self.user_tokens[user_id] = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_at': datetime.utcnow() + timedelta(seconds=token_data['expires_in']),
            'user_role': token_data.get('user_role', 'student')
        }
        logger.debug(f"Stored tokens for user {user_id}")
    
    def get_user_tokens(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение токенов пользователя"""
        return self.user_tokens.get(user_id)
    
    def get_access_token(self, user_id: int) -> Optional[str]:
        """Получение access токена пользователя"""
        tokens = self.get_user_tokens(user_id)
        if tokens and not self.is_token_expired(user_id):
            return tokens['access_token']
        return None
    
    def is_token_expired(self, user_id: int) -> bool:
        """Проверка истечения токена"""
        tokens = self.get_user_tokens(user_id)
        if not tokens:
            return True
        
        expires_at = tokens.get('expires_at')
        if not expires_at:
            return True
        
        return datetime.utcnow() >= expires_at
    
    async def refresh_user_token(self, user_id: int) -> bool:
        """Обновление токена пользователя"""
        tokens = self.get_user_tokens(user_id)
        if not tokens:
            return False
        
        refresh_token = tokens.get('refresh_token')
        if not refresh_token:
            return False
        
        try:
            async with auth_service_client:
                new_tokens = await auth_service_client.refresh_token(refresh_token)
                
                if new_tokens:
                    self.store_user_tokens(user_id, new_tokens)
                    return True
        except Exception as e:
            logger.error(f"Failed to refresh token for user {user_id}: {e}")
        
        return False
    
    def clear_user_tokens(self, user_id: int):
        """Очистка токенов пользователя"""
        if user_id in self.user_tokens:
            del self.user_tokens[user_id]
            logger.debug(f"Cleared tokens for user {user_id}")
    
    async def ensure_valid_token(self, user_id: int) -> Optional[str]:
        """Обеспечение валидного токена (с автообновлением)"""
        # Проверяем текущий токен
        access_token = self.get_access_token(user_id)
        if access_token:
            return access_token
        
        # Пытаемся обновить токен
        if await self.refresh_user_token(user_id):
            return self.get_access_token(user_id)
        
        return None

# Глобальный менеджер токенов
token_manager = TokenManager()

# === Fallback функции ===

async def _fallback_login_with_access_code(
    access_code: str, 
    telegram_id: int,
    username: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Fallback: простая проверка без JWT"""
    try:
        from .user_service_client import validate_access_code
        
        result = await validate_access_code(access_code, telegram_id, username)
        
        if result.get('success'):
            # Создаем простой "токен" (на самом деле просто user_id)
            return {
                'access_token': f"fallback_token_{result['user_id']}",
                'refresh_token': f"fallback_refresh_{result['user_id']}",
                'token_type': 'bearer',
                'expires_in': 3600,
                'user_id': result['user_id'],
                'user_role': 'student'  # Предполагаем роль по умолчанию
            }
        
        return None
    except Exception as e:
        logger.error(f"Fallback failed for login_with_access_code: {e}")
        return None

async def _fallback_validate_token(token: str) -> Dict[str, Any]:
    """Fallback: простая валидация для fallback токенов"""
    try:
        if token.startswith('fallback_token_'):
            user_id = int(token.replace('fallback_token_', ''))
            return {
                'valid': True,
                'user_id': user_id,
                'user_role': 'student',
                'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                'scopes': []
            }
        
        return {'valid': False, 'error': 'Invalid fallback token'}
    except Exception as e:
        logger.error(f"Fallback failed for validate_token: {e}")
        return {'valid': False, 'error': str(e)}

# === Обёрнутые в fallback функции ===

@with_fallback(_fallback_login_with_access_code)
async def login_with_access_code(
    access_code: str, 
    telegram_id: int,
    username: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Аутентификация по коду доступа с fallback"""
    async with auth_service_client:
        result = await auth_service_client.login_with_access_code(
            access_code, telegram_id, username
        )
        
        if result:
            # Сохраняем токены в менеджере
            token_manager.store_user_tokens(result['user_id'], result)
        
        return result

@with_fallback(_fallback_validate_token)
async def validate_token(token: str) -> Dict[str, Any]:
    """Валидация токена с fallback"""
    async with auth_service_client:
        return await auth_service_client.validate_token(token)

# === Дополнительные функции без fallback ===

async def refresh_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """Обновление токена"""
    async with auth_service_client:
        return await auth_service_client.refresh_token(refresh_token)

async def logout(
    access_token: str, 
    refresh_token: Optional[str] = None
) -> bool:
    """Выход из системы"""
    async with auth_service_client:
        return await auth_service_client.logout(access_token, refresh_token)

async def create_session(
    user_id: int,
    telegram_id: Optional[int] = None,
    expires_in: int = 3600
) -> Optional[str]:
    """Создание сессии"""
    async with auth_service_client:
        return await auth_service_client.create_session(user_id, telegram_id, expires_in)

async def check_permission(
    user_id: int,
    resource: str,
    action: str
) -> bool:
    """Проверка прав доступа"""
    async with auth_service_client:
        return await auth_service_client.check_permission(user_id, resource, action)

async def get_auth_stats() -> Dict[str, Any]:
    """Получение статистики аутентификации"""
    async with auth_service_client:
        return await auth_service_client.get_auth_stats()

async def check_auth_service_health() -> bool:
    """Проверка здоровья Auth Service"""
    async with auth_service_client:
        return await auth_service_client.health_check()

# === Утилиты для интеграции с handlers ===

async def authenticate_user_by_access_code(
    access_code: str, 
    telegram_id: int,
    username: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Полная аутентификация пользователя"""
    try:
        # Логинимся через Auth Service
        auth_result = await login_with_access_code(access_code, telegram_id, username)
        
        if auth_result:
            user_id = auth_result['user_id']
            
            # Создаем сессию
            session_id = await create_session(user_id, telegram_id)
            if session_id:
                auth_result['session_id'] = session_id
            
            logger.info(f"User {user_id} authenticated successfully")
            return auth_result
        
        return None
    except Exception as e:
        logger.error(f"Failed to authenticate user: {e}")
        return None

async def get_user_from_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Получение информации о пользователе из токена"""
    try:
        validation = await validate_token(access_token)
        
        if validation.get('valid'):
            return {
                'user_id': validation['user_id'],
                'user_role': validation.get('user_role'),
                'expires_at': validation.get('expires_at'),
                'scopes': validation.get('scopes', [])
            }
        
        return None
    except Exception as e:
        logger.error(f"Failed to get user from token: {e}")
        return None