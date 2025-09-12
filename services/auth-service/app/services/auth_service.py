# -*- coding: utf-8 -*-
"""
Auth Service - Business Logic
Бизнес-логика для аутентификации и авторизации
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, or_, desc, update
import httpx

from ..models.auth import AuthToken, AccessCode, AuthSession, AuthLog, ApiKey, TokenType
from ..schemas.auth import (
    AccessCodeRequest, LoginResponse, TokenRefreshRequest, TokenValidationResponse,
    LogoutRequest, SessionCreate, ApiKeyCreate, AuthLogCreate, AuthStats
)
from ..core.security import security_manager, hash_string, create_tokens_for_user

class AuthService:
    """Сервис аутентификации и авторизации"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_service_url = "http://user-service:8001"  # URL User Service
    
    async def authenticate_with_access_code(
        self, 
        request: AccessCodeRequest,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[LoginResponse]:
        """
        Аутентификация по коду доступа
        """
        try:
            # Логируем попытку аутентификации
            await self.log_auth_event(
                user_id=None,
                event_type="access_code_attempt",
                success=False,  # Пока что False, изменим если успешно
                details={"access_code": request.access_code[:3] + "***"},
                client_ip=client_ip,
                user_agent=user_agent,
                telegram_id=request.telegram_id
            )
            
            # Проверяем код доступа через User Service
            user_data = await self._validate_access_code_with_user_service(request)
            
            if not user_data or not user_data.get("success"):
                await self.log_auth_event(
                    user_id=None,
                    event_type="access_code_failed",
                    success=False,
                    details={"reason": "invalid_access_code"},
                    client_ip=client_ip,
                    user_agent=user_agent,
                    telegram_id=request.telegram_id
                )
                return None
            
            user_id = user_data["user_id"]
            user_role = user_data.get("user_role", "student")
            
            # Создаем токены
            tokens_data = create_tokens_for_user(user_id, user_role)
            
            # Сохраняем токены в базе
            await self._store_tokens(
                tokens_data, 
                user_id, 
                client_ip, 
                user_agent
            )
            
            # Создаем сессию
            session_data = SessionCreate(
                user_id=user_id,
                telegram_id=request.telegram_id,
                client_ip=client_ip,
                user_agent=user_agent
            )
            await self.create_session(session_data)
            
            # Логируем успешную аутентификацию
            await self.log_auth_event(
                user_id=user_id,
                event_type="access_code_success",
                success=True,
                details={"user_role": user_role},
                client_ip=client_ip,
                user_agent=user_agent,
                telegram_id=request.telegram_id
            )
            
            return LoginResponse(
                access_token=tokens_data["access_token"],
                refresh_token=tokens_data["refresh_token"],
                token_type=tokens_data["token_type"],
                expires_in=tokens_data["expires_in"],
                user_id=user_id,
                user_role=user_role
            )
            
        except Exception as e:
            await self.log_auth_event(
                user_id=None,
                event_type="access_code_error",
                success=False,
                details={"error": str(e)},
                client_ip=client_ip,
                user_agent=user_agent,
                telegram_id=request.telegram_id
            )
            raise
    
    async def refresh_token(
        self, 
        request: TokenRefreshRequest,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[LoginResponse]:
        """
        Обновление токена
        """
        try:
            # Валидируем refresh токен
            payload = security_manager.validate_token(request.refresh_token, "refresh")
            if not payload:
                await self.log_auth_event(
                    user_id=None,
                    event_type="token_refresh_failed",
                    success=False,
                    details={"reason": "invalid_refresh_token"},
                    client_ip=client_ip,
                    user_agent=user_agent
                )
                return None
            
            user_id = int(payload["sub"])
            token_id = payload["jti"]
            
            # Проверяем, что токен не отозван
            result = await self.db.execute(
                select(AuthToken).where(
                    and_(
                        AuthToken.token_id == token_id,
                        AuthToken.user_id == user_id,
                        AuthToken.token_type == TokenType.REFRESH,
                        AuthToken.is_revoked == False
                    )
                )
            )
            stored_token = result.scalar_one_or_none()
            
            if not stored_token:
                await self.log_auth_event(
                    user_id=user_id,
                    event_type="token_refresh_failed",
                    success=False,
                    details={"reason": "token_revoked_or_not_found"},
                    client_ip=client_ip,
                    user_agent=user_agent
                )
                return None
            
            # Получаем информацию о пользователе
            user_info = await self._get_user_info(user_id)
            if not user_info:
                return None
                
            user_role = user_info.get("role", "student")
            
            # Отзываем старый refresh токен
            stored_token.is_revoked = True
            stored_token.revoked_at = datetime.utcnow()
            
            # Создаем новые токены
            tokens_data = create_tokens_for_user(user_id, user_role)
            
            # Сохраняем новые токены
            await self._store_tokens(
                tokens_data, 
                user_id, 
                client_ip, 
                user_agent
            )
            
            await self.db.commit()
            
            # Логируем успешное обновление
            await self.log_auth_event(
                user_id=user_id,
                event_type="token_refresh_success",
                success=True,
                details={"user_role": user_role},
                client_ip=client_ip,
                user_agent=user_agent
            )
            
            return LoginResponse(
                access_token=tokens_data["access_token"],
                refresh_token=tokens_data["refresh_token"],
                token_type=tokens_data["token_type"],
                expires_in=tokens_data["expires_in"],
                user_id=user_id,
                user_role=user_role
            )
            
        except Exception as e:
            await self.log_auth_event(
                user_id=None,
                event_type="token_refresh_error",
                success=False,
                details={"error": str(e)},
                client_ip=client_ip,
                user_agent=user_agent
            )
            raise
    
    async def validate_token(self, token: str) -> TokenValidationResponse:
        """
        Валидация токена
        """
        try:
            # Декодируем токен
            payload = security_manager.validate_token(token, "access")
            if not payload:
                return TokenValidationResponse(
                    valid=False,
                    error="Invalid or expired token"
                )
            
            user_id = int(payload["sub"])
            token_id = payload["jti"]
            
            # Проверяем в базе данных
            result = await self.db.execute(
                select(AuthToken).where(
                    and_(
                        AuthToken.token_id == token_id,
                        AuthToken.user_id == user_id,
                        AuthToken.token_type == TokenType.ACCESS,
                        AuthToken.is_revoked == False
                    )
                )
            )
            stored_token = result.scalar_one_or_none()
            
            if not stored_token:
                return TokenValidationResponse(
                    valid=False,
                    error="Token revoked or not found"
                )
            
            return TokenValidationResponse(
                valid=True,
                user_id=user_id,
                user_role=payload.get("role"),
                expires_at=datetime.fromtimestamp(payload["exp"]),
                scopes=payload.get("scopes", [])
            )
            
        except Exception as e:
            return TokenValidationResponse(
                valid=False,
                error=f"Token validation error: {str(e)}"
            )
    
    async def logout(
        self, 
        request: LogoutRequest,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Выход из системы - отзыв токенов
        """
        try:
            # Получаем user_id из access токена
            payload = security_manager.decode_token(request.token)
            if not payload:
                return False
            
            user_id = int(payload["sub"])
            access_token_id = payload["jti"]
            
            # Отзываем access токен
            await self.db.execute(
                update(AuthToken)
                .where(
                    and_(
                        AuthToken.token_id == access_token_id,
                        AuthToken.user_id == user_id
                    )
                )
                .values(
                    is_revoked=True,
                    revoked_at=datetime.utcnow()
                )
            )
            
            # Отзываем refresh токен если передан
            if request.refresh_token:
                refresh_payload = security_manager.decode_token(request.refresh_token)
                if refresh_payload:
                    refresh_token_id = refresh_payload["jti"]
                    await self.db.execute(
                        update(AuthToken)
                        .where(
                            and_(
                                AuthToken.token_id == refresh_token_id,
                                AuthToken.user_id == user_id
                            )
                        )
                        .values(
                            is_revoked=True,
                            revoked_at=datetime.utcnow()
                        )
                    )
            
            # Деактивируем активные сессии пользователя
            await self.db.execute(
                update(AuthSession)
                .where(
                    and_(
                        AuthSession.user_id == user_id,
                        AuthSession.is_active == True
                    )
                )
                .values(is_active=False)
            )
            
            await self.db.commit()
            
            # Логируем выход
            await self.log_auth_event(
                user_id=user_id,
                event_type="logout",
                success=True,
                client_ip=client_ip,
                user_agent=user_agent
            )
            
            return True
            
        except Exception as e:
            await self.log_auth_event(
                user_id=None,
                event_type="logout_error",
                success=False,
                details={"error": str(e)},
                client_ip=client_ip,
                user_agent=user_agent
            )
            return False
    
    async def create_session(self, session_data: SessionCreate) -> str:
        """
        Создание новой сессии
        """
        session_id = security_manager.create_session_id()
        expires_at = datetime.utcnow() + timedelta(seconds=session_data.expires_in)
        
        session = AuthSession(
            session_id=session_id,
            user_id=session_data.user_id,
            expires_at=expires_at,
            client_ip=session_data.client_ip,
            user_agent=session_data.user_agent,
            telegram_id=session_data.telegram_id
        )
        
        self.db.add(session)
        await self.db.commit()
        
        return session_id
    
    async def create_api_key(
        self, 
        user_id: int, 
        api_key_data: ApiKeyCreate
    ) -> Dict[str, Any]:
        """
        Создание API ключа
        """
        api_key, key_id = security_manager.generate_api_key()
        key_hash = hash_string(api_key)
        
        expires_at = None
        if api_key_data.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=api_key_data.expires_in_days)
        
        db_api_key = ApiKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=api_key_data.name,
            description=api_key_data.description,
            scopes=json.dumps(api_key_data.scopes),
            expires_at=expires_at
        )
        
        self.db.add(db_api_key)
        await self.db.commit()
        await self.db.refresh(db_api_key)
        
        return {
            "api_key": api_key,  # Возвращаем только один раз!
            "key_info": db_api_key
        }
    
    async def get_auth_stats(self) -> AuthStats:
        """
        Получение статистики аутентификации
        """
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        
        # Активные сессии
        active_sessions_result = await self.db.execute(
            select(func.count(AuthSession.id))
            .where(
                and_(
                    AuthSession.is_active == True,
                    AuthSession.expires_at > now
                )
            )
        )
        active_sessions = active_sessions_result.scalar()
        
        # Активные токены
        active_tokens_result = await self.db.execute(
            select(func.count(AuthToken.id))
            .where(
                and_(
                    AuthToken.is_revoked == False,
                    AuthToken.expires_at > now
                )
            )
        )
        active_tokens = active_tokens_result.scalar()
        
        # API ключи
        api_keys_result = await self.db.execute(
            select(func.count(ApiKey.id))
            .where(ApiKey.is_active == True)
        )
        api_keys = api_keys_result.scalar()
        
        # Успешные входы за 24 часа
        successful_logins_result = await self.db.execute(
            select(func.count(AuthLog.id))
            .where(
                and_(
                    AuthLog.event_type.in_(["access_code_success", "token_refresh_success"]),
                    AuthLog.success == True,
                    AuthLog.created_at >= yesterday
                )
            )
        )
        successful_logins = successful_logins_result.scalar()
        
        # Неудачные входы за 24 часа
        failed_logins_result = await self.db.execute(
            select(func.count(AuthLog.id))
            .where(
                and_(
                    AuthLog.event_type.in_(["access_code_failed", "token_refresh_failed"]),
                    AuthLog.success == False,
                    AuthLog.created_at >= yesterday
                )
            )
        )
        failed_logins = failed_logins_result.scalar()
        
        # Уникальные пользователи за 24 часа
        unique_users_result = await self.db.execute(
            select(func.count(func.distinct(AuthLog.user_id)))
            .where(
                and_(
                    AuthLog.user_id.isnot(None),
                    AuthLog.created_at >= yesterday
                )
            )
        )
        unique_users = unique_users_result.scalar()
        
        return AuthStats(
            total_active_sessions=active_sessions,
            total_active_tokens=active_tokens,
            total_api_keys=api_keys,
            successful_logins_24h=successful_logins,
            failed_logins_24h=failed_logins,
            unique_users_24h=unique_users
        )
    
    async def log_auth_event(
        self,
        user_id: Optional[int],
        event_type: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        telegram_id: Optional[int] = None
    ):
        """
        Логирование события аутентификации
        """
        log_entry = AuthLog(
            user_id=user_id,
            event_type=event_type,
            success=success,
            details=json.dumps(details) if details else None,
            error_message=error_message,
            client_ip=client_ip,
            user_agent=user_agent,
            telegram_id=telegram_id
        )
        
        self.db.add(log_entry)
        await self.db.commit()
    
    async def _validate_access_code_with_user_service(
        self, 
        request: AccessCodeRequest
    ) -> Optional[Dict[str, Any]]:
        """
        Валидация кода доступа через User Service
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.user_service_url}/api/v1/users/validate-access-code",
                    json={
                        "access_code": request.access_code,
                        "telegram_id": request.telegram_id,
                        "username": request.username
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        # Получаем дополнительную информацию о пользователе
                        user_info = await self._get_user_info(data["user_id"])
                        if user_info:
                            data["user_role"] = user_info.get("role", "student")
                        return data
                
                return None
                
        except Exception as e:
            print(f"Error calling User Service: {e}")
            return None
    
    async def _get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение информации о пользователе из User Service
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.user_service_url}/api/v1/users/{user_id}",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    return response.json()
                
                return None
                
        except Exception as e:
            print(f"Error fetching user info: {e}")
            return None
    
    async def _store_tokens(
        self, 
        tokens_data: Dict[str, Any], 
        user_id: int,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Сохранение токенов в базе данных
        """
        # Access токен
        access_token = AuthToken(
            token_id=tokens_data["access_token_id"],
            user_id=user_id,
            token_type=TokenType.ACCESS,
            token_hash=hash_string(tokens_data["access_token"]),
            issued_at=datetime.utcnow(),
            expires_at=tokens_data["access_expires_at"],
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        # Refresh токен
        refresh_token = AuthToken(
            token_id=tokens_data["refresh_token_id"],
            user_id=user_id,
            token_type=TokenType.REFRESH,
            token_hash=hash_string(tokens_data["refresh_token"]),
            issued_at=datetime.utcnow(),
            expires_at=tokens_data["refresh_expires_at"],
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        self.db.add(access_token)
        self.db.add(refresh_token)
        await self.db.commit()