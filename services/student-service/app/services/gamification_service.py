# -*- coding: utf-8 -*-
"""
Gamification Service
Сервис геймификации и системы очков
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, desc
from ..database.connection import get_db_session
from ..models.student import Student
from ..models.gamification import (
    XPTransaction, Level, Badge, StudentBadge,
    Leaderboard, Competition, CompetitionParticipant
)
from ..schemas.student import XPTransactionCreate, BadgeAwardCreate

logger = logging.getLogger(__name__)

class GamificationService:
    """Сервис геймификации и системы очков"""
    
    # Конфигурация системы уровней
    LEVEL_CONFIG = {
        1: {"xp_required": 0, "title": "Новичок", "color": "#8B4513"},
        2: {"xp_required": 100, "title": "Ученик", "color": "#228B22"},
        3: {"xp_required": 250, "title": "Студент", "color": "#4169E1"},
        4: {"xp_required": 500, "title": "Исследователь", "color": "#9932CC"},
        5: {"xp_required": 1000, "title": "Знаток", "color": "#FF4500"},
        6: {"xp_required": 2000, "title": "Эксперт", "color": "#DC143C"},
        7: {"xp_required": 4000, "title": "Мастер", "color": "#B8860B"},
        8: {"xp_required": 8000, "title": "Гуру", "color": "#800080"},
        9: {"xp_required": 15000, "title": "Легенда", "color": "#FFD700"},
        10: {"xp_required": 25000, "title": "Гроссмейстер", "color": "#FF69B4"}
    }
    
    # XP за различные действия
    XP_REWARDS = {
        "lesson_completed": 50,
        "homework_submitted": 30,
        "homework_perfect": 50,  # Дополнительные очки за идеальную работу
        "material_studied": 10,
        "daily_streak": 20,  # Ежедневная серия занятий
        "week_streak": 100,  # Недельная серия
        "month_streak": 500,  # Месячная серия
        "first_lesson": 25,
        "achievement_unlocked": 100,
        "competition_win": 200,
        "competition_participate": 50
    }
    
    async def award_xp(
        self, 
        student_id: int, 
        action: str, 
        amount: Optional[int] = None,
        lesson_id: Optional[int] = None,
        homework_id: Optional[int] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Начисление XP студенту"""
        try:
            async with get_db_session() as session:
                # Получаем студента
                student = await session.get(Student, student_id)
                if not student:
                    raise ValueError(f"Student with id {student_id} not found")
                
                # Определяем количество XP
                xp_amount = amount or self.XP_REWARDS.get(action, 0)
                if xp_amount <= 0:
                    logger.warning(f"No XP reward defined for action: {action}")
                    return {"success": False, "reason": "No XP reward defined"}
                
                # Проверяем на дублирование (для некоторых действий)
                if action in ["lesson_completed", "homework_submitted"]:
                    existing = await session.execute(
                        select(XPTransaction).where(
                            and_(
                                XPTransaction.student_id == student_id,
                                XPTransaction.action == action,
                                XPTransaction.lesson_id == lesson_id if lesson_id else True,
                                XPTransaction.homework_id == homework_id if homework_id else True
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        logger.info(f"XP already awarded for {action} to student {student_id}")
                        return {"success": False, "reason": "Already awarded"}
                
                # Сохраняем старый уровень для проверки прогресса
                old_level = self.calculate_level(student.total_xp)
                
                # Создаем транзакцию XP
                xp_transaction = XPTransaction(
                    student_id=student_id,
                    action=action,
                    amount=xp_amount,
                    lesson_id=lesson_id,
                    homework_id=homework_id,
                    description=description or f"XP за {action}"
                )
                session.add(xp_transaction)
                
                # Обновляем общий XP студента
                student.total_xp += xp_amount
                
                # Проверяем повышение уровня
                new_level = self.calculate_level(student.total_xp)
                level_up = new_level > old_level
                
                if level_up:
                    student.current_level = new_level
                    logger.info(f"Student {student_id} leveled up to {new_level}!")
                
                await session.commit()
                
                # Проверяем достижения связанные с XP
                await self._check_xp_achievements(student_id, student.total_xp, new_level)
                
                return {
                    "success": True,
                    "xp_awarded": xp_amount,
                    "total_xp": student.total_xp,
                    "old_level": old_level,
                    "new_level": new_level,
                    "level_up": level_up,
                    "level_title": self.LEVEL_CONFIG[new_level]["title"] if new_level <= 10 else "Легендарный Мастер"
                }
                
        except Exception as e:
            logger.error(f"Error awarding XP: {e}")
            return {"success": False, "error": str(e)}
    
    def calculate_level(self, total_xp: int) -> int:
        """Вычисление уровня на основе общего XP"""
        for level in range(10, 0, -1):  # От 10 к 1
            if total_xp >= self.LEVEL_CONFIG[level]["xp_required"]:
                return level
        return 1
    
    def get_xp_for_next_level(self, current_xp: int) -> Dict[str, int]:
        """Получение информации о прогрессе к следующему уровню"""
        current_level = self.calculate_level(current_xp)
        
        if current_level >= 10:
            return {
                "current_level": current_level,
                "next_level": None,
                "xp_needed": 0,
                "progress_percent": 100
            }
        
        next_level = current_level + 1
        current_level_xp = self.LEVEL_CONFIG[current_level]["xp_required"]
        next_level_xp = self.LEVEL_CONFIG[next_level]["xp_required"]
        
        xp_needed = next_level_xp - current_xp
        progress = ((current_xp - current_level_xp) / (next_level_xp - current_level_xp)) * 100
        
        return {
            "current_level": current_level,
            "next_level": next_level,
            "xp_needed": xp_needed,
            "progress_percent": min(100, max(0, progress))
        }
    
    async def award_badge(
        self, 
        student_id: int, 
        badge_code: str, 
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Награждение студента значком"""
        try:
            async with get_db_session() as session:
                # Проверяем существование значка
                badge_result = await session.execute(
                    select(Badge).where(Badge.code == badge_code)
                )
                badge = badge_result.scalar_one_or_none()
                
                if not badge:
                    logger.error(f"Badge with code {badge_code} not found")
                    return {"success": False, "reason": "Badge not found"}
                
                # Проверяем, что студент еще не имеет этого значка
                existing = await session.execute(
                    select(StudentBadge).where(
                        and_(
                            StudentBadge.student_id == student_id,
                            StudentBadge.badge_id == badge.id
                        )
                    )
                )
                
                if existing.scalar_one_or_none():
                    return {"success": False, "reason": "Badge already awarded"}
                
                # Награждаем значком
                student_badge = StudentBadge(
                    student_id=student_id,
                    badge_id=badge.id,
                    earned_at=datetime.utcnow(),
                    reason=reason
                )
                session.add(student_badge)
                
                await session.commit()
                
                # Начисляем XP за получение значка
                await self.award_xp(student_id, "achievement_unlocked", description=f"Получен значок: {badge.name}")
                
                return {
                    "success": True,
                    "badge": {
                        "id": badge.id,
                        "name": badge.name,
                        "description": badge.description,
                        "icon": badge.icon,
                        "rarity": badge.rarity
                    }
                }
                
        except Exception as e:
            logger.error(f"Error awarding badge: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_leaderboard(
        self, 
        period: str = "all_time",
        subject_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Получение таблицы лидеров"""
        try:
            async with get_db_session() as session:
                # Определяем период
                date_filter = None
                if period == "week":
                    date_filter = datetime.utcnow() - timedelta(days=7)
                elif period == "month":
                    date_filter = datetime.utcnow() - timedelta(days=30)
                
                # Строим запрос
                if date_filter:
                    # Для периодических лидербордов - считаем XP за период
                    query = select(
                        Student.id,
                        Student.telegram_username,
                        Student.display_name,
                        Student.avatar_url,
                        func.coalesce(func.sum(XPTransaction.amount), 0).label("period_xp")
                    ).select_from(
                        Student
                    ).outerjoin(
                        XPTransaction, and_(
                            XPTransaction.student_id == Student.id,
                            XPTransaction.created_at >= date_filter
                        )
                    ).group_by(
                        Student.id, Student.telegram_username, 
                        Student.display_name, Student.avatar_url
                    ).order_by(desc("period_xp")).limit(limit)
                else:
                    # Для общего лидерборда - используем total_xp
                    query = select(Student).order_by(desc(Student.total_xp)).limit(limit)
                
                result = await session.execute(query)
                
                if date_filter:
                    leaders = []
                    for row in result:
                        student_data = {
                            "id": row.id,
                            "username": row.telegram_username,
                            "display_name": row.display_name,
                            "avatar_url": row.avatar_url,
                            "xp": row.period_xp,
                            "level": self.calculate_level(row.period_xp) if period != "all_time" else None
                        }
                        leaders.append(student_data)
                else:
                    leaders = []
                    for idx, student in enumerate(result.scalars(), 1):
                        student_data = {
                            "position": idx,
                            "id": student.id,
                            "username": student.telegram_username,
                            "display_name": student.display_name,
                            "avatar_url": student.avatar_url,
                            "xp": student.total_xp,
                            "level": student.current_level,
                            "level_title": self.LEVEL_CONFIG.get(student.current_level, {}).get("title", "Unknown")
                        }
                        leaders.append(student_data)
                
                return leaders
                
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    async def calculate_streak(self, student_id: int) -> Dict[str, Any]:
        """Вычисление серии активности студента"""
        try:
            async with get_db_session() as session:
                # Получаем последние транзакции XP для определения активности
                recent_transactions = await session.execute(
                    select(XPTransaction).where(
                        and_(
                            XPTransaction.student_id == student_id,
                            XPTransaction.action.in_(["lesson_completed", "homework_submitted"]),
                            XPTransaction.created_at >= datetime.utcnow() - timedelta(days=30)
                        )
                    ).order_by(desc(XPTransaction.created_at))
                )
                
                transactions = recent_transactions.scalars().all()
                
                if not transactions:
                    return {"current_streak": 0, "longest_streak": 0, "last_activity": None}
                
                # Группируем по дням
                daily_activity = {}
                for transaction in transactions:
                    date_key = transaction.created_at.date()
                    daily_activity[date_key] = True
                
                # Вычисляем текущую серию
                current_streak = 0
                current_date = datetime.utcnow().date()
                
                while current_date in daily_activity:
                    current_streak += 1
                    current_date -= timedelta(days=1)
                
                # Вычисляем максимальную серию
                sorted_dates = sorted(daily_activity.keys())
                longest_streak = 0
                temp_streak = 1
                
                for i in range(1, len(sorted_dates)):
                    if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                        temp_streak += 1
                    else:
                        longest_streak = max(longest_streak, temp_streak)
                        temp_streak = 1
                
                longest_streak = max(longest_streak, temp_streak)
                
                return {
                    "current_streak": current_streak,
                    "longest_streak": longest_streak,
                    "last_activity": max(daily_activity.keys()) if daily_activity else None
                }
                
        except Exception as e:
            logger.error(f"Error calculating streak: {e}")
            return {"current_streak": 0, "longest_streak": 0, "last_activity": None}
    
    async def _check_xp_achievements(self, student_id: int, total_xp: int, level: int):
        """Проверка достижений связанных с XP и уровнями"""
        achievements_to_award = []
        
        # Достижения за XP
        xp_milestones = [100, 500, 1000, 2500, 5000, 10000, 25000]
        for milestone in xp_milestones:
            if total_xp >= milestone:
                achievements_to_award.append(f"xp_{milestone}")
        
        # Достижения за уровни
        level_milestones = [2, 5, 8, 10]
        for milestone in level_milestones:
            if level >= milestone:
                achievements_to_award.append(f"level_{milestone}")
        
        # Награждаем достижениями
        for achievement_code in achievements_to_award:
            await self.award_badge(student_id, achievement_code)
    
    async def initialize_default_badges(self):
        """Инициализация стандартных значков системы"""
        try:
            async with get_db_session() as session:
                default_badges = [
                    # XP достижения
                    {
                        "code": "xp_100",
                        "name": "Первая сотня",
                        "description": "Заработать 100 XP",
                        "icon": "🏆",
                        "rarity": "common",
                        "category": "xp"
                    },
                    {
                        "code": "xp_1000", 
                        "name": "Тысячник",
                        "description": "Заработать 1000 XP",
                        "icon": "🥉",
                        "rarity": "uncommon",
                        "category": "xp"
                    },
                    {
                        "code": "xp_10000",
                        "name": "Десять тысяч",
                        "description": "Заработать 10000 XP", 
                        "icon": "🥈",
                        "rarity": "rare",
                        "category": "xp"
                    },
                    
                    # Уровни
                    {
                        "code": "level_5",
                        "name": "Знаток",
                        "description": "Достичь 5-го уровня",
                        "icon": "⭐",
                        "rarity": "uncommon", 
                        "category": "level"
                    },
                    {
                        "code": "level_10",
                        "name": "Мастер",
                        "description": "Достичь максимального уровня",
                        "icon": "👑",
                        "rarity": "legendary",
                        "category": "level"
                    },
                    
                    # Активность
                    {
                        "code": "streak_7",
                        "name": "Неделя подряд",
                        "description": "Заниматься 7 дней подряд",
                        "icon": "🔥",
                        "rarity": "uncommon",
                        "category": "streak"
                    },
                    {
                        "code": "streak_30",
                        "name": "Месячный марафон", 
                        "description": "Заниматься 30 дней подряд",
                        "icon": "🏃‍♂️",
                        "rarity": "epic",
                        "category": "streak"
                    },
                    
                    # Специальные
                    {
                        "code": "first_lesson",
                        "name": "Первый шаг",
                        "description": "Завершить первый урок",
                        "icon": "👶",
                        "rarity": "common",
                        "category": "special"
                    },
                    {
                        "code": "perfect_homework",
                        "name": "Идеалист",
                        "description": "Выполнить домашнее задание на отлично",
                        "icon": "💯",
                        "rarity": "uncommon",
                        "category": "homework"
                    }
                ]
                
                for badge_data in default_badges:
                    # Проверяем, что значок еще не существует
                    existing = await session.execute(
                        select(Badge).where(Badge.code == badge_data["code"])
                    )
                    
                    if not existing.scalar_one_or_none():
                        badge = Badge(**badge_data)
                        session.add(badge)
                
                await session.commit()
                logger.info("Default badges initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing default badges: {e}")