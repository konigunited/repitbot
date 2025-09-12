# -*- coding: utf-8 -*-
"""
Base event classes and utilities for RepitBot microservices event-driven architecture.
Provides consistent event handling patterns across all services.
"""
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field

from ..models.enums import EventType


class BaseEvent(BaseModel):
    """Base event class for all domain events."""
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = Field(description="Type of event")
    service_name: str = Field(description="Service that generated the event") 
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    causation_id: Optional[str] = Field(None, description="Event that caused this event")
    user_id: Optional[int] = Field(None, description="User associated with event")
    aggregate_id: str = Field(description="ID of the aggregate that generated the event")
    aggregate_version: int = Field(default=1, description="Version of the aggregate")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_json(self) -> str:
        """Serialize event to JSON."""
        return self.model_dump_json()
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseEvent':
        """Deserialize event from JSON."""
        return cls.model_validate_json(json_str)
    
    def to_message_body(self) -> Dict[str, Any]:
        """Convert event to message broker format."""
        return {
            "headers": {
                "event_id": self.event_id,
                "event_type": self.event_type.value,
                "service_name": self.service_name,
                "timestamp": self.timestamp.isoformat(),
                "correlation_id": self.correlation_id,
                "causation_id": self.causation_id,
                "user_id": self.user_id,
            },
            "body": {
                "aggregate_id": self.aggregate_id,
                "aggregate_version": self.aggregate_version,
                "data": self.data,
                "metadata": self.metadata,
            }
        }


# User Domain Events
class UserCreatedEvent(BaseEvent):
    """Event fired when a new user is created."""
    event_type: EventType = EventType.USER_CREATED


class UserUpdatedEvent(BaseEvent):
    """Event fired when user information is updated."""
    event_type: EventType = EventType.USER_UPDATED


class UserDeletedEvent(BaseEvent):
    """Event fired when a user is deleted."""
    event_type: EventType = EventType.USER_DELETED


# Lesson Domain Events
class LessonCreatedEvent(BaseEvent):
    """Event fired when a new lesson is scheduled."""
    event_type: EventType = EventType.LESSON_CREATED


class LessonUpdatedEvent(BaseEvent):
    """Event fired when lesson details are updated."""
    event_type: EventType = EventType.LESSON_UPDATED


class LessonCancelledEvent(BaseEvent):
    """Event fired when a lesson is cancelled."""
    event_type: EventType = EventType.LESSON_CANCELLED


class LessonRescheduledEvent(BaseEvent):
    """Event fired when a lesson is rescheduled."""
    event_type: EventType = EventType.LESSON_RESCHEDULED


class LessonConductedEvent(BaseEvent):
    """Event fired when a lesson is marked as conducted."""
    event_type: EventType = EventType.LESSON_CONDUCTED


# Homework Domain Events  
class HomeworkAssignedEvent(BaseEvent):
    """Event fired when homework is assigned to a student."""
    event_type: EventType = EventType.HOMEWORK_ASSIGNED


class HomeworkSubmittedEvent(BaseEvent):
    """Event fired when student submits homework."""
    event_type: EventType = EventType.HOMEWORK_SUBMITTED


class HomeworkCheckedEvent(BaseEvent):
    """Event fired when tutor checks homework."""
    event_type: EventType = EventType.HOMEWORK_CHECKED


# Payment Domain Events
class PaymentCreatedEvent(BaseEvent):
    """Event fired when a payment is recorded."""
    event_type: EventType = EventType.PAYMENT_CREATED


class PaymentUpdatedEvent(BaseEvent):
    """Event fired when payment status is updated."""
    event_type: EventType = EventType.PAYMENT_UPDATED


# Achievement Domain Events
class AchievementEarnedEvent(BaseEvent):
    """Event fired when student earns an achievement."""
    event_type: EventType = EventType.ACHIEVEMENT_EARNED


# Notification Domain Events
class NotificationSentEvent(BaseEvent):
    """Event fired when notification is successfully sent."""
    event_type: EventType = EventType.NOTIFICATION_SENT


class NotificationFailedEvent(BaseEvent):
    """Event fired when notification sending fails."""
    event_type: EventType = EventType.NOTIFICATION_FAILED


# Material Domain Events
class MaterialCreatedEvent(BaseEvent):
    """Event fired when educational material is created."""
    event_type: EventType = EventType.MATERIAL_CREATED


class MaterialUpdatedEvent(BaseEvent):
    """Event fired when material is updated."""
    event_type: EventType = EventType.MATERIAL_UPDATED


class MaterialDeletedEvent(BaseEvent):
    """Event fired when material is deleted."""
    event_type: EventType = EventType.MATERIAL_DELETED


