# -*- coding: utf-8 -*-
"""
Students API Endpoints
API для работы со студентами
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Optional
import logging

from ...services.student_service import StudentService
from ...schemas import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentSummary,
    XPTransaction,
    LevelUpResponse,
    StudentSearchFilters,
    StudentDashboard,
    StudentProfileUpdate,
    StudentPreferences
)

router = APIRouter(prefix="/students", tags=["students"])
logger = logging.getLogger(__name__)

# Dependency для получения сервиса
def get_student_service() -> StudentService:
    return StudentService()

@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_data: StudentCreate,
    service: StudentService = Depends(get_student_service)
):
    """Создание нового студента"""
    try:
        student = await service.create_student(student_data)
        return student
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating student: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create student"
        )

@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: int,
    service: StudentService = Depends(get_student_service)
):
    """Получение студента по ID"""
    try:
        student = await service.get_student_by_id(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        return student
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get student"
        )

@router.get("/by-user/{user_id}", response_model=StudentResponse)
async def get_student_by_user_id(
    user_id: int,
    service: StudentService = Depends(get_student_service)
):
    """Получение студента по user_id"""
    try:
        student = await service.get_student_by_user_id(user_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        return student
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting student by user_id {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get student"
        )

@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: int,
    student_data: StudentUpdate,
    service: StudentService = Depends(get_student_service)
):
    """Обновление данных студента"""
    try:
        student = await service.update_student(student_id, student_data)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        return student
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update student"
        )

@router.patch("/{student_id}/profile", response_model=StudentResponse)
async def update_student_profile(
    student_id: int,
    profile_data: StudentProfileUpdate,
    service: StudentService = Depends(get_student_service)
):
    """Обновление профиля студента"""
    try:
        # Преобразуем в StudentUpdate
        student_update = StudentUpdate(**profile_data.model_dump(exclude_unset=True))
        student = await service.update_student(student_id, student_update)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        return student
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating student profile {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: int,
    service: StudentService = Depends(get_student_service)
):
    """Удаление студента (мягкое удаление)"""
    try:
        success = await service.delete_student(student_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete student"
        )

@router.get("/", response_model=List[StudentSummary])
async def search_students(
    level_min: Optional[int] = Query(None, description="Минимальный уровень"),
    level_max: Optional[int] = Query(None, description="Максимальный уровень"),
    is_premium: Optional[bool] = Query(None, description="Премиум статус"),
    is_active: Optional[bool] = Query(None, description="Активность"),
    has_streak: Optional[bool] = Query(None, description="Наличие стрика"),
    limit: int = Query(50, le=100, description="Количество результатов"),
    offset: int = Query(0, ge=0, description="Смещение"),
    service: StudentService = Depends(get_student_service)
):
    """Поиск студентов с фильтрами"""
    try:
        filters = StudentSearchFilters(
            level_min=level_min,
            level_max=level_max,
            is_premium=is_premium,
            is_active=is_active,
            has_streak=has_streak
        )
        
        students = await service.search_students(filters, limit, offset)
        return students
    except Exception as e:
        logger.error(f"Error searching students: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search students"
        )

@router.post("/{student_id}/experience", response_model=Optional[LevelUpResponse])
async def add_experience(
    student_id: int,
    xp_transaction: XPTransaction,
    service: StudentService = Depends(get_student_service)
):
    """Добавление опыта студенту"""
    try:
        level_up_response = await service.add_experience(student_id, xp_transaction)
        return level_up_response
    except Exception as e:
        logger.error(f"Error adding XP to student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add experience"
        )

@router.patch("/{student_id}/stats")
async def update_student_stats(
    student_id: int,
    stats_update: dict,
    service: StudentService = Depends(get_student_service)
):
    """Обновление статистики студента"""
    try:
        success = await service.update_student_stats(student_id, stats_update)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        return {"status": "success", "message": "Stats updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating student stats {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update stats"
        )

@router.get("/{student_id}/dashboard", response_model=StudentDashboard)
async def get_student_dashboard(
    student_id: int,
    service: StudentService = Depends(get_student_service)
):
    """Получение дашборда студента"""
    try:
        dashboard = await service.get_student_dashboard(student_id)
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard for student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard"
        )

# Специальные endpoints для геймификации
@router.post("/{student_id}/level-up", response_model=Optional[LevelUpResponse])
async def trigger_level_check(
    student_id: int,
    service: StudentService = Depends(get_student_service)
):
    """Принудительная проверка возможности повышения уровня"""
    try:
        # Добавляем 0 XP для запуска проверки уровня
        xp_transaction = XPTransaction(
            amount=0,
            reason="Level check",
            category="system"
        )
        level_up_response = await service.add_experience(student_id, xp_transaction)
        return level_up_response
    except Exception as e:
        logger.error(f"Error checking level for student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check level"
        )

# Endpoints для событий от других сервисов
@router.post("/{student_id}/events/lesson-completed")
async def handle_lesson_completed_event(
    student_id: int,
    event_data: dict,
    service: StudentService = Depends(get_student_service)
):
    """Обработка события завершения урока"""
    try:
        # Обновляем статистику
        stats_update = {"lessons_completed": 1}
        await service.update_student_stats(student_id, stats_update)
        
        # Начисляем XP
        xp_transaction = XPTransaction(
            amount=100,  # Стандартные очки за урок
            reason="Lesson completed",
            category="lesson",
            metadata=event_data
        )
        level_up_response = await service.add_experience(student_id, xp_transaction)
        
        return {
            "status": "success",
            "message": "Lesson completion processed",
            "level_up": level_up_response is not None
        }
    except Exception as e:
        logger.error(f"Error handling lesson completed event for student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process lesson completion"
        )

@router.post("/{student_id}/events/homework-submitted")
async def handle_homework_submitted_event(
    student_id: int,
    event_data: dict,
    service: StudentService = Depends(get_student_service)
):
    """Обработка события сдачи домашнего задания"""
    try:
        # Обновляем статистику
        stats_update = {"homework_submitted": 1}
        
        # Проверяем оценку
        score = event_data.get("score", 0)
        if score >= 90:  # Идеальная работа
            stats_update["homework_perfect"] = 1
        
        await service.update_student_stats(student_id, stats_update)
        
        # Начисляем XP
        base_xp = 50
        bonus_xp = 100 if score >= 90 else 0
        total_xp = base_xp + bonus_xp
        
        xp_transaction = XPTransaction(
            amount=total_xp,
            reason=f"Homework submitted (score: {score})",
            category="homework",
            metadata=event_data
        )
        level_up_response = await service.add_experience(student_id, xp_transaction)
        
        return {
            "status": "success",
            "message": "Homework submission processed",
            "xp_earned": total_xp,
            "level_up": level_up_response is not None
        }
    except Exception as e:
        logger.error(f"Error handling homework submitted event for student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process homework submission"
        )