from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserRole(str, Enum):
    tutor = "tutor"
    student = "student"
    parent = "parent"
    admin = "admin"


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role: UserRole
    telegram_id: Optional[str] = None


class UserCreate(UserBase):
    access_code: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    telegram_id: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(UserBase):
    id: int
    is_active: bool
    access_code: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
