from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, Float, Integer, String

from ..core.database import Base


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, nullable=False)
    tutor_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="RUB", nullable=False)
    status = Column(SqlEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    method = Column(String(64), nullable=False)
    description = Column(String(255), nullable=True)
    invoice_id = Column(String(64), unique=True, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
