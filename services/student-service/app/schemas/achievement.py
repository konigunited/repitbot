# -*- coding: utf-8 -*-
"""
Achievement Schemas
Pydantic схемы для системы достижений
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AchievementTypeEnum(str, Enum):
    """Типы достижений"""
    LESSON = "lesson"
    HOMEWORK = "homework"
    STREAK = "streak"
    STUDY_TIME = "study_time"
    PERFECT_SCORE = "perfect_score"
    MILESTONE = "milestone"
    SOCIAL = "social"
    SPECIAL = "special"


class AchievementRarityEnum(str, Enum):
    """Редкость достижений"""
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class AchievementBase(BaseModel):
    """Базовая схема достижения"""
    name: str = Field(..., max_length=100)
    description: str
    icon_url: Optional[str] = Field(None, max_length=500)
    type: AchievementTypeEnum
    rarity: AchievementRarityEnum = AchievementRarityEnum.COMMON
    xp_reward: int = Field(default=0, ge=0)
    badge_url: Optional[str] = Field(None, max_length=500)
    criteria: Dict[str, Any]
    is_active: bool = True
    is_hidden: bool = False
    is_repeatable: bool = False
    sort_order: int = 0


class AchievementCreate(AchievementBase):
    """Схема для создания достижения"""
    pass


class AchievementUpdate(BaseModel):
    """Схема для обновления достижения"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    icon_url: Optional[str] = Field(None, max_length=500)
    xp_reward: Optional[int] = Field(None, ge=0)
    badge_url: Optional[str] = Field(None, max_length=500)
    criteria: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_hidden: Optional[bool] = None
    is_repeatable: Optional[bool] = None
    sort_order: Optional[int] = None


class AchievementResponse(AchievementBase):
    """Схема ответа с достижением"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


class StudentAchievementBase(BaseModel):
    """Базовая схема достижения студента"""
    progress_data: Optional[Dict[str, Any]] = None
    is_showcased: bool = False


class StudentAchievementCreate(StudentAchievementBase):
    """Схема для создания достижения студента"""
    student_id: int
    achievement_id: int


class StudentAchievementUpdate(BaseModel):
    """Схема для обновления достижения студента"""
    progress_data: Optional[Dict[str, Any]] = None
    is_showcased: Optional[bool] = None


class StudentAchievementResponse(StudentAchievementBase):
    """Схема ответа с достижением студента"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    student_id: int
    achievement_id: int
    earned_at: datetime
    notification_sent: bool
    achievement: Optional[AchievementResponse] = None


class AchievementProgress(BaseModel):
    """Схема прогресса достижения"""
    achievement_id: int
    achievement_name: str
    current_value: int
    target_value: int
    progress_percentage: float
    is_completed: bool
    estimated_completion: Optional[datetime] = None


class AchievementUnlocked(BaseModel):
    """Схема разблокированного достижения"""
    achievement: AchievementResponse
    student_achievement: StudentAchievementResponse
    xp_earned: int
    is_new_unlock: bool = True


class AchievementFilters(BaseModel):
    """Фильтры для поиска достижений"""
    type: Optional[AchievementTypeEnum] = None
    rarity: Optional[AchievementRarityEnum] = None
    is_active: Optional[bool] = None
    is_hidden: Optional[bool] = None
    is_repeatable: Optional[bool] = None
    earned_by_student: Optional[int] = None  # ID студента
    not_earned_by_student: Optional[int] = None  # ID студента


class AchievementStats(BaseModel):
    """Статистика достижений"""
    total_achievements: int
    earned_achievements: int
    completion_percentage: float
    by_rarity: Dict[str, int]
    by_type: Dict[str, int]
    recent_unlocks: List[StudentAchievementResponse]


class AchievementLeaderboard(BaseModel):
    """Лидерборд по достижениям"""
    student_id: int
    student_name: Optional[str] = None
    avatar_url: Optional[str] = None
    achievements_count: int
    total_xp_from_achievements: int
    rare_achievements_count: int
    legendary_achievements_count: int


class BulkAchievementCheck(BaseModel):
    """Схема для массовой проверки достижений"""
    student_ids: List[int]
    force_recheck: bool = False
    achievement_types: Optional[List[AchievementTypeEnum]] = None


class AchievementCriteria(BaseModel):
    """Схема критериев достижения"""
    lessons_completed: Optional[int] = None
    homework_submitted: Optional[int] = None
    homework_perfect: Optional[int] = None
    current_streak: Optional[int] = None
    study_time_minutes: Optional[int] = None
    level: Optional[int] = None
    materials_studied: Optional[int] = None
    custom_criteria: Optional[Dict[str, Any]] = None


class CreateAchievementFromTemplate(BaseModel):
    """Схема создания достижения из шаблона"""
    template_name: str
    customizations: Optional[Dict[str, Any]] = None