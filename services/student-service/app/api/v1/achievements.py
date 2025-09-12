# -*- coding: utf-8 -*-
"""
Achievements API Endpoints
API для работы с системой достижений
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Optional
import logging

from ...services.achievement_service import AchievementService
from ...schemas import (
    AchievementCreate,
    AchievementUpdate,
    AchievementResponse,
    StudentAchievementResponse,
    AchievementUnlocked,
    AchievementFilters,
    AchievementStats,
    AchievementTypeEnum,
    AchievementRarityEnum
)

router = APIRouter(prefix="/achievements", tags=["achievements"])
logger = logging.getLogger(__name__)

# Dependency для получения сервиса
def get_achievement_service() -> AchievementService:
    return AchievementService()

# ============== CRUD для достижений ==============

@router.post("/", response_model=AchievementResponse, status_code=status.HTTP_201_CREATED)
async def create_achievement(
    achievement_data: AchievementCreate,
    service: AchievementService = Depends(get_achievement_service)
):
    """Создание нового достижения"""
    try:
        achievement = await service.create_achievement(achievement_data)
        return achievement
    except Exception as e:
        logger.error(f"Error creating achievement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create achievement"
        )

@router.get("/", response_model=List[AchievementResponse])
async def get_achievements(
    type: Optional[AchievementTypeEnum] = Query(None, description="Тип достижения"),
    rarity: Optional[AchievementRarityEnum] = Query(None, description="Редкость достижения"),
    is_active: Optional[bool] = Query(None, description="Активные достижения"),
    is_hidden: Optional[bool] = Query(None, description="Скрытые достижения"),
    service: AchievementService = Depends(get_achievement_service)
):
    """Получение списка достижений с фильтрами"""
    try:
        filters = AchievementFilters(
            type=type,
            rarity=rarity,
            is_active=is_active,
            is_hidden=is_hidden
        )
        achievements = await service.get_achievements(filters)
        return achievements
    except Exception as e:
        logger.error(f"Error getting achievements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get achievements"
        )

@router.get("/{achievement_id}", response_model=AchievementResponse)
async def get_achievement(
    achievement_id: int,
    service: AchievementService = Depends(get_achievement_service)
):
    """Получение достижения по ID"""
    try:
        achievement = await service.get_achievement(achievement_id)
        if not achievement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Achievement not found"
            )
        return achievement
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting achievement {achievement_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get achievement"
        )

@router.put("/{achievement_id}", response_model=AchievementResponse)
async def update_achievement(
    achievement_id: int,
    achievement_data: AchievementUpdate,
    service: AchievementService = Depends(get_achievement_service)
):
    """Обновление достижения"""
    try:
        achievement = await service.update_achievement(achievement_id, achievement_data)
        if not achievement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Achievement not found"
            )
        return achievement
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating achievement {achievement_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update achievement"
        )

@router.delete("/{achievement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_achievement(
    achievement_id: int,
    service: AchievementService = Depends(get_achievement_service)
):
    """Удаление достижения"""
    try:
        success = await service.delete_achievement(achievement_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Achievement not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting achievement {achievement_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete achievement"
        )

# ============== Работа с достижениями студентов ==============

@router.get("/students/{student_id}", response_model=List[StudentAchievementResponse])
async def get_student_achievements(
    student_id: int,
    service: AchievementService = Depends(get_achievement_service)
):
    """Получение достижений студента"""
    try:
        achievements = await service.get_student_achievements(student_id)
        return achievements
    except Exception as e:
        logger.error(f"Error getting achievements for student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get student achievements"
        )

@router.post("/students/{student_id}/check", response_model=List[AchievementUnlocked])
async def check_student_achievements(
    student_id: int,
    service: AchievementService = Depends(get_achievement_service)
):
    """Проверка и начисление достижений для студента"""
    try:
        unlocked = await service.check_achievements_for_student(student_id)
        return unlocked
    except Exception as e:
        logger.error(f"Error checking achievements for student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check achievements"
        )

@router.get("/students/{student_id}/stats", response_model=AchievementStats)
async def get_student_achievement_stats(
    student_id: int,
    service: AchievementService = Depends(get_achievement_service)
):
    """Получение статистики достижений студента"""
    try:
        stats = await service.get_achievement_stats(student_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting achievement stats for student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get achievement stats"
        )

# ============== Специальные endpoints ==============

@router.post("/initialize-defaults")
async def initialize_default_achievements(
    service: AchievementService = Depends(get_achievement_service)
):
    """Инициализация стандартных достижений (для администраторов)"""
    try:
        await service.initialize_default_achievements()
        return {"status": "success", "message": "Default achievements initialized"}
    except Exception as e:
        logger.error(f"Error initializing default achievements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize default achievements"
        )

@router.get("/types", response_model=List[str])
async def get_achievement_types():
    """Получение списка типов достижений"""
    return [type.value for type in AchievementTypeEnum]

@router.get("/rarities", response_model=List[str])
async def get_achievement_rarities():
    """Получение списка редкостей достижений"""
    return [rarity.value for rarity in AchievementRarityEnum]

# ============== Endpoints для событий ==============

@router.post("/events/lesson-completed/{student_id}")
async def handle_lesson_completed_achievement_check(
    student_id: int,
    event_data: dict,
    service: AchievementService = Depends(get_achievement_service)
):
    """Проверка достижений при завершении урока"""
    try:
        unlocked = await service.check_achievements_for_student(student_id)
        
        return {
            "status": "success",
            "achievements_unlocked": len(unlocked),
            "unlocked": unlocked
        }
    except Exception as e:
        logger.error(f"Error checking achievements for lesson completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check achievements"
        )

@router.post("/events/homework-submitted/{student_id}")
async def handle_homework_submitted_achievement_check(
    student_id: int,
    event_data: dict,
    service: AchievementService = Depends(get_achievement_service)
):
    """Проверка достижений при сдаче домашнего задания"""
    try:
        unlocked = await service.check_achievements_for_student(student_id)
        
        return {
            "status": "success",
            "achievements_unlocked": len(unlocked),
            "unlocked": unlocked
        }
    except Exception as e:
        logger.error(f"Error checking achievements for homework submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check achievements"
        )

@router.post("/events/level-up/{student_id}")
async def handle_level_up_achievement_check(
    student_id: int,
    event_data: dict,
    service: AchievementService = Depends(get_achievement_service)
):
    """Проверка достижений при повышении уровня"""
    try:
        unlocked = await service.check_achievements_for_student(student_id)
        
        return {
            "status": "success",
            "achievements_unlocked": len(unlocked),
            "unlocked": unlocked
        }
    except Exception as e:
        logger.error(f"Error checking achievements for level up: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check achievements"
        )