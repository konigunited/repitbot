# -*- coding: utf-8 -*-
"""
Student Schemas
Pydantic схемы для работы со студентами
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class StudentBase(BaseModel):
    """Базовая схема студента"""
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    avatar_url: Optional[str] = Field(None, max_length=500)
    preferred_subjects: List[str] = Field(default_factory=list)
    learning_goals: List[str] = Field(default_factory=list)
    study_schedule: Dict[str, Any] = Field(default_factory=dict)
    notification_preferences: Dict[str, Any] = Field(default_factory=dict)
    privacy_settings: Dict[str, Any] = Field(default_factory=dict)


class StudentCreate(StudentBase):
    """Схема для создания студента"""
    user_id: int = Field(..., description="ID пользователя из User Service")


class StudentUpdate(StudentBase):
    """Схема для обновления студента"""
    is_active: Optional[bool] = None
    is_premium: Optional[bool] = None


class StudentProfileUpdate(BaseModel):
    """Схема для обновления профиля студента"""
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    avatar_url: Optional[str] = Field(None, max_length=500)
    preferred_subjects: Optional[List[str]] = None
    learning_goals: Optional[List[str]] = None
    privacy_settings: Optional[Dict[str, Any]] = None


class StudentPreferences(BaseModel):
    """Схема настроек студента"""
    study_schedule: Optional[Dict[str, Any]] = None
    notification_preferences: Optional[Dict[str, Any]] = None
    privacy_settings: Optional[Dict[str, Any]] = None


# Схемы для геймификации
class XPTransactionCreate(BaseModel):
    """Схема для создания транзакции XP"""
    student_id: int
    action: str = Field(..., max_length=100)
    amount: int = Field(..., gt=0)
    lesson_id: Optional[int] = None
    homework_id: Optional[int] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class XPTransactionResponse(BaseModel):
    """Схема ответа транзакции XP"""
    id: int
    student_id: int
    action: str
    amount: int
    lesson_id: Optional[int]
    homework_id: Optional[int]
    description: Optional[str]
    created_at: datetime
    metadata: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class BadgeAwardCreate(BaseModel):
    """Схема для награждения значком"""
    student_id: int
    badge_code: str
    reason: Optional[str] = None


class BadgeResponse(BaseModel):
    """Схема ответа значка"""
    id: int
    code: str
    name: str
    description: str
    category: str
    rarity: str
    icon: Optional[str]
    color: Optional[str]
    image_url: Optional[str]
    is_active: bool
    is_secret: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentBadgeResponse(BaseModel):
    """Схема ответа значка студента"""
    id: int
    student_id: int
    badge_id: int
    earned_at: datetime
    reason: Optional[str]
    is_displayed: bool
    badge: BadgeResponse

    model_config = ConfigDict(from_attributes=True)


class LevelResponse(BaseModel):
    """Схема ответа уровня"""
    level_number: int
    title: str
    description: Optional[str]
    xp_required: int
    color: Optional[str]
    icon: Optional[str]
    rewards: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class GameStatsResponse(BaseModel):
    """Схема ответа игровой статистики"""
    student_id: int
    total_xp: int
    current_level: int
    level_info: LevelResponse
    xp_to_next_level: int
    progress_to_next_level: float
    total_badges: int
    recent_badges: List[StudentBadgeResponse]
    streak_days: int
    rank: Optional[int]

    model_config = ConfigDict(from_attributes=True)


# Схемы для рекомендаций
class RecommendationResponse(BaseModel):
    """Схема ответа рекомендации"""
    type: str
    title: str
    description: str
    relevance_score: float = Field(..., ge=0, le=100)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DifficultyPrediction(BaseModel):
    """Схема предсказания сложности"""
    difficulty: str = Field(..., regex="^(beginner|intermediate|advanced|remedial)$")
    confidence: float = Field(..., ge=0, le=1)
    avg_score: Optional[float] = None
    completion_rate: Optional[float] = None
    trend: Optional[float] = None
    session_count: int = 0


class SimilarStudent(BaseModel):
    """Схема похожего студента"""
    student_id: int
    username: Optional[str]
    display_name: Optional[str]
    similarity: float = Field(..., ge=0, le=1)
    common_skills: List[str]
    level: int


class SimilarStudentsResponse(BaseModel):
    """Схема ответа похожих студентов"""
    student_id: int
    similar_students: List[SimilarStudent]
    total_found: int


# Схемы для прогресса
class ProgressUpdateCreate(BaseModel):
    """Схема для обновления прогресса"""
    lesson_id: int
    completion_rate: float = Field(..., ge=0, le=1)
    time_spent: int = Field(..., ge=0)
    correct_answers: int = Field(..., ge=0)
    total_questions: int = Field(..., gt=0)
    skills_practiced: Optional[List[str]] = Field(default_factory=list)


class SkillProgressResponse(BaseModel):
    """Схема ответа прогресса навыка"""
    skill_name: str
    current_level: int
    progress_percent: float
    practice_count: int
    last_practiced: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class StudySessionResponse(BaseModel):
    """Схема ответа учебной сессии"""
    id: int
    lesson_id: Optional[int]
    duration: int
    score: float
    completed: bool
    skills_practiced: List[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProgressAnalyticsResponse(BaseModel):
    """Схема ответа аналитики прогресса"""
    period: str
    start_date: datetime
    end_date: datetime
    progress_trend: Dict[str, Any]
    activity_pattern: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    recommendations: List[str]


class ComprehensiveProgressResponse(BaseModel):
    """Комплексная схема ответа прогресса"""
    student_id: int
    overall_progress: Dict[str, Any]
    subjects: List[Dict[str, Any]]
    skills: List[SkillProgressResponse]
    recent_sessions: List[StudySessionResponse]
    activity_stats: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


# Схемы для соревнований
class CompetitionCreate(BaseModel):
    """Схема для создания соревнования"""
    title: str = Field(..., max_length=200)
    description: str
    competition_type: str = Field(..., max_length=50)
    max_participants: Optional[int] = None
    entry_fee_xp: int = Field(default=0, ge=0)
    registration_start: datetime
    registration_end: datetime
    competition_start: datetime
    competition_end: datetime
    first_place_reward: Dict[str, Any] = Field(default_factory=dict)
    second_place_reward: Dict[str, Any] = Field(default_factory=dict)
    third_place_reward: Dict[str, Any] = Field(default_factory=dict)
    participation_reward: Dict[str, Any] = Field(default_factory=dict)
    rules: Optional[str] = None
    scoring_criteria: Dict[str, Any] = Field(default_factory=dict)
    is_public: bool = True


class CompetitionResponse(BaseModel):
    """Схема ответа соревнования"""
    id: int
    title: str
    description: str
    competition_type: str
    max_participants: Optional[int]
    entry_fee_xp: int
    registration_start: datetime
    registration_end: datetime
    competition_start: datetime
    competition_end: datetime
    status: str
    is_public: bool
    participants_count: int
    is_registration_open: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompetitionParticipantResponse(BaseModel):
    """Схема ответа участника соревнования"""
    id: int
    student_id: int
    competition_id: int
    score: float
    rank: Optional[int]
    status: str
    is_winner: bool
    registered_at: datetime
    performance_data: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntry(BaseModel):
    """Схема записи в лидерборде"""
    rank: int
    student_id: int
    username: Optional[str]
    display_name: Optional[str]
    score: int
    level: Optional[int]
    level_title: Optional[str]
    avatar_url: Optional[str]


class LeaderboardResponse(BaseModel):
    """Схема ответа лидерборда"""
    leaderboard_type: str
    category: Optional[str]
    period: Optional[str]
    total_participants: int
    entries: List[LeaderboardEntry]
    student_rank: Optional[int]  # Позиция запрашивающего студента
    last_updated: datetime


class StudentStats(BaseModel):
    """Схема статистики студента"""
    lessons_completed: int = 0
    homework_submitted: int = 0
    homework_perfect: int = 0
    materials_studied: int = 0
    study_time_minutes: int = 0
    current_streak: int = 0
    best_streak: int = 0


class StudentLevel(BaseModel):
    """Схема уровня студента"""
    current_level: int
    experience_points: int
    xp_for_current_level: int
    xp_for_next_level: int
    xp_progress_percentage: float
    can_level_up: bool
    total_xp_earned: int


class StudentResponse(StudentBase):
    """Схема ответа со студентом"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    level: int
    experience_points: int
    total_xp_earned: int
    lessons_completed: int
    homework_submitted: int
    homework_perfect: int
    materials_studied: int
    study_time_minutes: int
    current_streak: int
    best_streak: int
    last_activity_date: Optional[datetime] = None
    is_active: bool
    is_premium: bool
    created_at: datetime
    updated_at: datetime
    
    # Вычисляемые поля
    xp_for_next_level: int
    xp_progress_percentage: float
    can_level_up: bool


