# -*- coding: utf-8 -*-
"""
Event Bus for Microservices Communication
Общий Event Bus для обмена событиями между микросервисами
"""
import asyncio
import aio_pika
import json
import logging
import uuid
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
import os

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Типы событий в системе"""
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    # Lesson events
    LESSON_CREATED = "lesson.created"
    LESSON_UPDATED = "lesson.updated"
    LESSON_COMPLETED = "lesson.completed"
    LESSON_CANCELLED = "lesson.cancelled"
    
    # Homework events
    HOMEWORK_CREATED = "homework.created"
    HOMEWORK_SUBMITTED = "homework.submitted"
    HOMEWORK_GRADED = "homework.graded"
    HOMEWORK_REVIEWED = "homework.reviewed"
    
    # Payment events
    PAYMENT_CREATED = "payment.created"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    BALANCE_UPDATED = "balance.updated"
    
    # Material events
    MATERIAL_UPLOADED = "material.uploaded"
    MATERIAL_ACCESSED = "material.accessed"
    MATERIAL_DOWNLOADED = "material.downloaded"
    
    # Notification events
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_DELIVERED = "notification.delivered"
    NOTIFICATION_FAILED = "notification.failed"
    
    # Student events
    STUDENT_CREATED = "student.created"
    STUDENT_LEVEL_UP = "student.level_up"
    ACHIEVEMENT_EARNED = "achievement.earned"
    STREAK_UPDATED = "streak.updated"
    XP_EARNED = "xp.earned"
    
    # Analytics events
    ANALYTICS_COMPUTED = "analytics.computed"
    REPORT_GENERATED = "report.generated"

@dataclass
class Event:
    """Базовый класс события"""
    event_id: str
    event_type: EventType
    source_service: str
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    user_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def create(
        cls, 
        event_type: EventType, 
        source_service: str, 
        data: Dict[str, Any],
        user_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "Event":
        """Создание нового события"""
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            source_service=source_service,
            timestamp=datetime.now(),
            data=data,
            user_id=user_id,
            correlation_id=correlation_id,
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для сериализации"""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Создание события из словаря"""
        data["event_type"] = EventType(data["event_type"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

class EventBus:
    """Event Bus для обмена событиями между микросервисами"""
    
    def __init__(self, rabbitmq_url: str = None):
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None
        self.exchange_name = "repitbot_events"
        self.service_name = os.getenv("SERVICE_NAME", "unknown-service")
        
        # Хранилище обработчиков событий
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        self._consumer_tag: Optional[str] = None
        
        # Настройки
        self.retry_attempts = 3
        self.retry_delay = 5
        
    async def connect(self):
        """Подключение к RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()
            
            # Создаем exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Создаем очередь для сервиса
            queue_name = f"{self.service_name}_events"
            self.queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                auto_delete=False
            )
            
            logger.info(f"Connected to RabbitMQ, queue: {queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self):
        """Отключение от RabbitMQ"""
        try:
            if self._consumer_tag:
                await self.queue.cancel(self._consumer_tag)
                self._consumer_tag = None
                
            if self.connection:
                await self.connection.close()
                
            logger.info("Disconnected from RabbitMQ")
            
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    async def publish_event(self, event: Event):
        """Публикация события"""
        try:
            if not self.channel:
                await self.connect()
            
            # Сериализуем событие
            message_body = json.dumps(event.to_dict(), ensure_ascii=False)
            
            # Создаем routing key
            routing_key = event.event_type.value
            
            # Публикуем сообщение
            message = aio_pika.Message(
                message_body.encode(),
                headers={
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "source_service": event.source_service,
                    "timestamp": event.timestamp.isoformat(),
                    "user_id": str(event.user_id) if event.user_id else None,
                    "correlation_id": event.correlation_id
                },
                message_id=event.event_id,
                timestamp=event.timestamp,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            
            await self.exchange.publish(
                message,
                routing_key=routing_key
            )
            
            logger.debug(f"Published event {event.event_id}: {event.event_type.value}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")
            raise
    
    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """Подписка на тип события"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        
        self._event_handlers[event_type].append(handler)
        logger.info(f"Subscribed to {event_type.value}")
    
    async def start_consuming(self):
        """Запуск прослушивания событий"""
        try:
            if not self.channel:
                await self.connect()
            
            # Привязываем очередь к routing keys
            for event_type in self._event_handlers.keys():
                await self.queue.bind(
                    self.exchange,
                    routing_key=event_type.value
                )
                logger.info(f"Bound queue to {event_type.value}")
            
            # Начинаем потребление
            await self.queue.consume(self._handle_message)
            logger.info("Started consuming events")
            
        except Exception as e:
            logger.error(f"Failed to start consuming: {e}")
            raise
    
    async def _handle_message(self, message: aio_pika.IncomingMessage):
        """Обработка входящего сообщения"""
        try:
            async with message.process():
                # Десериализуем событие
                event_data = json.loads(message.body.decode())
                event = Event.from_dict(event_data)
                
                # Находим обработчики для данного типа события
                handlers = self._event_handlers.get(event.event_type, [])
                
                if not handlers:
                    logger.warning(f"No handlers for event {event.event_type.value}")
                    return
                
                # Выполняем обработчики
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                        
                        logger.debug(f"Handled event {event.event_id} with {handler.__name__}")
                        
                    except Exception as e:
                        logger.error(f"Handler {handler.__name__} failed for event {event.event_id}: {e}")
                        # Продолжаем выполнение других обработчиков
                
        except Exception as e:
            logger.error(f"Failed to handle message: {e}")
            # Отклоняем сообщение для повторной обработки
            await message.reject(requeue=True)
    
    async def publish_user_created(self, user_data: Dict[str, Any]):
        """Публикация события создания пользователя"""
        event = Event.create(
            event_type=EventType.USER_CREATED,
            source_service=self.service_name,
            data=user_data,
            user_id=user_data.get("id")
        )
        await self.publish_event(event)
    
    async def publish_lesson_completed(self, lesson_data: Dict[str, Any]):
        """Публикация события завершения урока"""
        event = Event.create(
            event_type=EventType.LESSON_COMPLETED,
            source_service=self.service_name,
            data=lesson_data,
            user_id=lesson_data.get("student_id")
        )
        await self.publish_event(event)
    
    async def publish_homework_submitted(self, homework_data: Dict[str, Any]):
        """Публикация события отправки домашки"""
        event = Event.create(
            event_type=EventType.HOMEWORK_SUBMITTED,
            source_service=self.service_name,
            data=homework_data,
            user_id=homework_data.get("student_id")
        )
        await self.publish_event(event)
    
    async def publish_payment_completed(self, payment_data: Dict[str, Any]):
        """Публикация события завершения платежа"""
        event = Event.create(
            event_type=EventType.PAYMENT_COMPLETED,
            source_service=self.service_name,
            data=payment_data,
            user_id=payment_data.get("user_id")
        )
        await self.publish_event(event)
    
    async def publish_student_level_up(self, level_data: Dict[str, Any]):
        """Публикация события повышения уровня"""
        event = Event.create(
            event_type=EventType.STUDENT_LEVEL_UP,
            source_service=self.service_name,
            data=level_data,
            user_id=level_data.get("user_id")
        )
        await self.publish_event(event)
    
    async def publish_achievement_earned(self, achievement_data: Dict[str, Any]):
        """Публикация события получения достижения"""
        event = Event.create(
            event_type=EventType.ACHIEVEMENT_EARNED,
            source_service=self.service_name,
            data=achievement_data,
            user_id=achievement_data.get("user_id")
        )
        await self.publish_event(event)

# Глобальный экземпляр Event Bus
_event_bus: Optional[EventBus] = None

def get_event_bus(service_name: str = None) -> EventBus:
    """Получение глобального экземпляра Event Bus"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        if service_name:
            _event_bus.service_name = service_name
    return _event_bus

async def init_event_bus(service_name: str, rabbitmq_url: str = None) -> EventBus:
    """Инициализация Event Bus"""
    global _event_bus
    _event_bus = EventBus(rabbitmq_url)
    _event_bus.service_name = service_name
    await _event_bus.connect()
    return _event_bus

async def cleanup_event_bus():
    """Очистка Event Bus"""
    global _event_bus
    if _event_bus:
        await _event_bus.disconnect()
        _event_bus = None