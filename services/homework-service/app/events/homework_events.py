# -*- coding: utf-8 -*-
"""
Система событий для Homework Service.
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
from ..models.homework import Homework, HomeworkSubmission

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class HomeworkEvent:
    """Базовый класс для событий домашних заданий."""
    event_type: str
    homework_id: int
    lesson_id: int
    student_id: int
    tutor_id: int
    timestamp: datetime
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HomeworkEvent':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class HomeworkEventPublisher:
    """
    Publisher для отправки событий о домашних заданиях.
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
            logger.info("Homework event publisher initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize homework event publisher: {e}")
            self._is_connected = False
            raise
    
    async def close(self):
        """Закрытие подключения."""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            self._is_connected = False
            logger.info("Homework event publisher connection closed")
        except Exception as e:
            logger.error(f"Error closing homework event publisher: {e}")
    
    async def publish_event(self, event: HomeworkEvent, routing_key: str):
        """Публикация события."""
        if not self._is_connected or not self.exchange:
            logger.warning("Homework event publisher not connected, skipping event")
            return
        
        try:
            message_body = json.dumps(event.to_dict(), ensure_ascii=False)
            
            await self.exchange.publish(
                aio_pika.Message(
                    message_body.encode('utf-8'),
                    content_type='application/json',
                    headers={
                        'event_type': event.event_type,
                        'service': 'homework-service',
                        'version': '1.0'
                    }
                ),
                routing_key=routing_key
            )
            
            logger.info(f"Published homework event {event.event_type} for homework {event.homework_id}")
            
        except Exception as e:
            logger.error(f"Failed to publish homework event {event.event_type}: {e}")
            raise
    
    async def publish_homework_assigned(self, homework: Homework):
        """Событие назначения домашнего задания."""
        event = HomeworkEvent(
            event_type="homework.assigned",
            homework_id=homework.id,
            lesson_id=homework.lesson_id,
            student_id=homework.student_id,
            tutor_id=homework.tutor_id,
            timestamp=datetime.now(),
            data={
                "description": homework.description,
                "deadline": homework.deadline.isoformat() if homework.deadline else None,
                "max_attempts": homework.max_attempts,
                "weight": homework.weight,
                "created_by": homework.created_by
            }
        )
        
        await self.publish_event(event, f"{settings.HOMEWORK_EVENT_ROUTING_KEY}.assigned")
    
    async def publish_homework_updated(self, homework: Homework, old_data: Dict[str, Any]):
        """Событие обновления домашнего задания."""
        event = HomeworkEvent(
            event_type="homework.updated",
            homework_id=homework.id,
            lesson_id=homework.lesson_id,
            student_id=homework.student_id,
            tutor_id=homework.tutor_id,
            timestamp=datetime.now(),
            data={
                "description": homework.description,
                "status": homework.status.value,
                "deadline": homework.deadline.isoformat() if homework.deadline else None,
                "old_data": old_data
            }
        )
        
        await self.publish_event(event, f"{settings.HOMEWORK_EVENT_ROUTING_KEY}.updated")
    
    async def publish_homework_submitted(self, homework: Homework, submission: HomeworkSubmission):
        """Событие сдачи домашнего задания."""
        event = HomeworkEvent(
            event_type="homework.submitted",
            homework_id=homework.id,
            lesson_id=homework.lesson_id,
            student_id=homework.student_id,
            tutor_id=homework.tutor_id,
            timestamp=datetime.now(),
            data={
                "submission_id": submission.id,
                "attempt_number": submission.attempt_number,
                "submission_type": submission.submission_type.value,
                "has_text": bool(submission.text_content),
                "file_count": len(submission.files) if submission.files else 0,
                "submitted_at": submission.submitted_at.isoformat()
            }
        )
        
        await self.publish_event(event, f"{settings.HOMEWORK_EVENT_ROUTING_KEY}.submitted")
    
    async def publish_homework_checked(self, homework: Homework, grade: Optional[float] = None):
        """Событие проверки домашнего задания."""
        event = HomeworkEvent(
            event_type="homework.checked",
            homework_id=homework.id,
            lesson_id=homework.lesson_id,
            student_id=homework.student_id,
            tutor_id=homework.tutor_id,
            timestamp=datetime.now(),
            data={
                "check_status": homework.check_status.value if homework.check_status else None,
                "grade": grade,
                "feedback": homework.feedback,
                "checked_at": homework.checked_at.isoformat() if homework.checked_at else None,
                "checked_by": homework.checked_by
            }
        )
        
        await self.publish_event(event, f"{settings.HOMEWORK_EVENT_ROUTING_KEY}.checked")
    
    async def publish_homework_overdue(self, homework: Homework):
        """Событие просрочки домашнего задания."""
        event = HomeworkEvent(
            event_type="homework.overdue",
            homework_id=homework.id,
            lesson_id=homework.lesson_id,
            student_id=homework.student_id,
            tutor_id=homework.tutor_id,
            timestamp=datetime.now(),
            data={
                "deadline": homework.deadline.isoformat() if homework.deadline else None,
                "days_overdue": (datetime.now() - homework.deadline).days if homework.deadline else 0,
                "status": homework.status.value
            }
        )
        
        await self.publish_event(event, f"{settings.HOMEWORK_EVENT_ROUTING_KEY}.overdue")
    
    async def publish_homework_reminder_needed(self, homework: Homework, hours_before: int):
        """Событие необходимости отправки напоминания о дедлайне."""
        event = HomeworkEvent(
            event_type="homework.reminder_needed",
            homework_id=homework.id,
            lesson_id=homework.lesson_id,
            student_id=homework.student_id,
            tutor_id=homework.tutor_id,
            timestamp=datetime.now(),
            data={
                "deadline": homework.deadline.isoformat() if homework.deadline else None,
                "hours_before": hours_before,
                "description": homework.description[:100] + "..." if len(homework.description) > 100 else homework.description
            }
        )
        
        await self.publish_event(event, f"{settings.HOMEWORK_EVENT_ROUTING_KEY}.reminder")
    
    async def publish_file_uploaded(self, homework: Homework, file_info: Dict[str, Any]):
        """Событие загрузки файла."""
        event = HomeworkEvent(
            event_type="homework.file_uploaded",
            homework_id=homework.id,
            lesson_id=homework.lesson_id,
            student_id=homework.student_id,
            tutor_id=homework.tutor_id,
            timestamp=datetime.now(),
            data={
                "file_id": file_info.get("id"),
                "filename": file_info.get("filename"),
                "file_type": file_info.get("file_type"),
                "file_size": file_info.get("file_size"),
                "uploaded_by": file_info.get("uploaded_by")
            }
        )
        
        await self.publish_event(event, f"{settings.HOMEWORK_EVENT_ROUTING_KEY}.file_uploaded")