class StudentSummary(BaseModel):
    """Краткая информация о студенте"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    level: int
    experience_points: int
    current_streak: int
    is_premium: bool


class StudentRanking(BaseModel):
    """Схема для рейтинга студентов"""
    student: StudentSummary
    rank: int
    score: int
    category: Optional[str] = None


class StudentActivity(BaseModel):
    """Схема активности студента"""
    date: datetime
    activity_type: str
    description: str
    xp_earned: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class XPTransaction(BaseModel):
    """Схема транзакции XP"""
    amount: int = Field(..., description="Количество XP (может быть отрицательным)")
    reason: str = Field(..., description="Причина начисления/списания")
    category: str = Field(default="general", description="Категория транзакции")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LevelUpResponse(BaseModel):
    """Схема ответа при повышении уровня"""
    old_level: int
    new_level: int
    xp_gained: int
    achievements_unlocked: List[str] = Field(default_factory=list)
    rewards: Dict[str, Any] = Field(default_factory=dict)


class StudentSearchFilters(BaseModel):
    """Фильтры для поиска студентов"""
    level_min: Optional[int] = None
    level_max: Optional[int] = None
    is_premium: Optional[bool] = None
    is_active: Optional[bool] = None
    has_streak: Optional[bool] = None
    subjects: Optional[List[str]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class BulkXPUpdate(BaseModel):
    """Схема для массового обновления XP"""
    updates: List[Dict[str, Any]] = Field(
        ..., 
        description="Список обновлений с полями: user_id, xp_amount, reason"
    )


class StudentDashboard(BaseModel):
    """Схема дашборда студента"""
    student: StudentResponse
    recent_activities: List[StudentActivity]
    current_goals: List[Dict[str, Any]]
    achievements_summary: Dict[str, Any]
    learning_statistics: Dict[str, Any]
    recommendations: List[Dict[str, Any]]