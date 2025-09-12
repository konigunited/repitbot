# -*- coding: utf-8 -*-
"""
Student Service
Основная бизнес-логика для работы со студентами
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload

from ..models import Student, GamificationData
from ..schemas import (
    StudentCreate, 
    StudentUpdate, 
    StudentResponse,
    StudentSummary,
    XPTransaction,
    LevelUpResponse,
    StudentSearchFilters,
    StudentDashboard,
    StudentStats
)
from ..core.config import settings
from ..database.connection import get_db_session

logger = logging.getLogger(__name__)


class StudentService:
    """Сервис для работы со студентами"""
    
    def __init__(self):
        self.logger = logger
    
    async def create_student(self, student_data: StudentCreate) -> StudentResponse:
        """Создание нового студента"""
        async with get_db_session() as session:
            try:
                # Проверяем, что студент с таким user_id не существует
                existing_student = await self.get_student_by_user_id(student_data.user_id)
                if existing_student:
                    raise ValueError(f"Student with user_id {student_data.user_id} already exists")
                
                # Создаем студента
                student = Student(**student_data.model_dump())
                session.add(student)
                await session.flush()  # Получаем ID
                
                # Создаем данные геймификации
                gamification_data = GamificationData(student_id=student.id)
                session.add(gamification_data)
                
                await session.commit()
                await session.refresh(student)
                
                self.logger.info(f"Created new student with user_id {student_data.user_id}")
                return self._student_to_response(student)
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error creating student: {e}")
                raise
    
    async def get_student_by_id(self, student_id: int) -> Optional[StudentResponse]:
        """Получение студента по ID"""
        async with get_db_session() as session:
            try:
                query = select(Student).options(
                    selectinload(Student.gamification_data)
                ).where(Student.id == student_id)
                
                result = await session.execute(query)
                student = result.scalar_one_or_none()
                
                if not student:
                    return None
                
                return self._student_to_response(student)
                
            except Exception as e:
                self.logger.error(f"Error getting student by ID {student_id}: {e}")
                raise
    
    async def get_student_by_user_id(self, user_id: int) -> Optional[StudentResponse]:
        """Получение студента по user_id"""
        async with get_db_session() as session:
            try:
                query = select(Student).options(
                    selectinload(Student.gamification_data)
                ).where(Student.user_id == user_id)
                
                result = await session.execute(query)
                student = result.scalar_one_or_none()
                
                if not student:
                    return None
                
                return self._student_to_response(student)
                
            except Exception as e:
                self.logger.error(f"Error getting student by user_id {user_id}: {e}")
                raise
    
    async def update_student(self, student_id: int, student_data: StudentUpdate) -> Optional[StudentResponse]:
        """Обновление данных студента"""
        async with get_db_session() as session:
            try:
                # Получаем студента
                query = select(Student).where(Student.id == student_id)
                result = await session.execute(query)
                student = result.scalar_one_or_none()
                
                if not student:
                    return None
                
                # Обновляем поля
                update_data = student_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(student, field, value)
                
                await session.commit()
                await session.refresh(student)
                
                self.logger.info(f"Updated student {student_id}")
                return self._student_to_response(student)
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error updating student {student_id}: {e}")
                raise
    
    async def delete_student(self, student_id: int) -> bool:
        """Удаление студента (мягкое удаление)"""
        async with get_db_session() as session:
            try:
                # Помечаем студента как неактивного
                query = update(Student).where(Student.id == student_id).values(
                    is_active=False,
                    updated_at=func.now()
                )
                
                result = await session.execute(query)
                await session.commit()
                
                if result.rowcount > 0:
                    self.logger.info(f"Deactivated student {student_id}")
                    return True
                
                return False
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error deleting student {student_id}: {e}")
                raise
    
    async def search_students(self, filters: StudentSearchFilters, limit: int = 50, offset: int = 0) -> List[StudentSummary]:
        """Поиск студентов с фильтрами"""
        async with get_db_session() as session:
            try:
                query = select(Student)
                
                # Применяем фильтры
                conditions = []
                
                if filters.level_min is not None:
                    conditions.append(Student.level >= filters.level_min)
                
                if filters.level_max is not None:
                    conditions.append(Student.level <= filters.level_max)
                
                if filters.is_premium is not None:
                    conditions.append(Student.is_premium == filters.is_premium)
                
                if filters.is_active is not None:
                    conditions.append(Student.is_active == filters.is_active)
                
                if filters.has_streak is not None:
                    if filters.has_streak:
                        conditions.append(Student.current_streak > 0)
                    else:
                        conditions.append(Student.current_streak == 0)
                
                if filters.subjects:
                    conditions.append(Student.preferred_subjects.op('&&')(filters.subjects))
                
                if filters.created_after:
                    conditions.append(Student.created_at >= filters.created_after)
                
                if filters.created_before:
                    conditions.append(Student.created_at <= filters.created_before)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                # Пагинация
                query = query.offset(offset).limit(limit).order_by(Student.level.desc())
                
                result = await session.execute(query)
                students = result.scalars().all()
                
                return [self._student_to_summary(student) for student in students]
                
            except Exception as e:
                self.logger.error(f"Error searching students: {e}")
                raise
    
    async def add_experience(self, student_id: int, xp_transaction: XPTransaction) -> Optional[LevelUpResponse]:
        """Добавление опыта студенту"""
        async with get_db_session() as session:
            try:
                # Получаем студента
                query = select(Student).where(Student.id == student_id)
                result = await session.execute(query)
                student = result.scalar_one_or_none()
                
                if not student:
                    self.logger.warning(f"Student {student_id} not found for XP transaction")
                    return None
                
                old_level = student.level
                old_xp = student.experience_points
                
                # Добавляем опыт
                student.experience_points += xp_transaction.amount
                student.total_xp_earned += max(0, xp_transaction.amount)  # Только положительные значения
                
                # Проверяем повышение уровня
                new_achievements = []
                while student.can_level_up():
                    student.level += 1
                    self.logger.info(f"Student {student_id} leveled up to {student.level}")
                    
                    # Можно добавить логику наград за повышение уровня
                    new_achievements.append(f"Reached level {student.level}")
                
                # Обновляем время последней активности
                student.last_activity_date = func.now()
                
                await session.commit()
                
                # Логируем транзакцию
                self.logger.info(
                    f"XP transaction for student {student_id}: "
                    f"{xp_transaction.amount} XP for {xp_transaction.reason}"
                )
                
                # Возвращаем информацию о повышении уровня, если оно произошло
                if student.level > old_level:
                    return LevelUpResponse(
                        old_level=old_level,
                        new_level=student.level,
                        xp_gained=xp_transaction.amount,
                        achievements_unlocked=new_achievements,
                        rewards={"level_bonus_xp": (student.level - old_level) * 50}
                    )
                
                return None
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error adding XP to student {student_id}: {e}")
                raise
    
    async def update_student_stats(self, student_id: int, stats_update: Dict[str, Any]) -> bool:
        """Обновление статистики студента"""
        async with get_db_session() as session:
            try:
                # Получаем студента
                query = select(Student).where(Student.id == student_id)
                result = await session.execute(query)
                student = result.scalar_one_or_none()
                
                if not student:
                    return False
                
                # Обновляем статистику
                for field, value in stats_update.items():
                    if hasattr(student, field):
                        current_value = getattr(student, field, 0)
                        if isinstance(value, (int, float)):
                            setattr(student, field, current_value + value)
                        else:
                            setattr(student, field, value)
                
                # Обновляем стрик, если была активность сегодня
                if 'last_activity_date' not in stats_update:
                    await self._update_streak(student)
                
                student.last_activity_date = func.now()
                await session.commit()
                
                self.logger.info(f"Updated stats for student {student_id}: {stats_update}")
                return True
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error updating student stats {student_id}: {e}")
                raise
    
    async def get_student_dashboard(self, student_id: int) -> Optional[StudentDashboard]:
        """Получение дашборда студента"""
        async with get_db_session() as session:
            try:
                # Получаем студента
                student = await self.get_student_by_id(student_id)
                if not student:
                    return None
                
                # Получаем недавние активности (заглушка)
                recent_activities = []
                
                # Получаем текущие цели (заглушка)
                current_goals = []
                
                # Сводка достижений (заглушка)
                achievements_summary = {
                    "total": 0,
                    "earned": 0,
                    "recent": []
                }
                
                # Статистика обучения
                learning_statistics = {
                    "total_lessons": student.lessons_completed,
                    "total_homework": student.homework_submitted,
                    "perfect_homework": student.homework_perfect,
                    "study_time_hours": round(student.study_time_minutes / 60, 1),
                    "current_streak": student.current_streak,
                    "level": student.level,
                    "xp": student.experience_points
                }
                
                # Рекомендации (заглушка)
                recommendations = []
                
                return StudentDashboard(
                    student=student,
                    recent_activities=recent_activities,
                    current_goals=current_goals,
                    achievements_summary=achievements_summary,
                    learning_statistics=learning_statistics,
                    recommendations=recommendations
                )
                
            except Exception as e:
                self.logger.error(f"Error getting dashboard for student {student_id}: {e}")
                raise
    
    async def _update_streak(self, student: Student):
        """Обновление стрика студента"""
        today = datetime.utcnow().date()
        
        if student.last_activity_date:
            last_activity_date = student.last_activity_date.date()
            
            if last_activity_date == today:
                # Активность уже была сегодня
                return
            elif last_activity_date == today - timedelta(days=1):
                # Активность была вчера - продолжаем стрик
                student.current_streak += 1
            else:
                # Стрик прерван
                student.current_streak = 1
        else:
            # Первая активность
            student.current_streak = 1
        
        # Обновляем лучший стрик
        student.best_streak = max(student.best_streak, student.current_streak)
    
    def _student_to_response(self, student: Student) -> StudentResponse:
        """Преобразование модели Student в StudentResponse"""
        student_dict = student.to_dict()
        return StudentResponse(**student_dict)
    
    def _student_to_summary(self, student: Student) -> StudentSummary:
        """Преобразование модели Student в StudentSummary"""
        return StudentSummary(
            id=student.id,
            user_id=student.user_id,
            display_name=student.display_name,
            avatar_url=student.avatar_url,
            level=student.level,
            experience_points=student.experience_points,
            current_streak=student.current_streak,
            is_premium=student.is_premium
        )