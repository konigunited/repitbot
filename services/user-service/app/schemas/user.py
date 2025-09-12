# -*- coding: utf-8 -*-
"""
User Service - Pydantic Schemas
Схемы для валидации и сериализации данных пользователей
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class UserRole(str, Enum):
    TUTOR = "tutor"
    STUDENT = "student"
    PARENT = "parent"

class UserBase(BaseModel):
    """Базовая схема пользователя"""
    full_name: str = Field(..., min_length=2, max_length=100, description="Полное имя пользователя")
    role: UserRole = Field(..., description="Роль пользователя")
    telegram_id: Optional[int] = Field(None, description="Telegram ID пользователя")
    username: Optional[str] = Field(None, max_length=50, description="Username в Telegram")

class UserCreate(UserBase):
    """Схема для создания пользователя"""
    access_code: Optional[str] = Field(None, min_length=6, max_length=10, description="Код доступа")
    parent_id: Optional[int] = Field(None, description="ID родителя (для учеников)")
    second_parent_id: Optional[int] = Field(None, description="ID второго родителя")

class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    telegram_id: Optional[int] = None
    username: Optional[str] = Field(None, max_length=50)
    points: Optional[int] = Field(None, ge=0)
    streak_days: Optional[int] = Field(None, ge=0)
    total_study_hours: Optional[int] = Field(None, ge=0)
    parent_id: Optional[int] = None
    second_parent_id: Optional[int] = None

class UserInDB(UserBase):
    """Схема пользователя в базе данных"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    access_code: str
    points: int = 0
    streak_days: int = 0
    total_study_hours: int = 0
    parent_id: Optional[int] = None
    second_parent_id: Optional[int] = None
    last_lesson_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class User(UserInDB):
    """Публичная схема пользователя"""
    pass

class UserWithChildren(User):
    """Пользователь с детьми (для родителей)"""
    children: List[User] = []

class UserStats(BaseModel):
    """Статистика пользователя"""
    total_users: int
    total_students: int
    total_parents: int
    total_tutors: int
    active_users_last_7_days: int
    active_users_last_30_days: int

class UserListResponse(BaseModel):
    """Ответ со списком пользователей"""
    users: List[User]
    total: int
    page: int
    size: int
    pages: int

class AccessCodeValidationRequest(BaseModel):
    """Запрос на валидацию кода доступа"""
    access_code: str = Field(..., min_length=6, max_length=10)
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    username: Optional[str] = Field(None, max_length=50)

class AccessCodeValidationResponse(BaseModel):
    """Ответ на валидацию кода доступа"""
    success: bool
    user_id: Optional[int] = None
    message: str

class UserPointsUpdate(BaseModel):
    """Обновление баллов пользователя"""
    points_to_add: int = Field(..., description="Количество баллов для добавления")
    reason: Optional[str] = Field(None, description="Причина начисления баллов")

class UserStreakUpdate(BaseModel):
    """Обновление streak дней"""
    lesson_date: datetime = Field(..., description="Дата урока")

class BulkUserUpdate(BaseModel):
    """Массовое обновление пользователей"""
    user_ids: List[int] = Field(..., description="Список ID пользователей")
    update_data: UserUpdate = Field(..., description="Данные для обновления")

class HealthCheckResponse(BaseModel):
    """Ответ health check"""
    status: str = "healthy"
    timestamp: datetime
    version: str = "1.0.0"
    database_status: str = "connected"