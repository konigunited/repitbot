# -*- coding: utf-8 -*-
"""
REST API endpoints для управления уроками.
Реализует полный CRUD для уроков, расписания и посещаемости.
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...services.lesson_service import LessonService
from ...schemas.lesson import (
    LessonCreate, LessonUpdate, LessonReschedule, LessonCancel,
    LessonResponse, LessonListResponse, LessonFilter,
    AttendanceCreate, AttendanceResponse,
    ScheduleCreate, ScheduleUpdate, ScheduleResponse,
    LessonStats, StudentLessonStats,
    BulkLessonCreate, BulkOperationResponse
)
from ...events.lesson_events import LessonEventPublisher

logger = logging.getLogger(__name__)

router = APIRouter()


def get_lesson_service() -> LessonService:
    """Dependency для получения lesson service."""
    # В реальном приложении здесь будет injection event_publisher
    return LessonService()


def get_current_user_id() -> int:
    """
    Dependency для получения ID текущего пользователя.
    В реальном приложении здесь будет JWT декодирование.
    """
    # TODO: Реализовать JWT аутентификацию
    return 1  # Заглушка


@router.post("/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson_data: LessonCreate,
    current_user: int = Depends(get_current_user_id),
    lesson_service: LessonService = Depends(get_lesson_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание нового урока.
    
    Создает урок с указанными параметрами и отправляет событие о создании.
    """
    try:
        lesson = await lesson_service.create_lesson(lesson_data, current_user, db)
        return LessonResponse.from_orm(lesson)
    except Exception as e:
        logger.error(f"Failed to create lesson: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lesson: {str(e)}"
        )


@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: int,
    lesson_service: LessonService = Depends(get_lesson_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение урока по ID.
    
    Возвращает детальную информацию об уроке.
    """
    lesson = await lesson_service.get_lesson_by_id(lesson_id, db)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with ID {lesson_id} not found"
        )
    
    return LessonResponse.from_orm(lesson)


@router.put("/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    lesson_data: LessonUpdate,
    current_user: int = Depends(get_current_user_id),
    lesson_service: LessonService = Depends(get_lesson_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление урока.
    
    Обновляет информацию об уроке и отправляет событие об обновлении.
    """
    try:
        lesson = await lesson_service.update_lesson(lesson_id, lesson_data, current_user, db)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with ID {lesson_id} not found"
            )
        
        return LessonResponse.from_orm(lesson)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update lesson {lesson_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lesson: {str(e)}"
        )


