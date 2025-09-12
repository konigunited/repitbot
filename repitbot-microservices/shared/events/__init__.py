# -*- coding: utf-8 -*-
"""
Shared events package for RepitBot microservices.

This package provides event-driven architecture components including:
- Base event classes
- Typed domain events
- Event handlers and publishers
- Event store interfaces
- Event bus for in-memory handling
"""

from .base import (
    # Base classes
    BaseEvent,
    EventHandler,
    EventPublisher,
    EventStore,
    EventBus,
    EventFactory,
    
    # User domain events
    UserCreatedEvent,
    UserUpdatedEvent, 
    UserDeletedEvent,
    
    # Lesson domain events
    LessonCreatedEvent,
    LessonUpdatedEvent,
    LessonCancelledEvent,
    LessonRescheduledEvent,
    LessonConductedEvent,
    
    # Homework domain events
    HomeworkAssignedEvent,
    HomeworkSubmittedEvent,
    HomeworkCheckedEvent,
    
    # Payment domain events
    PaymentCreatedEvent,
    PaymentUpdatedEvent,
    
    # Achievement domain events
    AchievementEarnedEvent,
    
    # Notification domain events
    NotificationSentEvent,
    NotificationFailedEvent,
    
    # Material domain events
    MaterialCreatedEvent,
    MaterialUpdatedEvent,
    MaterialDeletedEvent,
)

__all__ = [
    # Base classes
    "BaseEvent",
    "EventHandler", 
    "EventPublisher",
    "EventStore",
    "EventBus",
    "EventFactory",
    
    # User domain events
    "UserCreatedEvent",
    "UserUpdatedEvent",
    "UserDeletedEvent",
    
    # Lesson domain events  
    "LessonCreatedEvent",
    "LessonUpdatedEvent",
    "LessonCancelledEvent",
    "LessonRescheduledEvent", 
    "LessonConductedEvent",
    
    # Homework domain events
    "HomeworkAssignedEvent",
    "HomeworkSubmittedEvent",
    "HomeworkCheckedEvent",
    
    # Payment domain events
    "PaymentCreatedEvent",
    "PaymentUpdatedEvent",
    
    # Achievement domain events
    "AchievementEarnedEvent",
    
    # Notification domain events
    "NotificationSentEvent",
    "NotificationFailedEvent",
    
    # Material domain events
    "MaterialCreatedEvent", 
    "MaterialUpdatedEvent",
    "MaterialDeletedEvent",
]