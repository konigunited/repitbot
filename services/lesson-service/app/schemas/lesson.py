# -*- coding: utf-8 -*-
"""
Pydantic схемы для Lesson Service.
Валидация входных и выходных данных API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.lesson import TopicMastery, AttendanceStatus, LessonStatus, ScheduleRecurrenceType


# Enum схемы для API
class TopicMasterySchema(str, Enum):
    NOT_LEARNED = "not_learned"
    LEARNED = "learned"
    MASTERED = "mastered"


class AttendanceStatusSchema(str, Enum):
    ATTENDED = "attended"
    EXCUSED_ABSENCE = "excused_absence"
    UNEXCUSED_ABSENCE = "unexcused_absence"
    RESCHEDULED = "rescheduled"


class LessonStatusSchema(str, Enum):
    NOT_CONDUCTED = "not_conducted"
    CONDUCTED = "conducted"


class ScheduleRecurrenceTypeSchema(str, Enum):
    NONE = "none"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


# Базовые схемы
class LessonBase(BaseModel):
    """Базовые поля для урока."""
    topic: str = Field(..., min_length=1, max_length=200, description="Тема урока")
    date: datetime = Field(..., description="Дата и время урока")
    duration_minutes: int = Field(60, ge=15, le=300, description="Длительность урока в минутах")
    skills_developed: Optional[str] = Field(None, max_length=1000, description="Развитые навыки")
    mastery_level: TopicMasterySchema = Field(TopicMasterySchema.NOT_LEARNED, description="Уровень освоения")
    mastery_comment: Optional[str] = Field(None, max_length=500, description="Комментарий по освоению")
    notes: Optional[str] = Field(None, max_length=1000, description="Заметки к уроку")
    room_url: Optional[str] = Field(None, max_length=500, description="Ссылка на онлайн-комнату")


class LessonCreate(LessonBase):
    """Схема для создания урока."""
    student_id: int = Field(..., gt=0, description="ID студента")
    tutor_id: Optional[int] = Field(None, gt=0, description="ID репетитора")
    schedule_id: Optional[int] = Field(None, gt=0, description="ID расписания")
    
    @validator('date')
    def validate_future_date(cls, v):
        if v <= datetime.now():
            raise ValueError('Дата урока должна быть в будущем')
        return v


class LessonUpdate(BaseModel):
    """Схема для обновления урока."""
    topic: Optional[str] = Field(None, min_length=1, max_length=200)
    date: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=300)
    skills_developed: Optional[str] = Field(None, max_length=1000)
    mastery_level: Optional[TopicMasterySchema] = None
    mastery_comment: Optional[str] = Field(None, max_length=500)
    attendance_status: Optional[AttendanceStatusSchema] = None
    lesson_status: Optional[LessonStatusSchema] = None
    notes: Optional[str] = Field(None, max_length=1000)
    room_url: Optional[str] = Field(None, max_length=500)


class LessonReschedule(BaseModel):
    """Схема для переноса урока."""
    new_date: datetime = Field(..., description="Новая дата урока")
    reason: str = Field(..., min_length=1, max_length=500, description="Причина переноса")
    
    @validator('new_date')
    def validate_future_date(cls, v):
        if v <= datetime.now():
            raise ValueError('Новая дата урока должна быть в будущем')
        return v


class LessonCancel(BaseModel):
    """Схема для отмены урока."""
    reason: str = Field(..., min_length=1, max_length=500, description="Причина отмены")
    attendance_status: AttendanceStatusSchema = Field(
        AttendanceStatusSchema.EXCUSED_ABSENCE, 
        description="Статус посещаемости для отмененного урока"
    )


class LessonResponse(LessonBase):
    """Схема ответа с данными урока."""
    id: int
    student_id: int
    tutor_id: Optional[int]
    schedule_id: Optional[int]
    
    # Статусы
    attendance_status: AttendanceStatusSchema
    lesson_status: LessonStatusSchema
    is_attended: bool  # Для обратной совместимости
    
    # Перенос
    original_date: Optional[datetime]
    is_rescheduled: bool
    reschedule_reason: Optional[str]
    
    # Дополнительные поля
    homework_assigned: bool
    reminder_sent: bool
    notification_sent: bool
    materials_used: Optional[str]
    
    # Метаданные
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int]
    
    class Config:
        from_attributes = True


class LessonListResponse(BaseModel):
    """Схема ответа со списком уроков."""
    lessons: List[LessonResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Схемы для расписания
class ScheduleBase(BaseModel):
    """Базовые поля для расписания."""
    name: str = Field(..., min_length=1, max_length=100, description="Название расписания")
    description: Optional[str] = Field(None, max_length=500, description="Описание расписания")
    recurrence_type: ScheduleRecurrenceTypeSchema = Field(
        ScheduleRecurrenceTypeSchema.WEEKLY, 
        description="Тип повторения"
    )
    interval_days: int = Field(7, ge=1, le=365, description="Интервал в днях")
    start_time: datetime = Field(..., description="Время начала уроков")
    duration_minutes: int = Field(60, ge=15, le=300, description="Длительность урока")
    valid_from: datetime = Field(..., description="Дата начала действия расписания")
    valid_until: Optional[datetime] = Field(None, description="Дата окончания действия")
    weekdays: Optional[List[int]] = Field(None, description="Дни недели (1=Пн, 7=Вс)")
    default_topic_template: Optional[str] = Field(None, max_length=200, description="Шаблон темы урока")
    default_room_url: Optional[str] = Field(None, max_length=500, description="Ссылка по умолчанию")


class ScheduleCreate(ScheduleBase):
    """Схема для создания расписания."""
    student_id: int = Field(..., gt=0, description="ID студента")
    tutor_id: int = Field(..., gt=0, description="ID репетитора")
    
    @validator('valid_until')
    def validate_valid_until(cls, v, values):
        if v and 'valid_from' in values and v <= values['valid_from']:
            raise ValueError('Дата окончания должна быть позже даты начала')
        return v
    
    @validator('weekdays')
    def validate_weekdays(cls, v):
        if v:
            if not all(1 <= day <= 7 for day in v):
                raise ValueError('Дни недели должны быть от 1 до 7')
            if len(v) != len(set(v)):
                raise ValueError('Дни недели не должны повторяться')
        return v


class ScheduleUpdate(BaseModel):
    """Схема для обновления расписания."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    recurrence_type: Optional[ScheduleRecurrenceTypeSchema] = None
    interval_days: Optional[int] = Field(None, ge=1, le=365)
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=300)
    valid_until: Optional[datetime] = None
    weekdays: Optional[List[int]] = None
    default_topic_template: Optional[str] = Field(None, max_length=200)
    default_room_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class ScheduleResponse(ScheduleBase):
    """Схема ответа с данными расписания."""
    id: int
    student_id: int
    tutor_id: int
    is_active: bool
    lessons_created: int
    last_lesson_created: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    created_by: int
    
    class Config:
        from_attributes = True


