from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, Integer, String, Boolean

from ..core.database import Base


class NotificationChannel(str, Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    channel = Column(SqlEnum(NotificationChannel), nullable=False)
    is_enabled = Column(Boolean, default=True)
    schedule = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    channel = Column(SqlEnum(NotificationChannel), nullable=False)
    payload = Column(String(1024), nullable=False)
    status = Column(String(32), default="queued", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
