# -*- coding: utf-8 -*-
"""
Student Service Schemas
Pydantic схемы для микросервиса студентов
"""

# Импортируем все схемы
from .student import (
    StudentBase,
    StudentCreate,
    StudentUpdate,
    StudentProfileUpdate,
    StudentPreferences,
    StudentStats,
    StudentLevel,
    StudentResponse,
    StudentSummary,
    StudentRanking,
    StudentActivity,
    XPTransaction,
    LevelUpResponse,
    StudentSearchFilters,
    BulkXPUpdate,
    StudentDashboard
)

from .achievement import (
    AchievementTypeEnum,
    AchievementRarityEnum,
    AchievementBase,
    AchievementCreate,
    AchievementUpdate,
    AchievementResponse,
    StudentAchievementBase,
    StudentAchievementCreate,
    StudentAchievementUpdate,
    StudentAchievementResponse,
    AchievementProgress,
    AchievementUnlocked,
    AchievementFilters,
    AchievementStats,
    AchievementLeaderboard,
    BulkAchievementCheck,
    AchievementCriteria,
    CreateAchievementFromTemplate
)

from .progress import (
    ProgressTypeEnum,
    DifficultyLevelEnum,
    LearningProgressBase,
    LearningProgressCreate,
    LearningProgressUpdate,
    ProgressStep,
    LearningProgressResponse,
    LearningGoalBase,
    LearningGoalCreate,
    LearningGoalUpdate,
    LearningGoalResponse,
    StudySessionBase,
    StudySessionCreate,
    StudySessionUpdate,
    StudySessionResponse,
    ProgressSummary,
    GoalSummary,
    StudyAnalytics,
    ProgressFilters,
    BulkProgressUpdate,
    LearningRecommendation
)

# Экспортируем все схемы
__all__ = [
    # Student schemas
    "StudentBase",
    "StudentCreate", 
    "StudentUpdate",
    "StudentProfileUpdate",
    "StudentPreferences",
    "StudentStats",
    "StudentLevel",
    "StudentResponse",
    "StudentSummary",
    "StudentRanking",
    "StudentActivity",
    "XPTransaction",
    "LevelUpResponse",
    "StudentSearchFilters",
    "BulkXPUpdate",
    "StudentDashboard",
    
    # Achievement schemas
    "AchievementTypeEnum",
    "AchievementRarityEnum",
    "AchievementBase",
    "AchievementCreate",
    "AchievementUpdate", 
    "AchievementResponse",
    "StudentAchievementBase",
    "StudentAchievementCreate",
    "StudentAchievementUpdate",
    "StudentAchievementResponse",
    "AchievementProgress",
    "AchievementUnlocked",
    "AchievementFilters",
    "AchievementStats",
    "AchievementLeaderboard",
    "BulkAchievementCheck",
    "AchievementCriteria",
    "CreateAchievementFromTemplate",
    
    # Progress schemas
    "ProgressTypeEnum",
    "DifficultyLevelEnum",
    "LearningProgressBase",
    "LearningProgressCreate",
    "LearningProgressUpdate",
    "ProgressStep",
    "LearningProgressResponse",
    "LearningGoalBase", 
    "LearningGoalCreate",
    "LearningGoalUpdate",
    "LearningGoalResponse",
    "StudySessionBase",
    "StudySessionCreate",
    "StudySessionUpdate",
    "StudySessionResponse",
    "ProgressSummary",
    "GoalSummary",
    "StudyAnalytics",
    "ProgressFilters",
    "BulkProgressUpdate",
    "LearningRecommendation"
]