# Схемы для посещаемости
class AttendanceCreate(BaseModel):
    """Схема для отметки посещаемости."""
    attendance_status: AttendanceStatusSchema
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    absence_reason: Optional[str] = Field(None, max_length=500)
    is_excused: bool = False
    student_rating: Optional[int] = Field(None, ge=1, le=5)
    student_feedback: Optional[str] = Field(None, max_length=1000)
    tutor_rating: Optional[int] = Field(None, ge=1, le=5)
    tutor_notes: Optional[str] = Field(None, max_length=1000)


class AttendanceResponse(AttendanceCreate):
    """Схема ответа с данными посещаемости."""
    id: int
    lesson_id: int
    actual_duration_minutes: Optional[int]
    recorded_at: datetime
    recorded_by: int
    
    class Config:
        from_attributes = True


# Схемы для фильтрации
class LessonFilter(BaseModel):
    """Схема для фильтрации уроков."""
    student_id: Optional[int] = None
    tutor_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    lesson_status: Optional[LessonStatusSchema] = None
    attendance_status: Optional[AttendanceStatusSchema] = None
    mastery_level: Optional[TopicMasterySchema] = None
    topic_search: Optional[str] = Field(None, max_length=100)
    
    # Пагинация
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    
    # Сортировка
    sort_by: str = Field("date", regex="^(date|topic|created_at|updated_at)$")
    sort_order: str = Field("asc", regex="^(asc|desc)$")


# Схемы для статистики
class LessonStats(BaseModel):
    """Статистика по урокам."""
    total_lessons: int
    conducted_lessons: int
    cancelled_lessons: int
    rescheduled_lessons: int
    average_duration: float
    attendance_rate: float
    mastery_distribution: Dict[str, int]


class StudentLessonStats(LessonStats):
    """Статистика уроков для конкретного студента."""
    student_id: int
    total_study_hours: float
    current_streak: int
    longest_streak: int


# Схемы для операций
class BulkLessonCreate(BaseModel):
    """Схема для массового создания уроков."""
    lessons: List[LessonCreate] = Field(..., min_items=1, max_items=50)
    
    @validator('lessons')
    def validate_unique_dates(cls, v):
        dates = [lesson.date for lesson in v]
        if len(dates) != len(set(dates)):
            raise ValueError('Даты уроков должны быть уникальными')
        return v


class BulkOperationResponse(BaseModel):
    """Ответ на массовую операцию."""
    success_count: int
    error_count: int
    created_ids: List[int]
    errors: List[Dict[str, Any]]


# Схемы для событий
class LessonEventData(BaseModel):
    """Данные события урока."""
    lesson_id: int
    student_id: int
    tutor_id: Optional[int]
    event_type: str
    timestamp: datetime
    data: Dict[str, Any] = {}


class NotificationData(BaseModel):
    """Данные для уведомлений."""
    recipients: List[int]  # ID получателей
    message_template: str
    message_data: Dict[str, Any] = {}
    notification_type: str = "lesson_reminder"