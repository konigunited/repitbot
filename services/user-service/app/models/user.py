# -*- coding: utf-8 -*-
"""
User Service - SQLAlchemy Models
Микросервис управления пользователями
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SAEnum, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class UserRole(enum.Enum):
    TUTOR = "tutor"
    STUDENT = "student"
    PARENT = "parent"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=True, index=True)
    username = Column(String, unique=True, nullable=True)
    full_name = Column(String, nullable=False, index=True)
    role = Column(SAEnum(UserRole), nullable=False, index=True)
    access_code = Column(String, unique=True, nullable=False, index=True)
    
    # Gamification fields
    points = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    last_lesson_date = Column(DateTime, nullable=True)
    total_study_hours = Column(Integer, default=0)  # в минутах
    
    # Parent-child relationships
    parent_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    second_parent_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    parent = relationship("User", remote_side=[id], foreign_keys=[parent_id], back_populates="children")
    second_parent = relationship("User", remote_side=[id], foreign_keys=[second_parent_id])
    children = relationship("User", back_populates="parent", foreign_keys=[parent_id])
    
    def __repr__(self):
        return f"<User(id={self.id}, full_name='{self.full_name}', role='{self.role.value}')>"

class UserSession(Base):
    """Сессии пользователей для аудита"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationship
    user = relationship("User", foreign_keys=[user_id])

class UserActivity(Base):
    """Журнал активности пользователей"""
    __tablename__ = 'user_activities'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String, nullable=False)
    details = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", foreign_keys=[user_id])