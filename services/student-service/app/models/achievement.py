# -*- coding: utf-8 -*-
"""
Achievement Models
Модели системы достижений
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..database.connection import Base


class AchievementType(PyEnum):
    """Типы достижений"""
    LESSON = "lesson"  # За уроки
    HOMEWORK = "homework"  # За домашние задания
    STREAK = "streak"  # За регулярность
    STUDY_TIME = "study_time"  # За время обучения
    PERFECT_SCORE = "perfect_score"  # За идеальные оценки
    MILESTONE = "milestone"  # За достижение вех
    SOCIAL = "social"  # За социальные активности
    SPECIAL = "special"  # Специальные достижения


class AchievementRarity(PyEnum):
    """Редкость достижений"""
    COMMON = "common"  # Обычное
    RARE = "rare"  # Редкое
    EPIC = "epic"  # Эпическое
    LEGENDARY = "legendary"  # Легендарное


class Achievement(Base):
    """Модель шаблона достижения"""
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    name = Column(String(100), nullable=False)  # Название достижения
    description = Column(Text, nullable=False)  # Описание
    icon_url = Column(String(500), nullable=True)  # URL иконки
    
    # Категоризация
    type = Column(Enum(AchievementType), nullable=False)  # Тип достижения
    rarity = Column(Enum(AchievementRarity), default=AchievementRarity.COMMON)  # Редкость
    
    # Награды
    xp_reward = Column(Integer, default=0)  # Очки опыта за достижение
    badge_url = Column(String(500), nullable=True)  # URL значка
    
    # Условия получения (JSON с критериями)
    criteria = Column(JSON, nullable=False)  # Критерии для получения
    
    # Настройки
    is_active = Column(Boolean, default=True)  # Активно ли достижение
    is_hidden = Column(Boolean, default=False)  # Скрытое достижение
    is_repeatable = Column(Boolean, default=False)  # Можно ли получить повторно
    sort_order = Column(Integer, default=0)  # Порядок сортировки
    
    # Метаданные
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    student_achievements = relationship("StudentAchievement", back_populates="achievement")
    
    def __repr__(self):
        return f"<Achievement(id={self.id}, name='{self.name}', type={self.type.value})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon_url": self.icon_url,
            "type": self.type.value,
            "rarity": self.rarity.value,
            "xp_reward": self.xp_reward,
            "badge_url": self.badge_url,
            "criteria": self.criteria,
            "is_active": self.is_active,
            "is_hidden": self.is_hidden,
            "is_repeatable": self.is_repeatable,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class StudentAchievement(Base):
    """Модель полученного студентом достижения"""
    __tablename__ = "student_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    
    # Информация о получении
    earned_at = Column(DateTime, default=func.now())  # Когда получено
    progress_data = Column(JSON, nullable=True)  # Данные прогресса (для повторяемых)
    
    # Метаданные
    is_showcased = Column(Boolean, default=False)  # Показывать в профиле
    notification_sent = Column(Boolean, default=False)  # Отправлено ли уведомление
    
    # Связи
    student = relationship("Student", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="student_achievements")
    
    def __repr__(self):
        return f"<StudentAchievement(student_id={self.student_id}, achievement_id={self.achievement_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "achievement_id": self.achievement_id,
            "earned_at": self.earned_at.isoformat() if self.earned_at else None,
            "progress_data": self.progress_data,
            "is_showcased": self.is_showcased,
            "notification_sent": self.notification_sent,
            "achievement": self.achievement.to_dict() if self.achievement else None
        }


# Предустановленные достижения
DEFAULT_ACHIEVEMENTS = [
    # Достижения за уроки
    {
        "name": "Первый шаг",
        "description": "Завершите свой первый урок",
        "type": AchievementType.LESSON,
        "rarity": AchievementRarity.COMMON,
        "xp_reward": 50,
        "criteria": {"lessons_completed": 1},
        "icon_url": "/icons/first_lesson.png"
    },
    {
        "name": "Ученик",
        "description": "Завершите 10 уроков",
        "type": AchievementType.LESSON,
        "rarity": AchievementRarity.COMMON,
        "xp_reward": 100,
        "criteria": {"lessons_completed": 10},
        "icon_url": "/icons/student.png"
    },
    {
        "name": "Знаток",
        "description": "Завершите 50 уроков",
        "type": AchievementType.LESSON,
        "rarity": AchievementRarity.RARE,
        "xp_reward": 300,
        "criteria": {"lessons_completed": 50},
        "icon_url": "/icons/expert.png"
    },
    {
        "name": "Мастер",
        "description": "Завершите 100 уроков",
        "type": AchievementType.LESSON,
        "rarity": AchievementRarity.EPIC,
        "xp_reward": 500,
        "criteria": {"lessons_completed": 100},
        "icon_url": "/icons/master.png"
    },
    
    # Достижения за домашние задания
    {
        "name": "Исполнительный",
        "description": "Сдайте первое домашнее задание",
        "type": AchievementType.HOMEWORK,
        "rarity": AchievementRarity.COMMON,
        "xp_reward": 30,
        "criteria": {"homework_submitted": 1},
        "icon_url": "/icons/first_homework.png"
    },
    {
        "name": "Перфекционист",
        "description": "Получите 10 идеальных оценок за домашние задания",
        "type": AchievementType.PERFECT_SCORE,
        "rarity": AchievementRarity.RARE,
        "xp_reward": 250,
        "criteria": {"homework_perfect": 10},
        "icon_url": "/icons/perfectionist.png"
    },
    
    # Достижения за регулярность
    {
        "name": "Постоянство",
        "description": "Занимайтесь 7 дней подряд",
        "type": AchievementType.STREAK,
        "rarity": AchievementRarity.COMMON,
        "xp_reward": 150,
        "criteria": {"current_streak": 7},
        "icon_url": "/icons/streak_7.png"
    },
    {
        "name": "Железная дисциплина",
        "description": "Занимайтесь 30 дней подряд",
        "type": AchievementType.STREAK,
        "rarity": AchievementRarity.EPIC,
        "xp_reward": 600,
        "criteria": {"current_streak": 30},
        "icon_url": "/icons/streak_30.png"
    },
    
    # Достижения за время обучения
    {
        "name": "Активный ученик",
        "description": "Потратьте 50 часов на обучение",
        "type": AchievementType.STUDY_TIME,
        "rarity": AchievementRarity.RARE,
        "xp_reward": 400,
        "criteria": {"study_time_minutes": 3000},  # 50 часов
        "icon_url": "/icons/active_learner.png"
    },
    
    # Вехи уровней
    {
        "name": "Новичок",
        "description": "Достигните 5 уровня",
        "type": AchievementType.MILESTONE,
        "rarity": AchievementRarity.COMMON,
        "xp_reward": 200,
        "criteria": {"level": 5},
        "icon_url": "/icons/level_5.png"
    },
    {
        "name": "Продвинутый",
        "description": "Достигните 10 уровня",
        "type": AchievementType.MILESTONE,
        "rarity": AchievementRarity.RARE,
        "xp_reward": 400,
        "criteria": {"level": 10},
        "icon_url": "/icons/level_10.png"
    },
    {
        "name": "Эксперт",
        "description": "Достигните 25 уровня",
        "type": AchievementType.MILESTONE,
        "rarity": AchievementRarity.EPIC,
        "xp_reward": 800,
        "criteria": {"level": 25},
        "icon_url": "/icons/level_25.png"
    },
    {
        "name": "Легенда",
        "description": "Достигните 50 уровня",
        "type": AchievementType.MILESTONE,
        "rarity": AchievementRarity.LEGENDARY,
        "xp_reward": 1500,
        "criteria": {"level": 50},
        "icon_url": "/icons/level_50.png"
    }
]