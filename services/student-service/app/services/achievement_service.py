# -*- coding: utf-8 -*-
"""
Achievement Service
Сервис для работы с системой достижений
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.orm import selectinload

from ..models import (
    Achievement, 
    StudentAchievement, 
    Student,
    AchievementType,
    AchievementRarity,
    DEFAULT_ACHIEVEMENTS
)
from ..schemas import (
    AchievementCreate,
    AchievementUpdate,
    AchievementResponse,
    StudentAchievementCreate,
    StudentAchievementResponse,
    AchievementUnlocked,
    AchievementFilters,
    AchievementStats,
    BulkAchievementCheck
)
from ..database.connection import get_db_session

logger = logging.getLogger(__name__)


class AchievementService:
    """Сервис для работы с достижениями"""
    
    def __init__(self):
        self.logger = logger
    
    async def initialize_default_achievements(self):
        """Инициализация стандартных достижений"""
        async with get_db_session() as session:
            try:
                # Проверяем, есть ли уже достижения
                query = select(func.count(Achievement.id))
                result = await session.execute(query)
                count = result.scalar()
                
                if count > 0:
                    self.logger.info("Default achievements already exist")
                    return
                
                # Создаем стандартные достижения
                for achievement_data in DEFAULT_ACHIEVEMENTS:
                    achievement = Achievement(**achievement_data)
                    session.add(achievement)
                
                await session.commit()
                self.logger.info(f"Created {len(DEFAULT_ACHIEVEMENTS)} default achievements")
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error initializing default achievements: {e}")
                raise
    
    async def create_achievement(self, achievement_data: AchievementCreate) -> AchievementResponse:
        """Создание нового достижения"""
        async with get_db_session() as session:
            try:
                achievement = Achievement(**achievement_data.model_dump())
                session.add(achievement)
                await session.commit()
                await session.refresh(achievement)
                
                self.logger.info(f"Created achievement: {achievement.name}")
                return self._achievement_to_response(achievement)
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error creating achievement: {e}")
                raise
    
    async def get_achievement(self, achievement_id: int) -> Optional[AchievementResponse]:
        """Получение достижения по ID"""
        async with get_db_session() as session:
            try:
                query = select(Achievement).where(Achievement.id == achievement_id)
                result = await session.execute(query)
                achievement = result.scalar_one_or_none()
                
                if not achievement:
                    return None
                
                return self._achievement_to_response(achievement)
                
            except Exception as e:
                self.logger.error(f"Error getting achievement {achievement_id}: {e}")
                raise
    
    async def get_achievements(self, filters: Optional[AchievementFilters] = None) -> List[AchievementResponse]:
        """Получение списка достижений с фильтрами"""
        async with get_db_session() as session:
            try:
                query = select(Achievement)
                
                # Применяем фильтры
                if filters:
                    conditions = []
                    
                    if filters.type:
                        conditions.append(Achievement.type == filters.type)
                    
                    if filters.rarity:
                        conditions.append(Achievement.rarity == filters.rarity)
                    
                    if filters.is_active is not None:
                        conditions.append(Achievement.is_active == filters.is_active)
                    
                    if filters.is_hidden is not None:
                        conditions.append(Achievement.is_hidden == filters.is_hidden)
                    
                    if filters.is_repeatable is not None:
                        conditions.append(Achievement.is_repeatable == filters.is_repeatable)
                    
                    if conditions:
                        query = query.where(and_(*conditions))
                
                query = query.order_by(Achievement.sort_order, Achievement.name)
                result = await session.execute(query)
                achievements = result.scalars().all()
                
                return [self._achievement_to_response(achievement) for achievement in achievements]
                
            except Exception as e:
                self.logger.error(f"Error getting achievements: {e}")
                raise
    
    async def update_achievement(self, achievement_id: int, achievement_data: AchievementUpdate) -> Optional[AchievementResponse]:
        """Обновление достижения"""
        async with get_db_session() as session:
            try:
                query = select(Achievement).where(Achievement.id == achievement_id)
                result = await session.execute(query)
                achievement = result.scalar_one_or_none()
                
                if not achievement:
                    return None
                
                # Обновляем поля
                update_data = achievement_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(achievement, field, value)
                
                await session.commit()
                await session.refresh(achievement)
                
                self.logger.info(f"Updated achievement {achievement_id}")
                return self._achievement_to_response(achievement)
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error updating achievement {achievement_id}: {e}")
                raise
    
    async def delete_achievement(self, achievement_id: int) -> bool:
        """Удаление достижения"""
        async with get_db_session() as session:
            try:
                # Сначала удаляем все связанные достижения студентов
                await session.execute(
                    delete(StudentAchievement).where(StudentAchievement.achievement_id == achievement_id)
                )
                
                # Затем удаляем само достижение
                result = await session.execute(
                    delete(Achievement).where(Achievement.id == achievement_id)
                )
                
                await session.commit()
                
                if result.rowcount > 0:
                    self.logger.info(f"Deleted achievement {achievement_id}")
                    return True
                
                return False
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error deleting achievement {achievement_id}: {e}")
                raise
    
    async def check_achievements_for_student(self, student_id: int) -> List[AchievementUnlocked]:
        """Проверка и начисление достижений для студента"""
        async with get_db_session() as session:
            try:
                # Получаем студента
                query = select(Student).where(Student.id == student_id)
                result = await session.execute(query)
                student = result.scalar_one_or_none()
                
                if not student:
                    self.logger.warning(f"Student {student_id} not found for achievement check")
                    return []
                
                # Получаем все активные достижения
                achievements_query = select(Achievement).where(Achievement.is_active == True)
                achievements_result = await session.execute(achievements_query)
                achievements = achievements_result.scalars().all()
                
                # Получаем уже полученные достижения студента
                earned_query = select(StudentAchievement.achievement_id).where(
                    StudentAchievement.student_id == student_id
                )
                earned_result = await session.execute(earned_query)
                earned_achievement_ids = set(earned_result.scalars().all())
                
                unlocked_achievements = []
                
                # Проверяем каждое достижение
                for achievement in achievements:
                    # Пропускаем уже полученные неповторяемые достижения
                    if (achievement.id in earned_achievement_ids and 
                        not achievement.is_repeatable):
                        continue
                    
                    # Проверяем критерии достижения
                    if await self._check_achievement_criteria(student, achievement):
                        # Начисляем достижение
                        student_achievement = StudentAchievement(
                            student_id=student_id,
                            achievement_id=achievement.id
                        )
                        session.add(student_achievement)
                        
                        # Начисляем XP за достижение
                        if achievement.xp_reward > 0:
                            student.experience_points += achievement.xp_reward
                            student.total_xp_earned += achievement.xp_reward
                        
                        await session.flush()
                        await session.refresh(student_achievement)
                        
                        unlocked_achievements.append(AchievementUnlocked(
                            achievement=self._achievement_to_response(achievement),
                            student_achievement=self._student_achievement_to_response(student_achievement),
                            xp_earned=achievement.xp_reward,
                            is_new_unlock=achievement.id not in earned_achievement_ids
                        ))
                        
                        self.logger.info(
                            f"Student {student_id} unlocked achievement: {achievement.name}"
                        )
                
                await session.commit()
                return unlocked_achievements
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error checking achievements for student {student_id}: {e}")
                raise
    
    async def get_student_achievements(self, student_id: int) -> List[StudentAchievementResponse]:
        """Получение достижений студента"""
        async with get_db_session() as session:
            try:
                query = select(StudentAchievement).options(
                    selectinload(StudentAchievement.achievement)
                ).where(StudentAchievement.student_id == student_id).order_by(
                    StudentAchievement.earned_at.desc()
                )
                
                result = await session.execute(query)
                student_achievements = result.scalars().all()
                
                return [
                    self._student_achievement_to_response(sa) 
                    for sa in student_achievements
                ]
                
            except Exception as e:
                self.logger.error(f"Error getting achievements for student {student_id}: {e}")
                raise
    
    async def get_achievement_stats(self, student_id: int) -> AchievementStats:
        """Получение статистики достижений для студента"""
        async with get_db_session() as session:
            try:
                # Общее количество достижений
                total_query = select(func.count(Achievement.id)).where(
                    and_(Achievement.is_active == True, Achievement.is_hidden == False)
                )
                total_result = await session.execute(total_query)
                total_achievements = total_result.scalar()
                
                # Полученные достижения
                earned_query = select(func.count(StudentAchievement.id)).where(
                    StudentAchievement.student_id == student_id
                )
                earned_result = await session.execute(earned_query)
                earned_achievements = earned_result.scalar()
                
                # Статистика по редкости
                rarity_query = select(
                    Achievement.rarity,
                    func.count(StudentAchievement.id)
                ).select_from(
                    Achievement
                ).outerjoin(
                    StudentAchievement,
                    and_(
                        StudentAchievement.achievement_id == Achievement.id,
                        StudentAchievement.student_id == student_id
                    )
                ).group_by(Achievement.rarity)
                
                rarity_result = await session.execute(rarity_query)
                by_rarity = {rarity.value: count for rarity, count in rarity_result.all()}
                
                # Статистика по типу
                type_query = select(
                    Achievement.type,
                    func.count(StudentAchievement.id)
                ).select_from(
                    Achievement
                ).outerjoin(
                    StudentAchievement,
                    and_(
                        StudentAchievement.achievement_id == Achievement.id,
                        StudentAchievement.student_id == student_id
                    )
                ).group_by(Achievement.type)
                
                type_result = await session.execute(type_query)
                by_type = {type_.value: count for type_, count in type_result.all()}
                
                # Недавние разблокировки
                recent_query = select(StudentAchievement).options(
                    selectinload(StudentAchievement.achievement)
                ).where(
                    StudentAchievement.student_id == student_id
                ).order_by(
                    StudentAchievement.earned_at.desc()
                ).limit(5)
                
                recent_result = await session.execute(recent_query)
                recent_unlocks = [
                    self._student_achievement_to_response(sa)
                    for sa in recent_result.scalars().all()
                ]
                
                completion_percentage = (
                    (earned_achievements / total_achievements * 100) 
                    if total_achievements > 0 else 0
                )
                
                return AchievementStats(
                    total_achievements=total_achievements,
                    earned_achievements=earned_achievements,
                    completion_percentage=round(completion_percentage, 2),
                    by_rarity=by_rarity,
                    by_type=by_type,
                    recent_unlocks=recent_unlocks
                )
                
            except Exception as e:
                self.logger.error(f"Error getting achievement stats for student {student_id}: {e}")
                raise
    
    async def _check_achievement_criteria(self, student: Student, achievement: Achievement) -> bool:
        """Проверка критериев достижения"""
        try:
            criteria = achievement.criteria
            
            # Проверяем каждый критерий
            for field, target_value in criteria.items():
                if hasattr(student, field):
                    current_value = getattr(student, field)
                    if current_value < target_value:
                        return False
                else:
                    # Неизвестный критерий
                    self.logger.warning(f"Unknown achievement criteria: {field}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking achievement criteria: {e}")
            return False
    
    def _achievement_to_response(self, achievement: Achievement) -> AchievementResponse:
        """Преобразование модели Achievement в AchievementResponse"""
        return AchievementResponse(**achievement.to_dict())
    
    def _student_achievement_to_response(self, student_achievement: StudentAchievement) -> StudentAchievementResponse:
        """Преобразование модели StudentAchievement в StudentAchievementResponse"""
        return StudentAchievementResponse(**student_achievement.to_dict())