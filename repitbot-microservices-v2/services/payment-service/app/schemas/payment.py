from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class PaymentBase(BaseModel):
    student_id: int = Field(gt=0)
    tutor_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    currency: str = Field(default="RUB", max_length=8)
    method: str
    description: Optional[str] = None


class PaymentCreate(PaymentBase):
    invoice_id: Optional[str] = None


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    description: Optional[str] = None
    paid_at: Optional[datetime] = None


class PaymentOut(PaymentBase):
    id: int
    status: PaymentStatus
    invoice_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
