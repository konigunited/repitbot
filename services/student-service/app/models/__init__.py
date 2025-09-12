# -*- coding: utf-8 -*-
"""
Student Service Models
Модели данных для микросервиса студентов
"""

# Импортируем все модели для создания таблиц
from .student import Student
from .achievement import Achievement, StudentAchievement, AchievementType, AchievementRarity, DEFAULT_ACHIEVEMENTS
from .progress import LearningProgress, LearningGoal, StudySession, ProgressType, DifficultyLevel
from .gamification import (
    GamificationData, 
    Leaderboard, 
    Challenge, 
    ChallengeParticipation
)

# Экспортируем все основные классы
__all__ = [
    # Основные модели
    "Student",
    "Achievement",
    "StudentAchievement", 
    "LearningProgress",
    "LearningGoal",
    "StudySession",
    "GamificationData",
    "Leaderboard",
    "Challenge", 
    "ChallengeParticipation",
    
    # Енумы
    "AchievementType",
    "AchievementRarity", 
    "ProgressType",
    "DifficultyLevel",
    
    # Константы
    "DEFAULT_ACHIEVEMENTS"
]