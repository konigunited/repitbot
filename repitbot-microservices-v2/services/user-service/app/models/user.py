from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, Integer, String, Boolean
from sqlalchemy.orm import validates

from ..core.database import Base


class UserRole(str, Enum):
    TUTOR = "tutor"
    STUDENT = "student"
    PARENT = "parent"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    telegram_id = Column(String(64), unique=True, nullable=True, index=True)
    role = Column(SqlEnum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True)
    access_code = Column(String(16), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @validates("email")
    def validate_email(self, key, value):  # noqa: D401 - SQLAlchemy hook
        if "@" not in value:
            raise ValueError("Invalid email address")
        return value.lower()

    @validates("access_code")
    def validate_access_code(self, key, value):
        if len(value) < 6:
            raise ValueError("Access code must be at least 6 characters long")
        return value.upper()
