# -*- coding: utf-8 -*-
"""
Shared enums for RepitBot microservices architecture.
Extracted from the original monolithic application to ensure consistency across all services.
"""
import enum


class UserRole(enum.Enum):
    """User roles in the system."""
    TUTOR = "tutor"
    STUDENT = "student" 
    PARENT = "parent"


class HomeworkStatus(enum.Enum):
    """Homework completion and checking status."""
    PENDING = "pending"         # Ожидает выполнения
    SUBMITTED = "submitted"     # Выполнено учеником
    CHECKED = "checked"         # Проверено репетитором


class TopicMastery(enum.Enum):
    """Student's mastery level of a topic."""
    NOT_LEARNED = "not_learned"  # Не изучено
    LEARNED = "learned"          # Изучено
    MASTERED = "mastered"        # Освоено


class AttendanceStatus(enum.Enum):
    """Lesson attendance status."""
    ATTENDED = "attended"                    # Посетил урок
    EXCUSED_ABSENCE = "excused_absence"      # Уважительная причина
    UNEXCUSED_ABSENCE = "unexcused_absence"  # Неуважительный пропуск
    RESCHEDULED = "rescheduled"              # Урок перенесен


class LessonStatus(enum.Enum):
    """Lesson conduction status."""
    NOT_CONDUCTED = "not_conducted"  # Урок не проведен (по умолчанию)
    CONDUCTED = "conducted"          # Урок проведен


class ServiceStatus(enum.Enum):
    """Microservice health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class EventType(enum.Enum):
    """Event types for inter-service communication."""
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    # Lesson events
    LESSON_CREATED = "lesson.created"
    LESSON_UPDATED = "lesson.updated"
    LESSON_CANCELLED = "lesson.cancelled"
    LESSON_RESCHEDULED = "lesson.rescheduled"
    LESSON_CONDUCTED = "lesson.conducted"
    
    # Homework events
    HOMEWORK_ASSIGNED = "homework.assigned"
    HOMEWORK_SUBMITTED = "homework.submitted"
    HOMEWORK_CHECKED = "homework.checked"
    
    # Payment events
    PAYMENT_CREATED = "payment.created"
    PAYMENT_UPDATED = "payment.updated"
    
    # Achievement events
    ACHIEVEMENT_EARNED = "achievement.earned"
    
    # Notification events
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"
    
    # Material events
    MATERIAL_CREATED = "material.created"
    MATERIAL_UPDATED = "material.updated"
    MATERIAL_DELETED = "material.deleted"


class NotificationChannel(enum.Enum):
    """Available notification channels."""
    TELEGRAM = "telegram"
    EMAIL = "email" 
    SMS = "sms"
    PUSH = "push"


class NotificationPriority(enum.Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class PaymentStatus(enum.Enum):
    """Payment processing status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class DatabaseOperation(enum.Enum):
    """Database operation types for event sourcing."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SOFT_DELETE = "soft_delete"


class AchievementType(enum.Enum):
    """Types of student achievements."""
    POINTS_MILESTONE = "points_milestone"     # По баллам
    STREAK_MILESTONE = "streak_milestone"     # По дням подряд
    HOMEWORK_MASTER = "homework_master"       # По домашним заданиям
    LESSON_MILESTONE = "lesson_milestone"     # По количеству уроков
    PROGRESS_MILESTONE = "progress_milestone" # По прогрессу изучения
    SPECIAL_EVENT = "special_event"          # Особые события


class MaterialGrade(enum.Enum):
    """Educational material grade levels."""
    GRADE_1 = 1
    GRADE_2 = 2
    GRADE_3 = 3
    GRADE_4 = 4
    GRADE_5 = 5
    GRADE_6 = 6
    GRADE_7 = 7
    GRADE_8 = 8
    GRADE_9 = 9
    GRADE_10 = 10
    GRADE_11 = 11
    UNIVERSAL = 0  # Для всех классов


class SchedulerJobStatus(enum.Enum):
    """Scheduled job status."""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# TODO: Add more enums as microservices are developed
# - AuthenticationMethod
# - AnalyticsMetricType  
# - ReportType
# - ConfigurationType