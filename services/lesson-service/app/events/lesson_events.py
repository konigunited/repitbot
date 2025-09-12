# -*- coding: utf-8 -*-
"""
Система событий для Lesson Service.
Реализует event-driven архитектуру для межсервисного взаимодействия.
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

import aio_pika
from aio_pika import Connection, Channel, Exchange, Queue
from aio_pika.abc import AbstractIncomingMessage

from ..config.settings import get_settings
from ..models.lesson import Lesson, LessonAttendance

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class LessonEvent:
    """Базовый класс для событий уроков."""
    event_type: str
    lesson_id: int
    student_id: int
    tutor_id: Optional[int]
    timestamp: datetime
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LessonEvent':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class LessonEventPublisher:
    """
    Publisher для отправки событий о уроках.
    Использует RabbitMQ для асинхронной доставки событий.
    """
    
    def __init__(self):
        self.connection: Optional[Connection] = None
        self.channel: Optional[Channel] = None
        self.exchange: Optional[Exchange] = None
        self._is_connected = False
    
    async def initialize(self):
        """Инициализация подключения к RabbitMQ."""
        try:
            self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self.channel = await self.connection.channel()
            
            # Создание exchange
            self.exchange = await self.channel.declare_exchange(
                settings.EVENT_EXCHANGE_NAME,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            self._is_connected = True
            logger.info("Event publisher initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize event publisher: {e}")
            self._is_connected = False
            raise
    
    async def close(self):
        """Закрытие подключения."""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            self._is_connected = False
            logger.info("Event publisher connection closed")
        except Exception as e:
            logger.error(f"Error closing event publisher: {e}")
    
    async def publish_event(self, event: LessonEvent, routing_key: str):
        """Публикация события."""
        if not self._is_connected or not self.exchange:
            logger.warning("Event publisher not connected, skipping event")
            return
        
        try:
            message_body = json.dumps(event.to_dict(), ensure_ascii=False)
            
            await self.exchange.publish(
                aio_pika.Message(
                    message_body.encode('utf-8'),
                    content_type='application/json',
                    headers={
                        'event_type': event.event_type,
                        'service': 'lesson-service',
                        'version': '1.0'
                    }
                ),
                routing_key=routing_key
            )
            
            logger.info(f"Published event {event.event_type} for lesson {event.lesson_id}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            raise
    
    async def publish_lesson_created(self, lesson: Lesson):
        """Событие создания урока."""
        event = LessonEvent(
            event_type="lesson.created",
            lesson_id=lesson.id,
            student_id=lesson.student_id,
            tutor_id=lesson.tutor_id,
            timestamp=datetime.now(),
            data={
                "topic": lesson.topic,
                "date": lesson.date.isoformat(),
                "duration_minutes": lesson.duration_minutes,
                "room_url": lesson.room_url,
                "created_by": lesson.created_by
            }
        )
        
        await self.publish_event(event, f"{settings.LESSON_EVENT_ROUTING_KEY}.created")
    
    async def publish_lesson_updated(self, lesson: Lesson, old_data: Dict[str, Any]):
        """Событие обновления урока."""
        event = LessonEvent(
            event_type="lesson.updated",
            lesson_id=lesson.id,
            student_id=lesson.student_id,
            tutor_id=lesson.tutor_id,
            timestamp=datetime.now(),
            data={
                "topic": lesson.topic,
                "date": lesson.date.isoformat(),
                "mastery_level": lesson.mastery_level.value,
                "attendance_status": lesson.attendance_status.value,
                "lesson_status": lesson.lesson_status.value,
                "old_data": old_data
            }
        )
        
        await self.publish_event(event, f"{settings.LESSON_EVENT_ROUTING_KEY}.updated")
    
    async def publish_lesson_rescheduled(
        self, 
        lesson: Lesson, 
        original_date: datetime, 
        new_date: datetime, 
        reason: str
    ):
        """Событие переноса урока."""
        event = LessonEvent(
            event_type="lesson.rescheduled",
            lesson_id=lesson.id,
            student_id=lesson.student_id,
            tutor_id=lesson.tutor_id,
            timestamp=datetime.now(),
            data={
                "topic": lesson.topic,
                "original_date": original_date.isoformat(),
                "new_date": new_date.isoformat(),
                "reason": reason,
                "rescheduled_by": lesson.created_by
            }
        )
        
        await self.publish_event(event, f"{settings.LESSON_EVENT_ROUTING_KEY}.rescheduled")
    
    async def publish_lesson_cancelled(self, lesson: Lesson, reason: str):
        """Событие отмены урока."""
        event = LessonEvent(
            event_type="lesson.cancelled",
            lesson_id=lesson.id,
            student_id=lesson.student_id,
            tutor_id=lesson.tutor_id,
            timestamp=datetime.now(),
            data={
                "topic": lesson.topic,
                "date": lesson.date.isoformat(),
                "reason": reason,
                "attendance_status": lesson.attendance_status.value,
                "cancelled_by": lesson.created_by
            }
        )
        
        await self.publish_event(event, f"{settings.LESSON_EVENT_ROUTING_KEY}.cancelled")
    
    async def publish_lesson_deleted(self, lesson: Lesson):
        """Событие удаления урока."""
        event = LessonEvent(
            event_type="lesson.deleted",
            lesson_id=lesson.id,
            student_id=lesson.student_id,
            tutor_id=lesson.tutor_id,
            timestamp=datetime.now(),
            data={
                "topic": lesson.topic,
                "date": lesson.date.isoformat()
            }
        )
        
        await self.publish_event(event, f"{settings.LESSON_EVENT_ROUTING_KEY}.deleted")
    
    async def publish_attendance_marked(self, lesson: Lesson, attendance: LessonAttendance):
        """Событие отметки посещаемости."""
        event = LessonEvent(
            event_type="lesson.attendance_marked",
            lesson_id=lesson.id,
            student_id=lesson.student_id,
            tutor_id=lesson.tutor_id,
            timestamp=datetime.now(),
            data={
                "topic": lesson.topic,
                "date": lesson.date.isoformat(),
                "attendance_status": attendance.attendance_status.value,
                "student_rating": attendance.student_rating,
                "tutor_rating": attendance.tutor_rating,
                "actual_duration_minutes": attendance.actual_duration_minutes,
                "recorded_by": attendance.recorded_by
            }
        )
        
        await self.publish_event(event, f"{settings.LESSON_EVENT_ROUTING_KEY}.attendance")
    
    async def publish_lesson_reminder_needed(self, lesson: Lesson, hours_before: int):
        """Событие необходимости отправки напоминания о уроке."""
        event = LessonEvent(
            event_type="lesson.reminder_needed",
            lesson_id=lesson.id,
            student_id=lesson.student_id,
            tutor_id=lesson.tutor_id,
            timestamp=datetime.now(),
            data={
                "topic": lesson.topic,
                "date": lesson.date.isoformat(),
                "hours_before": hours_before,
                "room_url": lesson.room_url
            }
        )
        
        await self.publish_event(event, f"{settings.LESSON_EVENT_ROUTING_KEY}.reminder")


class LessonEventConsumer:
    """
    Consumer для обработки входящих событий от других сервисов.
    Обрабатывает события от User Service и других сервисов.
    """
    
    def __init__(self):
        self.connection: Optional[Connection] = None
        self.channel: Optional[Channel] = None
        self.exchange: Optional[Exchange] = None
        self._is_running = False
    
    async def initialize(self):
        """Инициализация consumer."""
        try:
            self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Подключение к exchange
            self.exchange = await self.channel.declare_exchange(
                settings.EVENT_EXCHANGE_NAME,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info("Event consumer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize event consumer: {e}")
            raise
    
    async def start_consuming(self):
        """Запуск потребления событий."""
        if self._is_running:
            return
        
        try:
            # Очередь для событий пользователей
            user_queue = await self.channel.declare_queue(
                "lesson_service_user_events",
                durable=True
            )
            
            # Привязка к routing keys для пользователей
            await user_queue.bind(self.exchange, "user.updated")
            await user_queue.bind(self.exchange, "user.deleted")
            
            # Очередь для событий домашних заданий
            homework_queue = await self.channel.declare_queue(
                "lesson_service_homework_events",
                durable=True
            )
            
            # Привязка к routing keys для домашних заданий
            await homework_queue.bind(self.exchange, "homework.assigned")
            await homework_queue.bind(self.exchange, "homework.submitted")
            await homework_queue.bind(self.exchange, "homework.checked")
            
            # Запуск потребления
            await user_queue.consume(self.handle_user_event)
            await homework_queue.consume(self.handle_homework_event)
            
            self._is_running = True
            logger.info("Started consuming events")
            
        except Exception as e:
            logger.error(f"Failed to start consuming events: {e}")
            raise
    
    async def stop_consuming(self):
        """Остановка потребления событий."""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            self._is_running = False
            logger.info("Stopped consuming events")
        except Exception as e:
            logger.error(f"Error stopping event consumer: {e}")
    
    async def handle_user_event(self, message: AbstractIncomingMessage):
        """Обработчик событий пользователей."""
        try:
            async with message.process():
                event_data = json.loads(message.body.decode('utf-8'))
                event_type = event_data.get('event_type')
                
                logger.info(f"Received user event: {event_type}")
                
                if event_type == "user.updated":
                    await self._handle_user_updated(event_data)
                elif event_type == "user.deleted":
                    await self._handle_user_deleted(event_data)
                
        except Exception as e:
            logger.error(f"Failed to handle user event: {e}")
            # В реальном приложении здесь может быть retry логика
    
    async def handle_homework_event(self, message: AbstractIncomingMessage):
        """Обработчик событий домашних заданий."""
        try:
            async with message.process():
                event_data = json.loads(message.body.decode('utf-8'))
                event_type = event_data.get('event_type')
                
                logger.info(f"Received homework event: {event_type}")
                
                if event_type == "homework.assigned":
                    await self._handle_homework_assigned(event_data)
                elif event_type == "homework.submitted":
                    await self._handle_homework_submitted(event_data)
                elif event_type == "homework.checked":
                    await self._handle_homework_checked(event_data)
                
        except Exception as e:
            logger.error(f"Failed to handle homework event: {e}")
    
    async def _handle_user_updated(self, event_data: Dict[str, Any]):
        """Обработка обновления пользователя."""
        # TODO: Обновить кеш пользователей или выполнить другую логику
        user_id = event_data.get('user_id')
        logger.info(f"User {user_id} was updated")
    
    async def _handle_user_deleted(self, event_data: Dict[str, Any]):
        """Обработка удаления пользователя."""
        # TODO: Удалить или архивировать уроки пользователя
        user_id = event_data.get('user_id')
        logger.info(f"User {user_id} was deleted")
    
    async def _handle_homework_assigned(self, event_data: Dict[str, Any]):
        """Обработка назначения домашнего задания."""
        from ..database.connection import get_db_session
        from ..models.lesson import Lesson
        from sqlalchemy import update
        
        lesson_id = event_data.get('data', {}).get('lesson_id')
        if lesson_id:
            try:
                async with get_db_session() as db:
                    # Отмечаем, что к уроку назначено ДЗ
                    stmt = update(Lesson).where(
                        Lesson.id == lesson_id
                    ).values(homework_assigned=True)
                    
                    await db.execute(stmt)
                    await db.commit()
                    
                    logger.info(f"Marked homework assigned for lesson {lesson_id}")
                    
            except Exception as e:
                logger.error(f"Failed to update lesson homework status: {e}")
    
    async def _handle_homework_submitted(self, event_data: Dict[str, Any]):
        """Обработка сдачи домашнего задания."""
        lesson_id = event_data.get('data', {}).get('lesson_id')
        logger.info(f"Homework submitted for lesson {lesson_id}")
    
    async def _handle_homework_checked(self, event_data: Dict[str, Any]):
        """Обработка проверки домашнего задания."""
        lesson_id = event_data.get('data', {}).get('lesson_id')
        logger.info(f"Homework checked for lesson {lesson_id}")


class EventManager:
    """Менеджер для управления publisher и consumer."""
    
    def __init__(self):
        self.publisher = LessonEventPublisher()
        self.consumer = LessonEventConsumer()
    
    async def initialize(self):
        """Инициализация event manager."""
        await self.publisher.initialize()
        await self.consumer.initialize()
    
    async def start(self):
        """Запуск event processing."""
        await self.consumer.start_consuming()
    
    async def stop(self):
        """Остановка event processing."""
        await self.consumer.stop_consuming()
        await self.publisher.close()


# Глобальный экземпляр event manager
event_manager = EventManager()