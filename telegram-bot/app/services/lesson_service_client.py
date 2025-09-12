# -*- coding: utf-8 -*-
"""
HTTP клиент для взаимодействия с Lesson Service.
Обеспечивает интеграцию Telegram Bot с микросервисом уроков.
"""

import logging
import httpx
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LessonData:
    """Данные урока для создания."""
    topic: str
    date: datetime
    student_id: int
    tutor_id: Optional[int] = None
    duration_minutes: int = 60
    skills_developed: Optional[str] = None
    notes: Optional[str] = None
    room_url: Optional[str] = None


@dataclass 
class LessonResponse:
    """Ответ от Lesson Service."""
    id: int
    topic: str
    date: datetime
    student_id: int
    tutor_id: Optional[int]
    duration_minutes: int
    attendance_status: str
    lesson_status: str
    is_attended: bool
    mastery_level: str
    skills_developed: Optional[str]
    mastery_comment: Optional[str]
    notes: Optional[str]
    created_at: datetime


class LessonServiceClient:
    """HTTP клиент для Lesson Service."""
    
    def __init__(self, base_url: str = "http://localhost:8002", timeout: float = 30.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("LessonServiceClient must be used as async context manager")
        return self._client
    
    async def create_lesson(self, lesson_data: LessonData) -> Optional[LessonResponse]:
        """Создание нового урока."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/lessons",
                json={
                    "topic": lesson_data.topic,
                    "date": lesson_data.date.isoformat(),
                    "student_id": lesson_data.student_id,
                    "tutor_id": lesson_data.tutor_id,
                    "duration_minutes": lesson_data.duration_minutes,
                    "skills_developed": lesson_data.skills_developed,
                    "notes": lesson_data.notes,
                    "room_url": lesson_data.room_url
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                return LessonResponse(
                    id=data["id"],
                    topic=data["topic"],
                    date=datetime.fromisoformat(data["date"]),
                    student_id=data["student_id"],
                    tutor_id=data["tutor_id"],
                    duration_minutes=data["duration_minutes"],
                    attendance_status=data["attendance_status"],
                    lesson_status=data["lesson_status"],
                    is_attended=data["is_attended"],
                    mastery_level=data["mastery_level"],
                    skills_developed=data["skills_developed"],
                    mastery_comment=data["mastery_comment"],
                    notes=data["notes"],
                    created_at=datetime.fromisoformat(data["created_at"])
                )
            else:
                logger.error(f"Failed to create lesson: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating lesson: {e}")
            return None
    
    async def get_lesson(self, lesson_id: int) -> Optional[LessonResponse]:
        """Получение урока по ID."""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/lessons/{lesson_id}")
            
            if response.status_code == 200:
                data = response.json()
                return LessonResponse(
                    id=data["id"],
                    topic=data["topic"],
                    date=datetime.fromisoformat(data["date"]),
                    student_id=data["student_id"],
                    tutor_id=data["tutor_id"],
                    duration_minutes=data["duration_minutes"],
                    attendance_status=data["attendance_status"],
                    lesson_status=data["lesson_status"],
                    is_attended=data["is_attended"],
                    mastery_level=data["mastery_level"],
                    skills_developed=data["skills_developed"],
                    mastery_comment=data["mastery_comment"],
                    notes=data["notes"],
                    created_at=datetime.fromisoformat(data["created_at"])
                )
            else:
                logger.error(f"Failed to get lesson {lesson_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting lesson {lesson_id}: {e}")
            return None
    
    async def update_lesson(
        self, 
        lesson_id: int, 
        updates: Dict[str, Any]
    ) -> Optional[LessonResponse]:
        """Обновление урока."""
        try:
            # Конвертация datetime в ISO формат
            if "date" in updates and isinstance(updates["date"], datetime):
                updates["date"] = updates["date"].isoformat()
            
            response = await self.client.put(
                f"{self.base_url}/api/v1/lessons/{lesson_id}",
                json=updates
            )
            
            if response.status_code == 200:
                data = response.json()
                return LessonResponse(
                    id=data["id"],
                    topic=data["topic"],
                    date=datetime.fromisoformat(data["date"]),
                    student_id=data["student_id"],
                    tutor_id=data["tutor_id"],
                    duration_minutes=data["duration_minutes"],
                    attendance_status=data["attendance_status"],
                    lesson_status=data["lesson_status"],
                    is_attended=data["is_attended"],
                    mastery_level=data["mastery_level"],
                    skills_developed=data["skills_developed"],
                    mastery_comment=data["mastery_comment"],
                    notes=data["notes"],
                    created_at=datetime.fromisoformat(data["created_at"])
                )
            else:
                logger.error(f"Failed to update lesson {lesson_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating lesson {lesson_id}: {e}")
            return None
    
    async def reschedule_lesson(
        self, 
        lesson_id: int, 
        new_date: datetime, 
        reason: str
    ) -> Optional[LessonResponse]:
        """Перенос урока."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/lessons/{lesson_id}/reschedule",
                json={
                    "new_date": new_date.isoformat(),
                    "reason": reason
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return LessonResponse(
                    id=data["id"],
                    topic=data["topic"],
                    date=datetime.fromisoformat(data["date"]),
                    student_id=data["student_id"],
                    tutor_id=data["tutor_id"],
                    duration_minutes=data["duration_minutes"],
                    attendance_status=data["attendance_status"],
                    lesson_status=data["lesson_status"],
                    is_attended=data["is_attended"],
                    mastery_level=data["mastery_level"],
                    skills_developed=data["skills_developed"],
                    mastery_comment=data["mastery_comment"],
                    notes=data["notes"],
                    created_at=datetime.fromisoformat(data["created_at"])
                )
            else:
                logger.error(f"Failed to reschedule lesson {lesson_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error rescheduling lesson {lesson_id}: {e}")
            return None
    
    async def cancel_lesson(
        self, 
        lesson_id: int, 
        reason: str, 
        attendance_status: str = "excused_absence"
    ) -> Optional[LessonResponse]:
        """Отмена урока."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/lessons/{lesson_id}/cancel",
                json={
                    "reason": reason,
                    "attendance_status": attendance_status
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return LessonResponse(
                    id=data["id"],
                    topic=data["topic"],
                    date=datetime.fromisoformat(data["date"]),
                    student_id=data["student_id"],
                    tutor_id=data["tutor_id"],
                    duration_minutes=data["duration_minutes"],
                    attendance_status=data["attendance_status"],
                    lesson_status=data["lesson_status"],
                    is_attended=data["is_attended"],
                    mastery_level=data["mastery_level"],
                    skills_developed=data["skills_developed"],
                    mastery_comment=data["mastery_comment"],
                    notes=data["notes"],
                    created_at=datetime.fromisoformat(data["created_at"])
                )
            else:
                logger.error(f"Failed to cancel lesson {lesson_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error cancelling lesson {lesson_id}: {e}")
            return None
    
    async def get_lessons(
        self,
        student_id: Optional[int] = None,
        tutor_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Optional[Dict[str, Any]]:
        """Получение списка уроков с фильтрами."""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            
            if student_id:
                params["student_id"] = student_id
            if tutor_id:
                params["tutor_id"] = tutor_id
            if date_from:
                params["date_from"] = date_from.isoformat()
            if date_to:
                params["date_to"] = date_to.isoformat()
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/lessons",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                # Конвертация дат в datetime объекты
                for lesson in data["lessons"]:
                    lesson["date"] = datetime.fromisoformat(lesson["date"])
                    lesson["created_at"] = datetime.fromisoformat(lesson["created_at"])
                
                return data
            else:
                logger.error(f"Failed to get lessons: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting lessons: {e}")
            return None
    
    async def mark_attendance(
        self,
        lesson_id: int,
        attendance_status: str,
        student_rating: Optional[int] = None,
        tutor_rating: Optional[int] = None,
        student_feedback: Optional[str] = None,
        tutor_notes: Optional[str] = None
    ) -> bool:
        """Отметка посещаемости урока."""
        try:
            data = {
                "attendance_status": attendance_status
            }
            
            if student_rating:
                data["student_rating"] = student_rating
            if tutor_rating:
                data["tutor_rating"] = tutor_rating
            if student_feedback:
                data["student_feedback"] = student_feedback
            if tutor_notes:
                data["tutor_notes"] = tutor_notes
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/lessons/{lesson_id}/attendance",
                json=data
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error marking attendance for lesson {lesson_id}: {e}")
            return False
    
    async def get_lesson_stats(
        self,
        student_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Получение статистики по урокам."""
        try:
            params = {}
            
            if student_id:
                params["student_id"] = student_id
            if date_from:
                params["date_from"] = date_from.isoformat()
            if date_to:
                params["date_to"] = date_to.isoformat()
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/lessons/stats",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get lesson stats: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting lesson stats: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Проверка состояния Lesson Service."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Lesson Service health check failed: {e}")
            return False


# Fallback функции для обратной совместимости с монолитом
async def create_lesson_fallback(lesson_data: LessonData) -> Optional[int]:
    """Fallback создание урока через монолитную БД."""
    try:
        from ...src.database import SessionLocal, Lesson, TopicMastery, AttendanceStatus, LessonStatus
        
        db = SessionLocal()
        try:
            lesson = Lesson(
                topic=lesson_data.topic,
                date=lesson_data.date,
                student_id=lesson_data.student_id,
                tutor_id=lesson_data.tutor_id,
                duration_minutes=lesson_data.duration_minutes,
                skills_developed=lesson_data.skills_developed,
                mastery_level=TopicMastery.NOT_LEARNED,
                attendance_status=AttendanceStatus.ATTENDED,
                lesson_status=LessonStatus.NOT_CONDUCTED,
                notes=lesson_data.notes,
                room_url=lesson_data.room_url
            )
            
            db.add(lesson)
            db.commit()
            db.refresh(lesson)
            
            logger.info(f"Created lesson {lesson.id} via fallback")
            return lesson.id
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Fallback lesson creation failed: {e}")
        return None


# Создание глобального клиента с fallback логикой
class LessonServiceManager:
    """Менеджер для работы с Lesson Service с fallback на монолит."""
    
    def __init__(self, service_url: str = "http://localhost:8002"):
        self.service_url = service_url
        self._service_available = None
    
    async def _check_service_availability(self) -> bool:
        """Проверка доступности сервиса."""
        if self._service_available is not None:
            return self._service_available
        
        try:
            async with LessonServiceClient(self.service_url) as client:
                self._service_available = await client.health_check()
                return self._service_available
        except Exception:
            self._service_available = False
            return False
    
    async def create_lesson(self, lesson_data: LessonData) -> Optional[int]:
        """Создание урока с fallback."""
        if await self._check_service_availability():
            try:
                async with LessonServiceClient(self.service_url) as client:
                    lesson = await client.create_lesson(lesson_data)
                    return lesson.id if lesson else None
            except Exception as e:
                logger.warning(f"Lesson service failed, using fallback: {e}")
                self._service_available = False
        
        # Fallback на монолитную БД
        return await create_lesson_fallback(lesson_data)
    
    async def get_lesson(self, lesson_id: int) -> Optional[LessonResponse]:
        """Получение урока с fallback."""
        if await self._check_service_availability():
            try:
                async with LessonServiceClient(self.service_url) as client:
                    return await client.get_lesson(lesson_id)
            except Exception as e:
                logger.warning(f"Lesson service failed, using fallback: {e}")
                self._service_available = False
        
        # TODO: Реализовать fallback получение из монолитной БД
        return None


# Глобальный экземпляр менеджера
lesson_service_manager = LessonServiceManager()