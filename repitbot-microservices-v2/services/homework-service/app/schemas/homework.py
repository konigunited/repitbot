from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HomeworkStatus(str, Enum):
    assigned = "assigned"
    submitted = "submitted"
    reviewed = "reviewed"
    completed = "completed"


class HomeworkBase(BaseModel):
    lesson_id: int = Field(gt=0)
    tutor_id: int = Field(gt=0)
    student_id: int = Field(gt=0)
    title: str
    description: Optional[str] = None
    resources: Optional[str] = None
    deadline: Optional[datetime] = None


class HomeworkCreate(HomeworkBase):
    pass


class HomeworkUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    resources: Optional[str] = None
    status: Optional[HomeworkStatus] = None
    deadline: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    feedback: Optional[str] = None


class HomeworkOut(HomeworkBase):
    id: int
    status: HomeworkStatus
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