# Event Handler Interface
class EventHandler(ABC):
    """Abstract base class for event handlers."""
    
    @abstractmethod
    def can_handle(self, event: BaseEvent) -> bool:
        """Check if handler can process the event."""
        pass
    
    @abstractmethod
    async def handle(self, event: BaseEvent) -> None:
        """Process the event."""
        pass


# Event Publisher Interface
class EventPublisher(ABC):
    """Abstract base class for event publishers."""
    
    @abstractmethod
    async def publish(self, event: BaseEvent) -> None:
        """Publish event to message broker."""
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[BaseEvent]) -> None:
        """Publish multiple events in batch."""
        pass


# Event Store Interface
class EventStore(ABC):
    """Abstract base class for event storage."""
    
    @abstractmethod
    async def append_event(self, event: BaseEvent) -> None:
        """Store event in event store."""
        pass
    
    @abstractmethod
    async def get_events(
        self, 
        aggregate_id: str, 
        from_version: int = 0
    ) -> List[BaseEvent]:
        """Retrieve events for an aggregate."""
        pass
    
    @abstractmethod
    async def get_events_by_type(
        self, 
        event_type: EventType,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None
    ) -> List[BaseEvent]:
        """Retrieve events by type and time range."""
        pass


# Event Bus for in-memory event handling
class EventBus:
    """In-memory event bus for handling events within a service."""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
    
    def register_handler(self, event_type: EventType, handler: EventHandler):
        """Register event handler for specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def unregister_handler(self, event_type: EventType, handler: EventHandler):
        """Unregister event handler."""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
    
    async def publish(self, event: BaseEvent):
        """Publish event to registered handlers."""
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            if handler.can_handle(event):
                await handler.handle(event)


# Event Factory for creating typed events
class EventFactory:
    """Factory for creating typed events."""
    
    _event_classes: Dict[EventType, Type[BaseEvent]] = {
        EventType.USER_CREATED: UserCreatedEvent,
        EventType.USER_UPDATED: UserUpdatedEvent,
        EventType.USER_DELETED: UserDeletedEvent,
        EventType.LESSON_CREATED: LessonCreatedEvent,
        EventType.LESSON_UPDATED: LessonUpdatedEvent,
        EventType.LESSON_CANCELLED: LessonCancelledEvent,
        EventType.LESSON_RESCHEDULED: LessonRescheduledEvent,
        EventType.LESSON_CONDUCTED: LessonConductedEvent,
        EventType.HOMEWORK_ASSIGNED: HomeworkAssignedEvent,
        EventType.HOMEWORK_SUBMITTED: HomeworkSubmittedEvent,
        EventType.HOMEWORK_CHECKED: HomeworkCheckedEvent,
        EventType.PAYMENT_CREATED: PaymentCreatedEvent,
        EventType.PAYMENT_UPDATED: PaymentUpdatedEvent,
        EventType.ACHIEVEMENT_EARNED: AchievementEarnedEvent,
        EventType.NOTIFICATION_SENT: NotificationSentEvent,
        EventType.NOTIFICATION_FAILED: NotificationFailedEvent,
        EventType.MATERIAL_CREATED: MaterialCreatedEvent,
        EventType.MATERIAL_UPDATED: MaterialUpdatedEvent,
        EventType.MATERIAL_DELETED: MaterialDeletedEvent,
    }
    
    @classmethod
    def create_event(
        self,
        event_type: EventType,
        service_name: str,
        aggregate_id: str,
        data: Dict[str, Any],
        **kwargs
    ) -> BaseEvent:
        """Create typed event instance."""
        event_class = self._event_classes.get(event_type, BaseEvent)
        return event_class(
            event_type=event_type,
            service_name=service_name,
            aggregate_id=aggregate_id,
            data=data,
            **kwargs
        )
    
    @classmethod
    def from_message(cls, message: Dict[str, Any]) -> BaseEvent:
        """Create event from message broker message."""
        headers = message.get("headers", {})
        body = message.get("body", {})
        
        event_type = EventType(headers.get("event_type"))
        event_class = cls._event_classes.get(event_type, BaseEvent)
        
        return event_class(
            event_id=headers.get("event_id"),
            event_type=event_type,
            service_name=headers.get("service_name"),
            timestamp=datetime.fromisoformat(headers.get("timestamp")),
            correlation_id=headers.get("correlation_id"),
            causation_id=headers.get("causation_id"),
            user_id=headers.get("user_id"),
            aggregate_id=body.get("aggregate_id"),
            aggregate_version=body.get("aggregate_version", 1),
            data=body.get("data", {}),
            metadata=body.get("metadata", {}),
        )


# TODO: Implement concrete event store and publisher implementations:
# - Redis Event Store
# - RabbitMQ Event Publisher
# - Kafka Event Publisher
# - PostgreSQL Event Store