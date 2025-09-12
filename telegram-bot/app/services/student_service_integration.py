# -*- coding: utf-8 -*-
"""
Student Service Integration for Telegram Bot
Интеграция с сервисом студентов для геймификации
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .microservice_client import get_microservice_client, HTTPException, ServiceUnavailableException

logger = logging.getLogger(__name__)

class StudentServiceIntegration:
    """Интеграция с сервисом студентов"""
    
    def __init__(self):
        self.client = get_microservice_client()
        self.fallback_enabled = True  # Включить fallback к локальной БД
    
    async def get_or_create_student_profile(self, user_id: int, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Получение или создание профиля студента"""
        try:
            # Пытаемся получить существующий профиль
            profile = await self.client.get_student_profile(user_id)
            if profile:
                return profile
            
            # Создаем новый профиль
            if not user_data:
                user_data = {"user_id": user_id}
            
            student_data = {
                "user_id": user_id,
                "display_name": user_data.get("display_name", f"User {user_id}"),
                "preferred_subjects": [],
                "learning_goals": [],
                "study_schedule": {},
                "notification_preferences": {
                    "achievements": True,
                    "level_up": True,
                    "reminders": True
                }
            }
            
            profile = await self.client.create_student(student_data)
            logger.info(f"Created new student profile for user {user_id}")
            return profile
            
        except (HTTPException, ServiceUnavailableException) as e:
            logger.error(f"Failed to get/create student profile for user {user_id}: {e}")
            
            if self.fallback_enabled:
                # Возвращаем базовый профиль
                return {
                    "user_id": user_id,
                    "level": 1,
                    "experience_points": 0,
                    "total_xp_earned": 0,
                    "lessons_completed": 0,
                    "homework_submitted": 0,
                    "current_streak": 0,
                    "best_streak": 0,
                    "achievements": []
                }
            raise
    
    async def add_experience_points(
        self,
        user_id: int,
        amount: int,
        reason: str,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Добавление очков опыта студенту"""
        try:
            xp_data = {
                "amount": amount,
                "reason": reason,
                "category": category,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
            
            result = await self.client.add_student_xp(user_id, xp_data)
            
            if result:
                logger.info(f"Added {amount} XP to user {user_id} for: {reason}")
                
                # Проверяем, произошло ли повышение уровня
                if result.get("level_up"):
                    await self._handle_level_up(user_id, result)
                
                # Проверяем новые достижения
                new_achievements = result.get("new_achievements", [])
                if new_achievements:
                    await self._handle_new_achievements(user_id, new_achievements)
            
            return result
            
        except (HTTPException, ServiceUnavailableException) as e:
            logger.error(f"Failed to add XP to user {user_id}: {e}")
            return None
    
    async def get_student_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение достижений студента"""
        try:
            achievements = await self.client.get_student_achievements(user_id)
            return achievements
        except (HTTPException, ServiceUnavailableException) as e:
            logger.error(f"Failed to get achievements for user {user_id}: {e}")
            return []
    
    async def get_student_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Получение дашборда студента с полной информацией"""
        try:
            profile = await self.get_or_create_student_profile(user_id)
            achievements = await self.get_student_achievements(user_id)
            
            # Формируем дашборд
            dashboard = {
                "profile": profile,
                "achievements": {
                    "total": len(achievements),
                    "recent": achievements[:5],  # Последние 5 достижений
                    "by_rarity": self._group_achievements_by_rarity(achievements)
                },
                "progress": {
                    "level": profile.get("level", 1),
                    "experience_points": profile.get("experience_points", 0),
                    "xp_for_next_level": profile.get("xp_for_next_level", 1000),
                    "xp_progress_percentage": profile.get("xp_progress_percentage", 0),
                    "can_level_up": profile.get("can_level_up", False)
                },
                "statistics": {
                    "lessons_completed": profile.get("lessons_completed", 0),
                    "homework_submitted": profile.get("homework_submitted", 0),
                    "homework_perfect": profile.get("homework_perfect", 0),
                    "materials_studied": profile.get("materials_studied", 0),
                    "study_time_minutes": profile.get("study_time_minutes", 0),
                    "current_streak": profile.get("current_streak", 0),
                    "best_streak": profile.get("best_streak", 0)
                }
            }
            
            return dashboard
            
        except (HTTPException, ServiceUnavailableException) as e:
            logger.error(f"Failed to get dashboard for user {user_id}: {e}")
            return {}
    
    async def record_lesson_completion(self, user_id: int, lesson_data: Dict[str, Any]) -> bool:
        """Запись завершения урока"""
        try:
            # Добавляем XP за завершение урока
            xp_amount = self._calculate_lesson_xp(lesson_data)
            
            result = await self.add_experience_points(
                user_id=user_id,
                amount=xp_amount,
                reason="Lesson completed",
                category="lesson",
                metadata={
                    "lesson_id": lesson_data.get("lesson_id"),
                    "lesson_type": lesson_data.get("lesson_type"),
                    "duration": lesson_data.get("duration"),
                    "score": lesson_data.get("score")
                }
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to record lesson completion for user {user_id}: {e}")
            return False
    
    async def record_homework_submission(self, user_id: int, homework_data: Dict[str, Any]) -> bool:
        """Запись отправки домашнего задания"""
        try:
            # Добавляем XP за отправку домашки
            base_xp = 50
            score = homework_data.get("score", 0)
            
            # Бонус за высокую оценку
            bonus_xp = 0
            if score >= 90:
                bonus_xp = 100  # Бонус за отличную работу
            elif score >= 75:
                bonus_xp = 50   # Бонус за хорошую работу
            
            total_xp = base_xp + bonus_xp
            
            result = await self.add_experience_points(
                user_id=user_id,
                amount=total_xp,
                reason=f"Homework submitted (score: {score})",
                category="homework",
                metadata={
                    "homework_id": homework_data.get("homework_id"),
                    "score": score,
                    "submission_time": homework_data.get("submission_time"),
                    "is_perfect": score >= 90
                }
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to record homework submission for user {user_id}: {e}")
            return False
    
    async def update_study_streak(self, user_id: int) -> Dict[str, Any]:
        """Обновление стрика обучения"""
        try:
            # Это должно обрабатываться автоматически в Student Service
            # при обновлении last_activity_date
            
            # Пока что просто возвращаем текущий профиль
            profile = await self.get_or_create_student_profile(user_id)
            
            return {
                "current_streak": profile.get("current_streak", 0),
                "best_streak": profile.get("best_streak", 0),
                "is_new_best": False  # TODO: логика определения нового рекорда
            }
            
        except Exception as e:
            logger.error(f"Failed to update study streak for user {user_id}: {e}")
            return {"current_streak": 0, "best_streak": 0, "is_new_best": False}
    
    def _calculate_lesson_xp(self, lesson_data: Dict[str, Any]) -> int:
        """Расчет XP за урок"""
        base_xp = 100
        
        # Бонус за тип урока
        lesson_type = lesson_data.get("lesson_type", "regular")
        type_multiplier = {
            "regular": 1.0,
            "practice": 1.2,
            "test": 1.5,
            "exam": 2.0
        }.get(lesson_type, 1.0)
        
        # Бонус за оценку
        score = lesson_data.get("score", 0)
        score_multiplier = 1.0
        if score >= 90:
            score_multiplier = 1.5
        elif score >= 75:
            score_multiplier = 1.2
        
        total_xp = int(base_xp * type_multiplier * score_multiplier)
        return max(total_xp, 50)  # Минимум 50 XP
    
    def _group_achievements_by_rarity(self, achievements: List[Dict[str, Any]]) -> Dict[str, int]:
        """Группировка достижений по редкости"""
        rarity_counts = {"common": 0, "rare": 0, "epic": 0, "legendary": 0}
        
        for achievement in achievements:
            rarity = achievement.get("achievement", {}).get("rarity", "common")
            if rarity in rarity_counts:
                rarity_counts[rarity] += 1
        
        return rarity_counts
    
    async def _handle_level_up(self, user_id: int, level_up_data: Dict[str, Any]):
        """Обработка повышения уровня"""
        new_level = level_up_data.get("new_level", 1)
        logger.info(f"User {user_id} leveled up to level {new_level}")
        
        try:
            # Отправляем уведомление через Notification Service
            notification_data = {
                "user_id": user_id,
                "type": "level_up",
                "title": "Поздравляем с повышением уровня!",
                "message": f"Вы достигли {new_level} уровня! 🎉",
                "data": {
                    "new_level": new_level,
                    "previous_level": level_up_data.get("previous_level", new_level - 1)
                },
                "channels": ["telegram"]
            }
            
            await self.client.send_notification(notification_data)
            
        except Exception as e:
            logger.error(f"Failed to send level up notification for user {user_id}: {e}")
    
    async def _handle_new_achievements(self, user_id: int, achievements: List[Dict[str, Any]]):
        """Обработка новых достижений"""
        logger.info(f"User {user_id} earned {len(achievements)} new achievements")
        
        try:
            for achievement in achievements:
                achievement_name = achievement.get("name", "Unknown Achievement")
                achievement_xp = achievement.get("xp_reward", 0)
                
                # Отправляем уведомление о достижении
                notification_data = {
                    "user_id": user_id,
                    "type": "achievement",
                    "title": "Новое достижение!",
                    "message": f"Вы получили достижение: {achievement_name} (+{achievement_xp} XP)",
                    "data": {
                        "achievement_id": achievement.get("achievement_id"),
                        "achievement_name": achievement_name,
                        "xp_reward": achievement_xp,
                        "rarity": achievement.get("rarity", "common")
                    },
                    "channels": ["telegram"]
                }
                
                await self.client.send_notification(notification_data)
                
        except Exception as e:
            logger.error(f"Failed to send achievement notifications for user {user_id}: {e}")


# Глобальный экземпляр
_student_integration: Optional[StudentServiceIntegration] = None

def get_student_integration() -> StudentServiceIntegration:
    """Получение глобального экземпляра интеграции со Student Service"""
    global _student_integration
    if _student_integration is None:
        _student_integration = StudentServiceIntegration()
    return _student_integration