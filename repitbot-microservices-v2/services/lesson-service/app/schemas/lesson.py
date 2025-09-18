from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LessonStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class LessonBase(BaseModel):
    tutor_id: int = Field(gt=0)
    student_id: int = Field(gt=0)
    subject: str
    topic: str
    scheduled_at: datetime
    duration_minutes: int = 60
    notes: Optional[str] = None


class LessonCreate(LessonBase):
    pass


class LessonUpdate(BaseModel):
    topic: Optional[str] = None
    status: Optional[LessonStatus] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None


class LessonOut(LessonBase):
    id: int
    status: LessonStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
