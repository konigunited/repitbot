# -*- coding: utf-8 -*-
"""
Student Model
Модель студента с профилем и настройками
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, DECIMAL, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, Optional

from ..database.connection import Base


class Student(Base):
    """Модель студента"""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)  # ID пользователя из User Service
    
    # Профиль студента
    display_name = Column(String(100), nullable=True)  # Отображаемое имя
    bio = Column(Text, nullable=True)  # Биография/описание
    avatar_url = Column(String(500), nullable=True)  # URL аватара
    
    # Геймификация
    level = Column(Integer, default=1)  # Текущий уровень
    experience_points = Column(Integer, default=0)  # Очки опыта
    total_xp_earned = Column(Integer, default=0)  # Всего заработано XP
    
    # Статистика обучения
    lessons_completed = Column(Integer, default=0)  # Завершенных уроков
    homework_submitted = Column(Integer, default=0)  # Сданных домашних заданий
    homework_perfect = Column(Integer, default=0)  # Идеальных домашних заданий
    materials_studied = Column(Integer, default=0)  # Изученных материалов
    study_time_minutes = Column(Integer, default=0)  # Время обучения в минутах
    
    # Стрики и достижения
    current_streak = Column(Integer, default=0)  # Текущий стрик (дни подряд)
    best_streak = Column(Integer, default=0)  # Лучший стрик
    last_activity_date = Column(DateTime, nullable=True)  # Последняя активность
    
    # Настройки и предпочтения
    preferred_subjects = Column(JSON, default=list)  # Предпочитаемые предметы
    learning_goals = Column(JSON, default=list)  # Цели обучения
    study_schedule = Column(JSON, default=dict)  # Расписание занятий
    notification_preferences = Column(JSON, default=dict)  # Настройки уведомлений
    
    # Статус и настройки
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    privacy_settings = Column(JSON, default=dict)  # Настройки приватности
    
    # Даты
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи с другими таблицами
    achievements = relationship("StudentAchievement", back_populates="student", cascade="all, delete-orphan")
    progress_records = relationship("LearningProgress", back_populates="student", cascade="all, delete-orphan")
    gamification_data = relationship("GamificationData", back_populates="student", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Student(id={self.id}, user_id={self.user_id}, level={self.level}, xp={self.experience_points})>"
    
    def get_xp_for_next_level(self) -> int:
        """Рассчитывает XP, необходимый для следующего уровня"""
        from ..core.config import settings
        base_xp = settings.DEFAULT_LEVEL_XP_THRESHOLD
        multiplier = settings.XP_MULTIPLIER
        return int(base_xp * (multiplier ** (self.level - 1)))
    
    def get_xp_progress_percentage(self) -> float:
        """Возвращает процент прогресса к следующему уровню"""
        current_level_xp = self.get_xp_for_current_level()
        next_level_xp = self.get_xp_for_next_level()
        current_xp_in_level = self.experience_points - current_level_xp
        xp_needed_for_level = next_level_xp - current_level_xp
        
        if xp_needed_for_level <= 0:
            return 100.0
        
        return min(100.0, (current_xp_in_level / xp_needed_for_level) * 100)
    
    def get_xp_for_current_level(self) -> int:
        """Рассчитывает XP, необходимый для текущего уровня"""
        if self.level <= 1:
            return 0
        
        from ..core.config import settings
        base_xp = settings.DEFAULT_LEVEL_XP_THRESHOLD
        multiplier = settings.XP_MULTIPLIER
        
        total_xp = 0
        for level in range(1, self.level):
            total_xp += int(base_xp * (multiplier ** (level - 1)))
        
        return total_xp
    
    def can_level_up(self) -> bool:
        """Проверяет, может ли студент повысить уровень"""
        return (
            self.experience_points >= self.get_xp_for_next_level() and 
            self.level < settings.MAX_LEVEL
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "display_name": self.display_name,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "level": self.level,
            "experience_points": self.experience_points,
            "total_xp_earned": self.total_xp_earned,
            "lessons_completed": self.lessons_completed,
            "homework_submitted": self.homework_submitted,
            "homework_perfect": self.homework_perfect,
            "materials_studied": self.materials_studied,
            "study_time_minutes": self.study_time_minutes,
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "last_activity_date": self.last_activity_date.isoformat() if self.last_activity_date else None,
            "preferred_subjects": self.preferred_subjects,
            "learning_goals": self.learning_goals,
            "study_schedule": self.study_schedule,
            "notification_preferences": self.notification_preferences,
            "is_active": self.is_active,
            "is_premium": self.is_premium,
            "privacy_settings": self.privacy_settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "xp_for_next_level": self.get_xp_for_next_level(),
            "xp_progress_percentage": self.get_xp_progress_percentage(),
            "can_level_up": self.can_level_up()
        }