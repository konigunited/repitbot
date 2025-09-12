from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
from enum import Enum as PyEnum
from datetime import datetime
from typing import Optional, Dict, Any


class NotificationChannel(PyEnum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class NotificationStatus(PyEnum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationPriority(PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(PyEnum):
    LESSON_REMINDER = "lesson_reminder"
    LESSON_CANCELLED = "lesson_cancelled"
    HOMEWORK_ASSIGNED = "homework_assigned"
    HOMEWORK_OVERDUE = "homework_overdue"
    PAYMENT_PROCESSED = "payment_processed"
    BALANCE_LOW = "balance_low"
    MATERIAL_SHARED = "material_shared"
    SYSTEM_NOTIFICATION = "system_notification"
    CUSTOM = "custom"


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Recipient information
    user_id = Column(Integer, nullable=False, index=True)
    channel = Column(Enum(NotificationChannel), nullable=False)
    recipient_address = Column(String(255), nullable=False)  # email, telegram_id, phone, etc.
    
    # Notification content
    type = Column(Enum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    html_message = Column(Text, nullable=True)
    
    # Metadata
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, index=True)
    template_id = Column(Integer, ForeignKey("notification_templates.id"), nullable=True)
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Tracking
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    correlation_id = Column(String(100), nullable=True, index=True)  # For tracking related notifications
    
    # Context data for templates and processing
    context_data = Column(JSON, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    template = relationship("NotificationTemplate", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.type}, status={self.status})>"


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Template identification
    name = Column(String(100), unique=True, nullable=False, index=True)
    type = Column(Enum(NotificationType), nullable=False, index=True)
    channel = Column(Enum(NotificationChannel), nullable=False)
    language = Column(String(5), default="ru")
    
    # Template content
    subject_template = Column(String(255), nullable=False)
    body_template = Column(Text, nullable=False)
    html_template = Column(Text, nullable=True)
    
    # Template metadata
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    variables = Column(JSON, nullable=True)  # List of available template variables
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    notifications = relationship("Notification", back_populates="template")
    
    def __repr__(self):
        return f"<NotificationTemplate(id={self.id}, name={self.name}, type={self.type})>"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User and notification type
    user_id = Column(Integer, nullable=False, index=True)
    notification_type = Column(Enum(NotificationType), nullable=False)
    
    # Channel preferences
    telegram_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    
    # Timing preferences
    quiet_hours_start = Column(String(5), nullable=True)  # Format: "22:00"
    quiet_hours_end = Column(String(5), nullable=True)    # Format: "08:00"
    timezone = Column(String(50), default="Europe/Moscow")
    
    # Advanced settings
    digest_mode = Column(Boolean, default=False)  # Group similar notifications
    min_interval_minutes = Column(Integer, default=0)  # Minimum time between notifications
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<NotificationPreference(user_id={self.user_id}, type={self.notification_type})>"