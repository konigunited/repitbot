# -*- coding: utf-8 -*-
"""
Event Handlers for Student Service
Обработчики событий от других сервисов
"""
import logging
from typing import Dict, Any

from ..services.student_service import StudentService
from ..services.achievement_service import AchievementService
from ..services.gamification_service import GamificationService
from ...shared.event_bus import Event, EventType, get_event_bus

logger = logging.getLogger(__name__)

class StudentEventHandlers:
    """Обработчики событий для Student Service"""
    
    def __init__(self):
        self.student_service = StudentService()
        self.achievement_service = AchievementService()
        self.gamification_service = GamificationService()
        self.event_bus = get_event_bus("student-service")
    
    def register_handlers(self):
        """Регистрация обработчиков событий"""
        # User events
        self.event_bus.subscribe(EventType.USER_CREATED, self.handle_user_created)
        
        # Lesson events
        self.event_bus.subscribe(EventType.LESSON_COMPLETED, self.handle_lesson_completed)
        
        # Homework events
        self.event_bus.subscribe(EventType.HOMEWORK_SUBMITTED, self.handle_homework_submitted)
        self.event_bus.subscribe(EventType.HOMEWORK_GRADED, self.handle_homework_graded)
        
        # Payment events
        self.event_bus.subscribe(EventType.PAYMENT_COMPLETED, self.handle_payment_completed)
        
        # Material events
        self.event_bus.subscribe(EventType.MATERIAL_ACCESSED, self.handle_material_accessed)
        
        logger.info("Registered student service event handlers")
    
    async def handle_user_created(self, event: Event):
        """Обработка создания пользователя"""
        try:
            user_data = event.data
            user_id = user_data.get("id") or event.user_id
            
            if not user_id:
                logger.warning("User created event without user ID")
                return
            
            # Создаем профиль студента для нового пользователя
            student_data = {
                "user_id": user_id,
                "display_name": user_data.get("name", f"User {user_id}"),
                "preferred_subjects": [],
                "learning_goals": [],
                "study_schedule": {},
                "notification_preferences": {
                    "achievements": True,
                    "level_up": True,
                    "reminders": True
                }
            }
            
            student = await self.student_service.create_student(student_data)
            
            logger.info(f"Created student profile for user {user_id}")
            
            # Публикуем событие создания студента
            await self.event_bus.publish_event(Event.create(
                event_type=EventType.STUDENT_CREATED,
                source_service="student-service",
                data={"student_id": student["id"], "user_id": user_id},
                user_id=user_id,
                correlation_id=event.correlation_id
            ))
            
        except Exception as e:
            logger.error(f"Failed to handle user created event {event.event_id}: {e}")
    
    async def handle_lesson_completed(self, event: Event):
        """Обработка завершения урока"""
        try:
            lesson_data = event.data
            user_id = lesson_data.get("student_id") or event.user_id
            
            if not user_id:
                logger.warning("Lesson completed event without user ID")
                return
            
            # Получаем студента
            student = await self.student_service.get_student_by_user_id(user_id)
            if not student:
                logger.warning(f"Student not found for user {user_id}")
                return
            
            # Обновляем статистику
            stats_update = {"lessons_completed": 1}
            
            # Добавляем время обучения если есть
            lesson_duration = lesson_data.get("duration_minutes", 0)
            if lesson_duration > 0:
                stats_update["study_time_minutes"] = lesson_duration
            
            await self.student_service.update_student_stats(student["id"], stats_update)
            
            # Начисляем XP
            base_xp = 100
            lesson_type = lesson_data.get("lesson_type", "regular")
            score = lesson_data.get("score", 0)
            
            # Бонусы
            type_multiplier = {
                "regular": 1.0,
                "practice": 1.2,
                "test": 1.5,
                "exam": 2.0
            }.get(lesson_type, 1.0)
            
            score_multiplier = 1.5 if score >= 90 else (1.2 if score >= 75 else 1.0)
            
            total_xp = int(base_xp * type_multiplier * score_multiplier)
            
            # Добавляем XP
            level_up_response = await self.student_service.add_experience(
                student["id"],
                {
                    "amount": total_xp,
                    "reason": f"Lesson completed ({lesson_type})",
                    "category": "lesson",
                    "metadata": lesson_data
                }
            )
            
            # Проверяем достижения
            await self.achievement_service.check_lesson_achievements(student["id"], lesson_data)
            
            # Публикуем XP событие
            await self.event_bus.publish_event(Event.create(
                event_type=EventType.XP_EARNED,
                source_service="student-service",
                data={
                    "user_id": user_id,
                    "student_id": student["id"],
                    "xp_amount": total_xp,
                    "reason": "lesson_completed",
                    "level_up": level_up_response is not None
                },
                user_id=user_id,
                correlation_id=event.correlation_id
            ))
            
            # Если был level up, публикуем событие
            if level_up_response:
                await self.event_bus.publish_student_level_up({
                    "user_id": user_id,
                    "student_id": student["id"],
                    "new_level": level_up_response["new_level"],
                    "previous_level": level_up_response["previous_level"],
                    "xp_earned": total_xp
                })
            
            logger.info(f"Processed lesson completion for user {user_id}: +{total_xp} XP")
            
        except Exception as e:
            logger.error(f"Failed to handle lesson completed event {event.event_id}: {e}")
    
    async def handle_homework_submitted(self, event: Event):
        """Обработка отправки домашнего задания"""
        try:
            homework_data = event.data
            user_id = homework_data.get("student_id") or event.user_id
            
            if not user_id:
                logger.warning("Homework submitted event without user ID")
                return
            
            # Получаем студента
            student = await self.student_service.get_student_by_user_id(user_id)
            if not student:
                logger.warning(f"Student not found for user {user_id}")
                return
            
            # Обновляем статистику
            stats_update = {"homework_submitted": 1}
            await self.student_service.update_student_stats(student["id"], stats_update)
            
            # Начисляем базовые XP за отправку
            base_xp = 50
            
            # Добавляем XP
            await self.student_service.add_experience(
                student["id"],
                {
                    "amount": base_xp,
                    "reason": "Homework submitted",
                    "category": "homework",
                    "metadata": homework_data
                }
            )
            
            # Проверяем достижения
            await self.achievement_service.check_homework_achievements(student["id"], homework_data)
            
            logger.info(f"Processed homework submission for user {user_id}: +{base_xp} XP")
            
        except Exception as e:
            logger.error(f"Failed to handle homework submitted event {event.event_id}: {e}")
    
    async def handle_homework_graded(self, event: Event):
        """Обработка оценки домашнего задания"""
        try:
            homework_data = event.data
            user_id = homework_data.get("student_id") or event.user_id
            score = homework_data.get("score", 0)
            
            if not user_id:
                logger.warning("Homework graded event without user ID")
                return
            
            # Получаем студента
            student = await self.student_service.get_student_by_user_id(user_id)
            if not student:
                logger.warning(f"Student not found for user {user_id}")
                return
            
            # Обновляем статистику для отличных работ
            stats_update = {}
            if score >= 90:
                stats_update["homework_perfect"] = 1
            
            if stats_update:
                await self.student_service.update_student_stats(student["id"], stats_update)
            
            # Дополнительные XP за высокую оценку
            bonus_xp = 0
            if score >= 90:
                bonus_xp = 100  # Отличная работа
            elif score >= 75:
                bonus_xp = 50   # Хорошая работа
            
            if bonus_xp > 0:
                await self.student_service.add_experience(
                    student["id"],
                    {
                        "amount": bonus_xp,
                        "reason": f"Homework graded (score: {score})",
                        "category": "homework",
                        "metadata": homework_data
                    }
                )
            
            # Проверяем достижения за оценки
            await self.achievement_service.check_grade_achievements(student["id"], score)
            
            logger.info(f"Processed homework grade for user {user_id}: score {score}, +{bonus_xp} XP")
            
        except Exception as e:
            logger.error(f"Failed to handle homework graded event {event.event_id}: {e}")
    
    async def handle_payment_completed(self, event: Event):
        """Обработка завершения платежа"""
        try:
            payment_data = event.data
            user_id = payment_data.get("user_id") or event.user_id
            amount = payment_data.get("amount", 0)
            
            if not user_id:
                logger.warning("Payment completed event without user ID")
                return
            
            # Получаем студента
            student = await self.student_service.get_student_by_user_id(user_id)
            if not student:
                logger.warning(f"Student not found for user {user_id}")
                return
            
            # Начисляем XP за пополнение баланса
            # XP зависит от суммы платежа
            xp_amount = min(int(amount * 0.1), 500)  # Максимум 500 XP
            
            if xp_amount > 0:
                await self.student_service.add_experience(
                    student["id"],
                    {
                        "amount": xp_amount,
                        "reason": f"Payment completed ({amount} RUB)",
                        "category": "payment",
                        "metadata": payment_data
                    }
                )
            
            # Проверяем достижения за платежи
            await self.achievement_service.check_payment_achievements(student["id"], amount)
            
            logger.info(f"Processed payment for user {user_id}: {amount} RUB, +{xp_amount} XP")
            
        except Exception as e:
            logger.error(f"Failed to handle payment completed event {event.event_id}: {e}")
    
    async def handle_material_accessed(self, event: Event):
        """Обработка доступа к материалам"""
        try:
            material_data = event.data
            user_id = material_data.get("user_id") or event.user_id
            
            if not user_id:
                logger.warning("Material accessed event without user ID")
                return
            
            # Получаем студента
            student = await self.student_service.get_student_by_user_id(user_id)
            if not student:
                logger.warning(f"Student not found for user {user_id}")
                return
            
            # Обновляем статистику
            stats_update = {"materials_studied": 1}
            await self.student_service.update_student_stats(student["id"], stats_update)
            
            # Небольшие XP за изучение материалов
            xp_amount = 25
            
            await self.student_service.add_experience(
                student["id"],
                {
                    "amount": xp_amount,
                    "reason": "Material studied",
                    "category": "material",
                    "metadata": material_data
                }
            )
            
            # Проверяем достижения за изучение материалов
            await self.achievement_service.check_material_achievements(student["id"], material_data)
            
            logger.info(f"Processed material access for user {user_id}: +{xp_amount} XP")
            
        except Exception as e:
            logger.error(f"Failed to handle material accessed event {event.event_id}: {e}")

# Глобальный экземпляр обработчиков
_event_handlers: Optional[StudentEventHandlers] = None

def get_event_handlers() -> StudentEventHandlers:
    """Получение глобального экземпляра обработчиков событий"""
    global _event_handlers
    if _event_handlers is None:
        _event_handlers = StudentEventHandlers()
    return _event_handlers

async def init_event_handlers():
    """Инициализация и регистрация обработчиков событий"""
    handlers = get_event_handlers()
    handlers.register_handlers()
    
    # Запускаем прослушивание событий
    await handlers.event_bus.start_consuming()
    
    logger.info("Student service event handlers initialized and listening")