class HomeworkEventConsumer:
    """
    Consumer для обработки входящих событий от других сервисов.
    Обрабатывает события от Lesson Service и User Service.
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
            
            logger.info("Homework event consumer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize homework event consumer: {e}")
            raise
    
    async def start_consuming(self):
        """Запуск потребления событий."""
        if self._is_running:
            return
        
        try:
            # Очередь для событий уроков
            lesson_queue = await self.channel.declare_queue(
                "homework_service_lesson_events",
                durable=True
            )
            
            # Привязка к routing keys для уроков
            await lesson_queue.bind(self.exchange, "lesson.created")
            await lesson_queue.bind(self.exchange, "lesson.updated")
            await lesson_queue.bind(self.exchange, "lesson.cancelled")
            await lesson_queue.bind(self.exchange, "lesson.completed")
            
            # Очередь для событий пользователей
            user_queue = await self.channel.declare_queue(
                "homework_service_user_events",
                durable=True
            )
            
            # Привязка к routing keys для пользователей
            await user_queue.bind(self.exchange, "user.updated")
            await user_queue.bind(self.exchange, "user.deleted")
            
            # Запуск потребления
            await lesson_queue.consume(self.handle_lesson_event)
            await user_queue.consume(self.handle_user_event)
            
            self._is_running = True
            logger.info("Started consuming homework events")
            
        except Exception as e:
            logger.error(f"Failed to start consuming homework events: {e}")
            raise
    
    async def stop_consuming(self):
        """Остановка потребления событий."""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            self._is_running = False
            logger.info("Stopped consuming homework events")
        except Exception as e:
            logger.error(f"Error stopping homework event consumer: {e}")
    
    async def handle_lesson_event(self, message: AbstractIncomingMessage):
        """Обработчик событий уроков."""
        try:
            async with message.process():
                event_data = json.loads(message.body.decode('utf-8'))
                event_type = event_data.get('event_type')
                
                logger.info(f"Received lesson event: {event_type}")
                
                if event_type == "lesson.created":
                    await self._handle_lesson_created(event_data)
                elif event_type == "lesson.updated":
                    await self._handle_lesson_updated(event_data)
                elif event_type == "lesson.cancelled":
                    await self._handle_lesson_cancelled(event_data)
                elif event_type == "lesson.completed":
                    await self._handle_lesson_completed(event_data)
                
        except Exception as e:
            logger.error(f"Failed to handle lesson event: {e}")
    
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
    
    async def _handle_lesson_created(self, event_data: Dict[str, Any]):
        """Обработка создания урока."""
        lesson_id = event_data.get('lesson_id')
        logger.info(f"Lesson {lesson_id} was created")
        # TODO: Возможно создать шаблон ДЗ для нового урока
    
    async def _handle_lesson_updated(self, event_data: Dict[str, Any]):
        """Обработка обновления урока."""
        lesson_id = event_data.get('lesson_id')
        logger.info(f"Lesson {lesson_id} was updated")
    
    async def _handle_lesson_cancelled(self, event_data: Dict[str, Any]):
        """Обработка отмены урока."""
        from ..database.connection import get_db_session
        from ..models.homework import Homework, HomeworkStatus
        from sqlalchemy import update
        
        lesson_id = event_data.get('lesson_id')
        
        try:
            async with get_db_session() as db:
                # Отменяем все домашние задания для отмененного урока
                stmt = update(Homework).where(
                    Homework.lesson_id == lesson_id,
                    Homework.status == HomeworkStatus.PENDING
                ).values(
                    status=HomeworkStatus.CHECKED,
                    feedback="Урок отменен",
                    checked_at=datetime.now()
                )
                
                await db.execute(stmt)
                await db.commit()
                
                logger.info(f"Cancelled homework for lesson {lesson_id}")
                
        except Exception as e:
            logger.error(f"Failed to cancel homework for lesson {lesson_id}: {e}")
    
    async def _handle_lesson_completed(self, event_data: Dict[str, Any]):
        """Обработка завершения урока."""
        lesson_id = event_data.get('lesson_id')
        logger.info(f"Lesson {lesson_id} was completed")
        # TODO: Возможно создать автоматическое ДЗ после урока
    
    async def _handle_user_updated(self, event_data: Dict[str, Any]):
        """Обработка обновления пользователя."""
        user_id = event_data.get('user_id')
        logger.info(f"User {user_id} was updated")
    
    async def _handle_user_deleted(self, event_data: Dict[str, Any]):
        """Обработка удаления пользователя."""
        user_id = event_data.get('user_id')
        logger.info(f"User {user_id} was deleted")
        # TODO: Архивировать или удалить домашние задания пользователя


class HomeworkEventManager:
    """Менеджер для управления publisher и consumer."""
    
    def __init__(self):
        self.publisher = HomeworkEventPublisher()
        self.consumer = HomeworkEventConsumer()
    
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
homework_event_manager = HomeworkEventManager()