# -*- coding: utf-8 -*-
"""
User Service - REST API Endpoints
API для управления пользователями
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...services.user_service import UserService
from ...schemas.user import (
    User, UserCreate, UserUpdate, UserInDB, UserWithChildren,
    UserListResponse, AccessCodeValidationRequest, AccessCodeValidationResponse,
    UserPointsUpdate, UserStreakUpdate, UserStats, HealthCheckResponse,
    UserRole
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])

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

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание нового пользователя"""
    try:
        user_service = UserService(db)
        user = await user_service.create_user(user_data)
        return User.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@router.get("/", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    role: Optional[UserRole] = Query(None, description="Фильтр по роли"),
    search: Optional[str] = Query(None, description="Поиск по имени"),
    db: AsyncSession = Depends(get_db)
):
    """Получение списка пользователей с пагинацией"""
    try:
        user_service = UserService(db)
        users, total = await user_service.get_users_with_pagination(
            page=page, size=size, role=role, search=search
        )
        
        pages = (total + size - 1) // size  # Ceil division
        
        return UserListResponse(
            users=[User.model_validate(user) for user in users],
            total=total,
            page=page,
            size=size,
            pages=pages
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )

@router.get("/stats", response_model=UserStats)
async def get_user_stats(db: AsyncSession = Depends(get_db)):
    """Получение статистики пользователей"""
    try:
        user_service = UserService(db)
        stats = await user_service.get_user_stats()
        return UserStats(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user stats: {str(e)}"
        )

@router.get("/parents-with-children", response_model=List[UserWithChildren])
async def get_parents_with_children(db: AsyncSession = Depends(get_db)):
    """Получение родителей со списком их детей"""
    try:
        user_service = UserService(db)
        return await user_service.get_parents_with_children()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch parents with children: {str(e)}"
        )

@router.get("/by-role/{role}", response_model=List[User])
async def get_users_by_role(
    role: UserRole,
    db: AsyncSession = Depends(get_db)
):
    """Получение пользователей по роли"""
    try:
        user_service = UserService(db)
        users = await user_service.get_users_by_role(role)
        return [User.model_validate(user) for user in users]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users by role: {str(e)}"
        )

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение пользователя по ID"""
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        return User.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user: {str(e)}"
        )

@router.get("/telegram/{telegram_id}", response_model=User)
async def get_user_by_telegram_id(
    telegram_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение пользователя по Telegram ID"""
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram_id(telegram_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with telegram_id {telegram_id} not found"
            )
        
        return User.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user by telegram_id: {str(e)}"
        )

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление пользователя"""
    try:
        user_service = UserService(db)
        user = await user_service.update_user(user_id, user_update)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        return User.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удаление пользователя"""
    try:
        user_service = UserService(db)
        success = await user_service.delete_user(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )

@router.post("/validate-access-code", response_model=AccessCodeValidationResponse)
async def validate_access_code(
    request: AccessCodeValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Валидация кода доступа и привязка Telegram аккаунта"""
    try:
        user_service = UserService(db)
        result = await user_service.validate_access_code(request)
        return AccessCodeValidationResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate access code: {str(e)}"
        )

@router.post("/{user_id}/points", response_model=User)
async def update_user_points(
    user_id: int,
    points_update: UserPointsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление баллов пользователя"""
    try:
        user_service = UserService(db)
        user = await user_service.update_user_points(user_id, points_update)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        return User.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user points: {str(e)}"
        )

@router.post("/{user_id}/streak", response_model=User)
async def update_user_streak(
    user_id: int,
    streak_update: UserStreakUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление streak дней пользователя"""
    try:
        user_service = UserService(db)
        user = await user_service.update_user_streak(user_id, streak_update)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        return User.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user streak: {str(e)}"
        )

@router.get("/{user_id}/activity", response_model=List[dict])
async def get_user_activity_log(
    user_id: int,
    limit: int = Query(50, ge=1, le=200, description="Количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получение журнала активности пользователя"""
    try:
        user_service = UserService(db)
        
        # Проверяем существование пользователя
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        return await user_service.get_user_activity_log(user_id, limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user activity log: {str(e)}"
        )