@router.post("/lessons/{lesson_id}/reschedule", response_model=LessonResponse)
async def reschedule_lesson(
    lesson_id: int,
    reschedule_data: LessonReschedule,
    current_user: int = Depends(get_current_user_id),
    lesson_service: LessonService = Depends(get_lesson_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Перенос урока на новую дату.
    
    Переносит урок, сохраняя историю изменений.
    """
    try:
        lesson = await lesson_service.reschedule_lesson(lesson_id, reschedule_data, current_user, db)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with ID {lesson_id} not found"
            )
        
        return LessonResponse.from_orm(lesson)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reschedule lesson {lesson_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reschedule lesson: {str(e)}"
        )


@router.post("/lessons/{lesson_id}/cancel", response_model=LessonResponse)
async def cancel_lesson(
    lesson_id: int,
    cancel_data: LessonCancel,
    current_user: int = Depends(get_current_user_id),
    lesson_service: LessonService = Depends(get_lesson_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Отмена урока.
    
    Отменяет урок и выполняет логику сдвига будущих уроков.
    """
    try:
        lesson = await lesson_service.cancel_lesson(lesson_id, cancel_data, current_user, db)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with ID {lesson_id} not found"
            )
        
        return LessonResponse.from_orm(lesson)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel lesson {lesson_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel lesson: {str(e)}"
        )


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: int,
    lesson_service: LessonService = Depends(get_lesson_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление урока.
    
    Полностью удаляет урок из системы.
    """
    try:
        success = await lesson_service.delete_lesson(lesson_id, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with ID {lesson_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete lesson {lesson_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lesson: {str(e)}"
        )


@router.get("/lessons", response_model=LessonListResponse)
async def get_lessons(
    student_id: Optional[int] = Query(None, description="ID студента"),
    tutor_id: Optional[int] = Query(None, description="ID репетитора"),
    date_from: Optional[datetime] = Query(None, description="Дата начала периода"),
    date_to: Optional[datetime] = Query(None, description="Дата окончания периода"),
    lesson_status: Optional[str] = Query(None, description="Статус урока"),
    attendance_status: Optional[str] = Query(None, description="Статус посещения"),
    mastery_level: Optional[str] = Query(None, description="Уровень освоения"),
    topic_search: Optional[str] = Query(None, description="Поиск по теме"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    sort_by: str = Query("date", description="Поле для сортировки"),
    sort_order: str = Query("asc", description="Порядок сортировки"),
    lesson_service: LessonService = Depends(get_lesson_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка уроков с фильтрацией и пагинацией.
    
    Поддерживает различные фильтры и сортировку.
    """
    try:
        # Создание фильтра из query параметров
        filters = LessonFilter(
            student_id=student_id,
            tutor_id=tutor_id,
            date_from=date_from,
            date_to=date_to,
            lesson_status=lesson_status,
            attendance_status=attendance_status,
            mastery_level=mastery_level,
            topic_search=topic_search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        lessons, total = await lesson_service.get_lessons(filters, db)
        
        # Расчет количества страниц
        total_pages = (total + page_size - 1) // page_size
        
        return LessonListResponse(
            lessons=[LessonResponse.from_orm(lesson) for lesson in lessons],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Failed to get lessons: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lessons: {str(e)}"
        )


@router.post("/lessons/{lesson_id}/attendance", response_model=AttendanceResponse)
async def mark_attendance(
    lesson_id: int,
    attendance_data: AttendanceCreate,
    current_user: int = Depends(get_current_user_id),
    lesson_service: LessonService = Depends(get_lesson_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Отметка посещаемости урока.
    
    Записывает детальную информацию о посещении урока.
    """
    try:
        attendance = await lesson_service.mark_attendance(lesson_id, attendance_data, current_user, db)
        if not attendance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with ID {lesson_id} not found"
            )
        
        return AttendanceResponse.from_orm(attendance)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark attendance for lesson {lesson_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark attendance: {str(e)}"
        )


@router.get("/lessons/stats", response_model=LessonStats)
async def get_lesson_statistics(
    student_id: Optional[int] = Query(None, description="ID студента"),
    date_from: Optional[datetime] = Query(None, description="Дата начала периода"),
    date_to: Optional[datetime] = Query(None, description="Дата окончания периода"),
    lesson_service: LessonService = Depends(get_lesson_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение статистики по урокам.
    
    Возвращает агрегированную статистику для указанного периода и студента.
    """
    try:
        stats = await lesson_service.get_lesson_stats(student_id, date_from, date_to, db)
        return stats
    except Exception as e:
        logger.error(f"Failed to get lesson statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.post("/lessons/bulk", response_model=BulkOperationResponse)
async def create_lessons_bulk(
    bulk_data: BulkLessonCreate,
    current_user: int = Depends(get_current_user_id),
    lesson_service: LessonService = Depends(get_lesson_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Массовое создание уроков.
    
    Создает несколько уроков за одну операцию.
    """
    try:
        created_ids = []
        errors = []
        success_count = 0
        error_count = 0
        
        for i, lesson_data in enumerate(bulk_data.lessons):
            try:
                lesson = await lesson_service.create_lesson(lesson_data, current_user, db)
                created_ids.append(lesson.id)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({
                    "index": i,
                    "lesson_data": lesson_data.dict(),
                    "error": str(e)
                })
                logger.error(f"Failed to create lesson {i}: {e}")
        
        return BulkOperationResponse(
            success_count=success_count,
            error_count=error_count,
            created_ids=created_ids,
            errors=errors
        )
    except Exception as e:
        logger.error(f"Failed bulk lesson creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lessons: {str(e)}"
        )


# Дополнительные endpoints для расписания
@router.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: int = Depends(get_current_user_id),
    # schedule_service: ScheduleService = Depends(get_schedule_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание расписания уроков.
    
    TODO: Реализовать ScheduleService для управления автоматическим созданием уроков.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Schedule management not implemented yet"
    )


@router.get("/schedules", response_model=List[ScheduleResponse])
async def get_schedules(
    student_id: Optional[int] = Query(None),
    tutor_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка расписаний.
    
    TODO: Реализовать получение расписаний с фильтрацией.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Schedule listing not implemented yet"
    )


# Health check для сервиса
@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint для проверки состояния сервиса."""
    try:
        # Простая проверка подключения к БД
        await db.execute("SELECT 1")
        return {"status": "healthy", "service": "lesson-service"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )