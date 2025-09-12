# -*- coding: utf-8 -*-
"""
Shared models package for RepitBot microservices.

Exports:
- Base model classes
- Common enums
- Database utilities
"""

from .base import (
    Base,
    BaseDBModel,
    BaseSchema,
    TimestampMixin,
    TimestampSchema,
    AuditMixin,
    SoftDeleteMixin,
    PaginationParams,
    PaginatedResponse,
    EventBase,
    HealthCheckResponse,
    APIResponse,
    DatabaseManager,
)

from .enums import (
    UserRole,
    HomeworkStatus,
    TopicMastery,
    AttendanceStatus,
    LessonStatus,
    ServiceStatus,
    EventType,
    NotificationChannel,
    NotificationPriority,
    PaymentStatus,
    DatabaseOperation,
    AchievementType,
    MaterialGrade,
    SchedulerJobStatus,
)

__all__ = [
    # Base classes
    "Base",
    "BaseDBModel", 
    "BaseSchema",
    "TimestampMixin",
    "TimestampSchema",
    "AuditMixin",
    "SoftDeleteMixin",
    "PaginationParams",
    "PaginatedResponse",
    "EventBase",
    "HealthCheckResponse",
    "APIResponse",
    "DatabaseManager",
    
    # Enums
    "UserRole",
    "HomeworkStatus",
    "TopicMastery", 
    "AttendanceStatus",
    "LessonStatus",
    "ServiceStatus",
    "EventType",
    "NotificationChannel",
    "NotificationPriority",
    "PaymentStatus",
    "DatabaseOperation",
    "AchievementType",
    "MaterialGrade",
    "SchedulerJobStatus",
]