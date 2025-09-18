from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    telegram = "telegram"
    email = "email"
    sms = "sms"


class PreferenceBase(BaseModel):
    user_id: int = Field(gt=0)
    channel: NotificationChannel
    is_enabled: bool = True
    schedule: Optional[str] = Field(default=None, description="Cron-like schedule or simple alias")


class PreferenceCreate(PreferenceBase):
    pass


class PreferenceUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    schedule: Optional[str] = None


class PreferenceOut(PreferenceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    user_id: int
    channel: NotificationChannel
    message: str


class NotificationLogOut(BaseModel):
    id: int
    user_id: int
    channel: NotificationChannel
    payload: str
    status: str
    created_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True
