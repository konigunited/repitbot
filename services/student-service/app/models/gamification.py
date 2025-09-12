# -*- coding: utf-8 -*-
"""
Gamification Models
Модели геймификации и социальных функций
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from ..database.connection import Base


class XPTransaction(Base):
    """Модель транзакции XP"""
    __tablename__ = "xp_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    
    # Данные транзакции
    action = Column(String(100), nullable=False)  # Действие за которое начислен XP
    amount = Column(Integer, nullable=False)  # Количество XP
    lesson_id = Column(Integer, nullable=True)  # ID урока (если применимо)
    homework_id = Column(Integer, nullable=True)  # ID домашнего задания
    
    # Описание
    description = Column(Text, nullable=True)  # Описание транзакции
    
    # Метаданные
    created_at = Column(DateTime, default=func.now())
    metadata = Column(JSON, default=dict)  # Дополнительные данные
    
    def __repr__(self):
        return f"<XPTransaction(student_id={self.student_id}, action='{self.action}', amount={self.amount})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "action": self.action,
            "amount": self.amount,
            "lesson_id": self.lesson_id,
            "homework_id": self.homework_id,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata
        }


class Level(Base):
    """Модель уровня"""
    __tablename__ = "levels"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Данные уровня
    level_number = Column(Integer, nullable=False, unique=True)
    title = Column(String(100), nullable=False)  # Название уровня
    description = Column(Text, nullable=True)  # Описание уровня
    
    # Требования
    xp_required = Column(Integer, nullable=False)  # XP необходимый для достижения
    
    # Награды уровня
    rewards = Column(JSON, default=dict)  # Награды за достижение уровня
    
    # Оформление
    color = Column(String(7), nullable=True)  # Цвет в hex
    icon = Column(String(100), nullable=True)  # Иконка или emoji
    
    # Метаданные
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<Level(number={self.level_number}, title='{self.title}', xp_required={self.xp_required})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "level_number": self.level_number,
            "title": self.title,
            "description": self.description,
            "xp_required": self.xp_required,
            "rewards": self.rewards,
            "color": self.color,
            "icon": self.icon,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Badge(Base):
    """Модель значка/достижения"""
    __tablename__ = "badges"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    code = Column(String(100), nullable=False, unique=True)  # Уникальный код значка
    name = Column(String(200), nullable=False)  # Название значка
    description = Column(Text, nullable=False)  # Описание значка
    
    # Категория и редкость
    category = Column(String(50), nullable=False)  # Категория (xp, level, streak, etc.)
    rarity = Column(String(20), nullable=False, default="common")  # common, uncommon, rare, epic, legendary
    
    # Оформление
    icon = Column(String(100), nullable=True)  # Иконка или emoji
    color = Column(String(7), nullable=True)  # Цвет в hex
    image_url = Column(String(500), nullable=True)  # URL изображения значка
    
    # Условия получения
    criteria = Column(JSON, default=dict)  # Критерии получения значка
    
    # Статус
    is_active = Column(Boolean, default=True)  # Активен ли значок
    is_secret = Column(Boolean, default=False)  # Секретный значок
    
    # Метаданные
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    student_badges = relationship("StudentBadge", back_populates="badge")
    
    def __repr__(self):
        return f"<Badge(code='{self.code}', name='{self.name}', rarity='{self.rarity}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "rarity": self.rarity,
            "icon": self.icon,
            "color": self.color,
            "image_url": self.image_url,
            "criteria": self.criteria,
            "is_active": self.is_active,
            "is_secret": self.is_secret,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class StudentBadge(Base):
    """Модель связи студент-значок"""
    __tablename__ = "student_badges"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    
    # Данные получения
    earned_at = Column(DateTime, default=func.now())  # Когда получен
    reason = Column(Text, nullable=True)  # Причина/обстоятельства получения
    
    # Отображение
    is_displayed = Column(Boolean, default=True)  # Показывать в профиле
    display_order = Column(Integer, default=0)  # Порядок отображения
    
    # Метаданные
    metadata = Column(JSON, default=dict)  # Дополнительные данные
    
    # Связи
    badge = relationship("Badge", back_populates="student_badges")
    
    def __repr__(self):
        return f"<StudentBadge(student_id={self.student_id}, badge_id={self.badge_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "badge_id": self.badge_id,
            "earned_at": self.earned_at.isoformat() if self.earned_at else None,
            "reason": self.reason,
            "is_displayed": self.is_displayed,
            "display_order": self.display_order,
            "metadata": self.metadata,
            "badge": self.badge.to_dict() if self.badge else None
        }


class Competition(Base):
    """Модель соревнования"""
    __tablename__ = "competitions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    title = Column(String(200), nullable=False)  # Название соревнования
    description = Column(Text, nullable=False)  # Описание
    competition_type = Column(String(50), nullable=False)  # Тип соревнования
    
    # Настройки соревнования
    max_participants = Column(Integer, nullable=True)  # Максимум участников
    entry_fee_xp = Column(Integer, default=0)  # Входная плата в XP
    
    # Временные рамки
    registration_start = Column(DateTime, nullable=False)
    registration_end = Column(DateTime, nullable=False)
    competition_start = Column(DateTime, nullable=False)
    competition_end = Column(DateTime, nullable=False)
    
    # Награды
    first_place_reward = Column(JSON, default=dict)  # Награда за 1 место
    second_place_reward = Column(JSON, default=dict)  # Награда за 2 место
    third_place_reward = Column(JSON, default=dict)  # Награда за 3 место
    participation_reward = Column(JSON, default=dict)  # Награда за участие
    
    # Правила и критерии
    rules = Column(Text, nullable=True)  # Правила соревнования
    scoring_criteria = Column(JSON, default=dict)  # Критерии оценки
    
    # Статус
    status = Column(String(20), default="planned")  # planned, registration, active, completed, cancelled
    is_public = Column(Boolean, default=True)  # Публичное соревнование
    
    # Метаданные
    created_by = Column(Integer, nullable=True)  # Кто создал (admin_id)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    participants = relationship("CompetitionParticipant", back_populates="competition")
    
    def __repr__(self):
        return f"<Competition(id={self.id}, title='{self.title}', status='{self.status}')>"
    
    @property
    def participants_count(self) -> int:
        return len(self.participants) if self.participants else 0
    
    @property
    def is_registration_open(self) -> bool:
        now = datetime.utcnow()
        return (self.registration_start <= now <= self.registration_end and 
                self.status == "registration")
    
    @property
    def is_active(self) -> bool:
        now = datetime.utcnow()
        return (self.competition_start <= now <= self.competition_end and 
                self.status == "active")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "competition_type": self.competition_type,
            "max_participants": self.max_participants,
            "entry_fee_xp": self.entry_fee_xp,
            "registration_start": self.registration_start.isoformat() if self.registration_start else None,
            "registration_end": self.registration_end.isoformat() if self.registration_end else None,
            "competition_start": self.competition_start.isoformat() if self.competition_start else None,
            "competition_end": self.competition_end.isoformat() if self.competition_end else None,
            "first_place_reward": self.first_place_reward,
            "second_place_reward": self.second_place_reward,
            "third_place_reward": self.third_place_reward,
            "participation_reward": self.participation_reward,
            "rules": self.rules,
            "scoring_criteria": self.scoring_criteria,
            "status": self.status,
            "is_public": self.is_public,
            "created_by": self.created_by,
            "participants_count": self.participants_count,
            "is_registration_open": self.is_registration_open,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class CompetitionParticipant(Base):
    """Модель участника соревнования"""
    __tablename__ = "competition_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    
    # Результаты
    score = Column(Float, default=0.0)  # Текущий счет
    rank = Column(Integer, nullable=True)  # Текущее место
    final_rank = Column(Integer, nullable=True)  # Итоговое место
    
    # Данные участия
    registered_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)  # Когда начал участвовать
    completed_at = Column(DateTime, nullable=True)  # Когда завершил
    
    # Статус
    status = Column(String(20), default="registered")  # registered, active, completed, disqualified
    is_winner = Column(Boolean, default=False)  # Является ли победителем
    reward_claimed = Column(Boolean, default=False)  # Получена ли награда
    
    # Данные о производительности
    performance_data = Column(JSON, default=dict)  # Детальные данные производительности
    
    # Связи
    competition = relationship("Competition", back_populates="participants")
    
    def __repr__(self):
        return f"<CompetitionParticipant(student_id={self.student_id}, competition_id={self.competition_id}, rank={self.rank})>"
    
    def update_score(self, new_score: float):
        """Обновляет счет участника"""
        self.score = new_score
        if self.status == "registered":
            self.status = "active"
            self.started_at = datetime.utcnow()
    
    def complete_participation(self, final_rank: int):
        """Завершает участие в соревновании"""
        self.final_rank = final_rank
        self.rank = final_rank
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        
        # Проверяем, является ли победителем (топ-3)
        self.is_winner = final_rank <= 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "competition_id": self.competition_id,
            "score": self.score,
            "rank": self.rank,
            "final_rank": self.final_rank,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "is_winner": self.is_winner,
            "reward_claimed": self.reward_claimed,
            "performance_data": self.performance_data,
            "competition": self.competition.to_dict() if self.competition else None
        }


class GamificationData(Base):
    """Модель данных геймификации студента"""
    __tablename__ = "gamification_data"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, unique=True)
    
    # Очки и награды
    total_points = Column(Integer, default=0)  # Общее количество очков
    weekly_points = Column(Integer, default=0)  # Очки за неделю
    monthly_points = Column(Integer, default=0)  # Очки за месяц
    
    # Рейтинги
    global_rank = Column(Integer, nullable=True)  # Глобальный рейтинг
    weekly_rank = Column(Integer, nullable=True)  # Рейтинг за неделю
    monthly_rank = Column(Integer, nullable=True)  # Рейтинг за месяц
    subject_ranks = Column(JSON, default=dict)  # Рейтинги по предметам
    
    # Статистика стриков
    study_streak_days = Column(Integer, default=0)  # Дни подряд обучения
    homework_streak = Column(Integer, default=0)  # Домашние задания подряд
    perfect_streak = Column(Integer, default=0)  # Идеальные работы подряд
    
    # Лучшие результаты
    best_study_streak = Column(Integer, default=0)  # Лучший стрик обучения
    best_homework_streak = Column(Integer, default=0)  # Лучший стрик домашних заданий
    best_perfect_streak = Column(Integer, default=0)  # Лучший стрик идеальных работ
    
    # Временные метки
    last_points_reset = Column(DateTime, default=func.now())  # Последний сброс очков
    last_streak_update = Column(DateTime, default=func.now())  # Последнее обновление стрика
    
    # Настройки соревнований
    participate_in_competitions = Column(Boolean, default=True)  # Участие в соревнованиях
    show_in_leaderboard = Column(Boolean, default=True)  # Показывать в рейтинге
    
    # Связи
    student = relationship("Student", back_populates="gamification_data")
    
    def __repr__(self):
        return f"<GamificationData(student_id={self.student_id}, total_points={self.total_points}, rank={self.global_rank})>"
    
    def add_points(self, points: int, category: str = "general"):
        """Добавляет очки студенту"""
        self.total_points += points
        self.weekly_points += points
        self.monthly_points += points
    
    def reset_weekly_points(self):
        """Сбрасывает недельные очки"""
        self.weekly_points = 0
        self.weekly_rank = None
    
    def reset_monthly_points(self):
        """Сбрасывает месячные очки"""
        self.monthly_points = 0
        self.monthly_rank = None
    
    def update_streak(self, streak_type: str, success: bool = True):
        """Обновляет стрик"""
        if streak_type == "study":
            if success:
                self.study_streak_days += 1
                self.best_study_streak = max(self.best_study_streak, self.study_streak_days)
            else:
                self.study_streak_days = 0
        
        elif streak_type == "homework":
            if success:
                self.homework_streak += 1
                self.best_homework_streak = max(self.best_homework_streak, self.homework_streak)
            else:
                self.homework_streak = 0
        
        elif streak_type == "perfect":
            if success:
                self.perfect_streak += 1
                self.best_perfect_streak = max(self.best_perfect_streak, self.perfect_streak)
            else:
                self.perfect_streak = 0
        
        self.last_streak_update = func.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "total_points": self.total_points,
            "weekly_points": self.weekly_points,
            "monthly_points": self.monthly_points,
            "global_rank": self.global_rank,
            "weekly_rank": self.weekly_rank,
            "monthly_rank": self.monthly_rank,
            "subject_ranks": self.subject_ranks,
            "study_streak_days": self.study_streak_days,
            "homework_streak": self.homework_streak,
            "perfect_streak": self.perfect_streak,
            "best_study_streak": self.best_study_streak,
            "best_homework_streak": self.best_homework_streak,
            "best_perfect_streak": self.best_perfect_streak,
            "last_points_reset": self.last_points_reset.isoformat() if self.last_points_reset else None,
            "last_streak_update": self.last_streak_update.isoformat() if self.last_streak_update else None,
            "participate_in_competitions": self.participate_in_competitions,
            "show_in_leaderboard": self.show_in_leaderboard
        }


class Leaderboard(Base):
    """Модель рейтинговой таблицы"""
    __tablename__ = "leaderboards"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Тип рейтинга
    leaderboard_type = Column(String(50), nullable=False)  # global, weekly, monthly, subject
    category = Column(String(100), nullable=True)  # Категория (предмет, навык)
    
    # Позиция
    rank = Column(Integer, nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    score = Column(Integer, nullable=False)  # Очки или другая метрика
    
    # Период
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Метаданные
    additional_data = Column(JSON, default=dict)  # Дополнительные данные
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<Leaderboard(type={self.leaderboard_type}, rank={self.rank}, student_id={self.student_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "leaderboard_type": self.leaderboard_type,
            "category": self.category,
            "rank": self.rank,
            "student_id": self.student_id,
            "score": self.score,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "additional_data": self.additional_data,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Challenge(Base):
    """Модель вызова/соревнования"""
    __tablename__ = "challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    title = Column(String(200), nullable=False)  # Название вызова
    description = Column(Text, nullable=False)  # Описание
    challenge_type = Column(String(50), nullable=False)  # Тип (daily, weekly, special)
    
    # Цели и условия
    target_metric = Column(String(100), nullable=False)  # Целевая метрика
    target_value = Column(Integer, nullable=False)  # Целевое значение
    criteria = Column(JSON, default=dict)  # Дополнительные критерии
    
    # Награды
    xp_reward = Column(Integer, default=0)  # Награда в XP
    points_reward = Column(Integer, default=0)  # Награда в очках
    badge_url = Column(String(500), nullable=True)  # URL значка
    
    # Временные рамки
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Статус
    is_active = Column(Boolean, default=True)
    is_global = Column(Boolean, default=False)  # Глобальный вызов
    max_participants = Column(Integer, nullable=True)  # Максимум участников
    
    # Метаданные
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    participations = relationship("ChallengeParticipation", back_populates="challenge")
    
    def __repr__(self):
        return f"<Challenge(id={self.id}, title='{self.title}', type={self.challenge_type})>"
    
    @property
    def is_ongoing(self) -> bool:
        """Проверяет, идет ли вызов сейчас"""
        now = datetime.utcnow()
        return self.start_date <= now <= self.end_date
    
    @property
    def participants_count(self) -> int:
        """Возвращает количество участников"""
        return len(self.participations) if self.participations else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "challenge_type": self.challenge_type,
            "target_metric": self.target_metric,
            "target_value": self.target_value,
            "criteria": self.criteria,
            "xp_reward": self.xp_reward,
            "points_reward": self.points_reward,
            "badge_url": self.badge_url,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_active": self.is_active,
            "is_global": self.is_global,
            "max_participants": self.max_participants,
            "is_ongoing": self.is_ongoing,
            "participants_count": self.participants_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ChallengeParticipation(Base):
    """Модель участия в вызове"""
    __tablename__ = "challenge_participations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=False)
    
    # Прогресс
    current_value = Column(Integer, default=0)  # Текущее значение
    progress_data = Column(JSON, default=dict)  # Детальные данные прогресса
    
    # Статус
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    reward_claimed = Column(Boolean, default=False)
    
    # Метаданные
    joined_at = Column(DateTime, default=func.now())
    last_update = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    challenge = relationship("Challenge", back_populates="participations")
    
    def __repr__(self):
        return f"<ChallengeParticipation(student_id={self.student_id}, challenge_id={self.challenge_id})>"
    
    @property
    def progress_percentage(self) -> float:
        """Возвращает прогресс в процентах"""
        if not self.challenge or self.challenge.target_value <= 0:
            return 0.0
        return min(100.0, (self.current_value / self.challenge.target_value) * 100)
    
    def update_progress(self, value: int):
        """Обновляет прогресс участия"""
        self.current_value = value
        self.last_update = func.now()
        
        if (self.challenge and 
            self.current_value >= self.challenge.target_value and 
            not self.is_completed):
            self.is_completed = True
            self.completed_at = func.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "challenge_id": self.challenge_id,
            "current_value": self.current_value,
            "progress_data": self.progress_data,
            "progress_percentage": self.progress_percentage,
            "is_completed": self.is_completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "reward_claimed": self.reward_claimed,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "challenge": self.challenge.to_dict() if self.challenge else None
        }