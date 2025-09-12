# -*- coding: utf-8 -*-
"""
Learning Progress Models
Модели отслеживания прогресса обучения
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..database.connection import Base


class ProgressType(PyEnum):
    """Типы прогресса"""
    LESSON = "lesson"  # Прогресс по урокам
    SUBJECT = "subject"  # Прогресс по предмету
    SKILL = "skill"  # Прогресс по навыкам
    GOAL = "goal"  # Прогресс по целям
    COURSE = "course"  # Прогресс по курсу


class DifficultyLevel(PyEnum):
    """Уровни сложности"""
    BEGINNER = "beginner"  # Начинающий
    INTERMEDIATE = "intermediate"  # Средний
    ADVANCED = "advanced"  # Продвинутый
    EXPERT = "expert"  # Экспертный


class LearningProgress(Base):
    """Модель прогресса обучения"""
    __tablename__ = "learning_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    
    # Идентификация объекта прогресса
    progress_type = Column(Enum(ProgressType), nullable=False)
    object_id = Column(String(100), nullable=False)  # ID урока/предмета/навыка
    object_name = Column(String(200), nullable=False)  # Название объекта
    
    # Прогресс
    progress_percentage = Column(Float, default=0.0)  # Процент завершения (0-100)
    current_step = Column(Integer, default=0)  # Текущий шаг
    total_steps = Column(Integer, default=1)  # Всего шагов
    
    # Время и активность
    time_spent_minutes = Column(Integer, default=0)  # Время, потраченное в минутах
    last_activity_at = Column(DateTime, default=func.now())  # Последняя активность
    started_at = Column(DateTime, default=func.now())  # Начало изучения
    completed_at = Column(DateTime, nullable=True)  # Завершение изучения
    
    # Сложность и оценки
    difficulty_level = Column(Enum(DifficultyLevel), default=DifficultyLevel.BEGINNER)
    mastery_score = Column(Float, default=0.0)  # Уровень освоения (0-100)
    confidence_level = Column(Float, default=0.0)  # Уровень уверенности (0-100)
    
    # Дополнительные данные
    metadata = Column(JSON, default=dict)  # Дополнительные метаданные
    notes = Column(Text, nullable=True)  # Заметки студента
    
    # Статус
    is_completed = Column(Boolean, default=False)
    is_bookmarked = Column(Boolean, default=False)  # Добавлено в закладки
    
    # Связи
    student = relationship("Student", back_populates="progress_records")
    
    def __repr__(self):
        return f"<LearningProgress(student_id={self.student_id}, type={self.progress_type.value}, object='{self.object_name}')>"
    
    def update_progress(self, completed_steps: int = None, time_spent: int = None):
        """Обновляет прогресс"""
        if completed_steps is not None:
            self.current_step = min(completed_steps, self.total_steps)
            self.progress_percentage = (self.current_step / self.total_steps) * 100
            
            if self.current_step >= self.total_steps:
                self.is_completed = True
                self.completed_at = func.now()
        
        if time_spent is not None:
            self.time_spent_minutes += time_spent
        
        self.last_activity_at = func.now()
    
    def calculate_mastery_score(self, performance_scores: List[float]) -> float:
        """Рассчитывает уровень освоения на основе результатов"""
        if not performance_scores:
            return 0.0
        
        # Взвешенная оценка с учетом последних результатов
        weights = [0.5 ** i for i in range(len(performance_scores))]
        weighted_sum = sum(score * weight for score, weight in zip(performance_scores, weights))
        total_weight = sum(weights)
        
        self.mastery_score = (weighted_sum / total_weight) if total_weight > 0 else 0.0
        return self.mastery_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "progress_type": self.progress_type.value,
            "object_id": self.object_id,
            "object_name": self.object_name,
            "progress_percentage": self.progress_percentage,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "time_spent_minutes": self.time_spent_minutes,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "difficulty_level": self.difficulty_level.value,
            "mastery_score": self.mastery_score,
            "confidence_level": self.confidence_level,
            "metadata": self.metadata,
            "notes": self.notes,
            "is_completed": self.is_completed,
            "is_bookmarked": self.is_bookmarked
        }


class LearningGoal(Base):
    """Модель цели обучения"""
    __tablename__ = "learning_goals"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    
    # Цель
    title = Column(String(200), nullable=False)  # Название цели
    description = Column(Text, nullable=True)  # Описание
    category = Column(String(100), nullable=True)  # Категория (предмет, навык)
    
    # Временные рамки
    target_date = Column(DateTime, nullable=True)  # Целевая дата
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Прогресс
    target_value = Column(Float, nullable=False)  # Целевое значение
    current_value = Column(Float, default=0.0)  # Текущее значение
    unit = Column(String(50), default="items")  # Единица измерения
    
    # Статус
    is_completed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Настройки
    is_public = Column(Boolean, default=False)  # Публичная цель
    reminder_enabled = Column(Boolean, default=True)  # Напоминания
    
    def __repr__(self):
        return f"<LearningGoal(id={self.id}, title='{self.title}', progress={self.current_value}/{self.target_value})>"
    
    @property
    def progress_percentage(self) -> float:
        """Возвращает прогресс в процентах"""
        if self.target_value <= 0:
            return 0.0
        return min(100.0, (self.current_value / self.target_value) * 100)
    
    def update_progress(self, value: float):
        """Обновляет прогресс цели"""
        self.current_value = value
        if self.current_value >= self.target_value and not self.is_completed:
            self.is_completed = True
            self.completed_at = func.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "unit": self.unit,
            "progress_percentage": self.progress_percentage,
            "is_completed": self.is_completed,
            "is_active": self.is_active,
            "is_public": self.is_public,
            "reminder_enabled": self.reminder_enabled
        }


class StudySession(Base):
    """Модель сессии обучения"""
    __tablename__ = "study_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    
    # Сессия
    subject = Column(String(100), nullable=True)  # Предмет
    activity_type = Column(String(50), nullable=False)  # Тип активности (lesson, homework, etc.)
    activity_id = Column(String(100), nullable=True)  # ID активности
    
    # Время
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=0)
    
    # Результаты
    focus_score = Column(Float, default=0.0)  # Оценка концентрации (0-100)
    productivity_score = Column(Float, default=0.0)  # Оценка продуктивности (0-100)
    satisfaction_score = Column(Float, default=0.0)  # Оценка удовлетворенности (0-100)
    
    # Метаданные
    notes = Column(Text, nullable=True)  # Заметки
    metadata = Column(JSON, default=dict)  # Дополнительные данные
    
    def __repr__(self):
        return f"<StudySession(id={self.id}, student_id={self.student_id}, duration={self.duration_minutes}min)>"
    
    def end_session(self, focus_score: float = None, productivity_score: float = None):
        """Завершает сессию обучения"""
        self.ended_at = func.now()
        if self.started_at:
            duration = (self.ended_at - self.started_at).total_seconds() / 60
            self.duration_minutes = int(duration)
        
        if focus_score is not None:
            self.focus_score = focus_score
        if productivity_score is not None:
            self.productivity_score = productivity_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "subject": self.subject,
            "activity_type": self.activity_type,
            "activity_id": self.activity_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_minutes": self.duration_minutes,
            "focus_score": self.focus_score,
            "productivity_score": self.productivity_score,
            "satisfaction_score": self.satisfaction_score,
            "notes": self.notes,
            "metadata": self.metadata
        }