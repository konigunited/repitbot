# -*- coding: utf-8 -*-
"""
Auth Service - SQLAlchemy Models
Микросервис аутентификации и авторизации
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum as SAEnum
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class TokenType(enum.Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"

class AuthToken(Base):
    """Модель для JWT токенов"""
    __tablename__ = 'auth_tokens'
    
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(String, unique=True, nullable=False, index=True)  # jti claim
    user_id = Column(Integer, nullable=False, index=True)
    token_type = Column(SAEnum(TokenType), nullable=False)
    token_hash = Column(String, nullable=False)  # Hash токена для безопасности
    
    # Время жизни токена
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Метаданные
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Информация о клиенте
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<AuthToken(id={self.id}, user_id={self.user_id}, type={self.token_type.value}, expired={self.expires_at < datetime.utcnow()})>"

class AccessCode(Base):
    """Модель для кодов доступа"""
    __tablename__ = 'access_codes'
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Статус использования
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)
    used_by_telegram_id = Column(Integer, nullable=True)
    
    # Время жизни кода
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime, nullable=True)  # Коды могут не истекать
    
    # Метаданные
    description = Column(String, nullable=True)  # Описание для чего создан код
    max_uses = Column(Integer, default=1)  # Максимальное количество использований
    use_count = Column(Integer, default=0)  # Количество использований
    
    def __repr__(self):
        return f"<AccessCode(code={self.code}, user_id={self.user_id}, used={self.is_used})>"

class AuthSession(Base):
    """Модель для сессий аутентификации"""
    __tablename__ = 'auth_sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Статус сессии
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Время жизни сессии
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Информация о клиенте
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    telegram_id = Column(Integer, nullable=True)
    
    # Дополнительные данные сессии
    session_data = Column(Text, nullable=True)  # JSON данные
    
    def __repr__(self):
        return f"<AuthSession(session_id={self.session_id}, user_id={self.user_id}, active={self.is_active})>"

class AuthLog(Base):
    """Журнал аутентификации"""
    __tablename__ = 'auth_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # Может быть NULL для неудачных попыток
    
    # Тип события
    event_type = Column(String, nullable=False, index=True)  # login, logout, token_refresh, access_denied, etc.
    
    # Детали события
    success = Column(Boolean, nullable=False)
    details = Column(Text, nullable=True)  # JSON с деталями
    error_message = Column(String, nullable=True)
    
    # Метаданные запроса
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    telegram_id = Column(Integer, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AuthLog(event={self.event_type}, user_id={self.user_id}, success={self.success})>"

class ApiKey(Base):
    """Модель для API ключей"""
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String, unique=True, nullable=False, index=True)
    key_hash = Column(String, nullable=False)  # Hash ключа
    
    # Владелец ключа
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False)  # Название ключа
    description = Column(String, nullable=True)
    
    # Права доступа
    scopes = Column(Text, nullable=True)  # JSON список разрешений
    
    # Статус
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Время жизни
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime, nullable=True)  # Может не истекать
    last_used = Column(DateTime, nullable=True)
    
    # Статистика использования
    use_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<ApiKey(key_id={self.key_id}, user_id={self.user_id}, active={self.is_active})>"