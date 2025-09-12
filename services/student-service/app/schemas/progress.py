# -*- coding: utf-8 -*-
"""
Progress Schemas
Pydantic схемы для прогресса обучения
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProgressTypeEnum(str, Enum):
    """Типы прогресса"""
    LESSON = "lesson"
    SUBJECT = "subject"
    SKILL = "skill"
    GOAL = "goal"
    COURSE = "course"


class DifficultyLevelEnum(str, Enum):
    """Уровни сложности"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningProgressBase(BaseModel):
    """Базовая схема прогресса обучения"""
    progress_type: ProgressTypeEnum
    object_id: str = Field(..., max_length=100)
    object_name: str = Field(..., max_length=200)
    current_step: int = Field(default=0, ge=0)
    total_steps: int = Field(default=1, ge=1)
    difficulty_level: DifficultyLevelEnum = DifficultyLevelEnum.BEGINNER
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class LearningProgressCreate(LearningProgressBase):
    """Схема для создания прогресса обучения"""
    student_id: int


class LearningProgressUpdate(BaseModel):
    """Схема для обновления прогресса обучения"""
    current_step: Optional[int] = Field(None, ge=0)
    total_steps: Optional[int] = Field(None, ge=1)
    time_spent_minutes: Optional[int] = Field(None, ge=0)
    mastery_score: Optional[float] = Field(None, ge=0, le=100)
    confidence_level: Optional[float] = Field(None, ge=0, le=100)
    difficulty_level: Optional[DifficultyLevelEnum] = None
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    is_bookmarked: Optional[bool] = None


class ProgressStep(BaseModel):
    """Схема шага прогресса"""
    step_number: int
    step_name: str
    is_completed: bool = False
    completion_time: Optional[datetime] = None
    score: Optional[float] = None


class LearningProgressResponse(LearningProgressBase):
    """Схема ответа с прогрессом обучения"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    student_id: int
    progress_percentage: float
    time_spent_minutes: int
    mastery_score: float
    confidence_level: float
    last_activity_at: datetime
    started_at: datetime
    completed_at: Optional[datetime] = None
    is_completed: bool
    is_bookmarked: bool


class LearningGoalBase(BaseModel):
    """Базовая схема цели обучения"""
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    target_value: float = Field(..., gt=0)
    unit: str = Field(default="items", max_length=50)
    target_date: Optional[datetime] = None
    is_public: bool = False
    reminder_enabled: bool = True


class LearningGoalCreate(LearningGoalBase):
    """Схема для создания цели обучения"""
    student_id: int


class LearningGoalUpdate(BaseModel):
    """Схема для обновления цели обучения"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    target_value: Optional[float] = Field(None, gt=0)
    current_value: Optional[float] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=50)
    target_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    reminder_enabled: Optional[bool] = None


class LearningGoalResponse(LearningGoalBase):
    """Схема ответа с целью обучения"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    student_id: int
    current_value: float
    progress_percentage: float
    is_completed: bool
    is_active: bool
    created_at: datetime
    completed_at: Optional[datetime] = None


class StudySessionBase(BaseModel):
    """Базовая схема сессии обучения"""
    subject: Optional[str] = Field(None, max_length=100)
    activity_type: str = Field(..., max_length=50)
    activity_id: Optional[str] = Field(None, max_length=100)


class StudySessionCreate(StudySessionBase):
    """Схема для создания сессии обучения"""
    student_id: int


class StudySessionUpdate(BaseModel):
    """Схема для обновления сессии обучения"""
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    focus_score: Optional[float] = Field(None, ge=0, le=100)
    productivity_score: Optional[float] = Field(None, ge=0, le=100)
    satisfaction_score: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StudySessionResponse(StudySessionBase):
    """Схема ответа с сессией обучения"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    student_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: int
    focus_score: float
    productivity_score: float
    satisfaction_score: float
    notes: Optional[str] = None
    metadata: Dict[str, Any]


class ProgressSummary(BaseModel):
    """Сводка прогресса студента"""
    total_progress_records: int
    completed_count: int
    in_progress_count: int
    bookmarked_count: int
    total_time_spent_minutes: int
    average_mastery_score: float
    subjects_studied: List[str]
    recent_activities: List[LearningProgressResponse]


class GoalSummary(BaseModel):
    """Сводка целей студента"""
    total_goals: int
    active_goals: int
    completed_goals: int
    completion_rate: float
    overdue_goals: int
    upcoming_deadlines: List[LearningGoalResponse]


class StudyAnalytics(BaseModel):
    """Аналитика обучения"""
    total_study_time_minutes: int
    average_session_duration: float
    study_sessions_count: int
    average_focus_score: float
    average_productivity_score: float
    study_streak_days: int
    most_studied_subjects: List[Dict[str, Any]]
    study_patterns: Dict[str, Any]


class ProgressFilters(BaseModel):
    """Фильтры для прогресса"""
    progress_type: Optional[ProgressTypeEnum] = None
    difficulty_level: Optional[DifficultyLevelEnum] = None
    is_completed: Optional[bool] = None
    is_bookmarked: Optional[bool] = None
    subject: Optional[str] = None
    started_after: Optional[datetime] = None
    started_before: Optional[datetime] = None
    min_mastery_score: Optional[float] = Field(None, ge=0, le=100)


class BulkProgressUpdate(BaseModel):
    """Массовое обновление прогресса"""
    updates: List[Dict[str, Any]] = Field(
        ...,
        description="Список обновлений с полями: student_id, object_id, progress_data"
    )


class LearningRecommendation(BaseModel):
    """Рекомендация для обучения"""
    type: str  # "lesson", "material", "skill", "goal"
    object_id: str
    title: str
    description: str
    reason: str  # Причина рекомендации
    priority: int = Field(ge=1, le=10)  # Приоритет 1-10
    estimated_time_minutes: Optional[int] = None
    difficulty_level: Optional[DifficultyLevelEnum] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)