# -*- coding: utf-8 -*-
"""
Payment Service Schemas
Pydantic models for request/response validation
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, validator, ConfigDict

from ..models.payment import PaymentStatus, PaymentType, TransactionType


# Base schemas
class PaymentBase(BaseModel):
    """Base payment schema"""
    student_id: int = Field(..., description="Student ID")
    lessons_paid: int = Field(..., gt=0, description="Number of lessons paid for")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    price_per_lesson: Decimal = Field(..., gt=0, description="Price per lesson")
    payment_type: PaymentType = Field(default=PaymentType.LESSON_PAYMENT)
    payment_method: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    notes: Optional[str] = None

    @validator('amount', 'price_per_lesson')
    def validate_decimal_places(cls, v):
        """Ensure decimal has at most 2 decimal places"""
        if v.as_tuple().exponent < -2:
            raise ValueError('Maximum 2 decimal places allowed')
        return v

    @validator('lessons_paid')
    def validate_lessons_positive(cls, v):
        """Ensure lessons count is positive"""
        if v <= 0:
            raise ValueError('Lessons count must be positive')
        return v


class PaymentCreate(PaymentBase):
    """Schema for creating payment"""
    pass


class PaymentUpdate(BaseModel):
    """Schema for updating payment"""
    status: Optional[PaymentStatus] = None
    payment_method: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    processed_by_user_id: Optional[int] = None


class PaymentResponse(PaymentBase):
    """Schema for payment response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: PaymentStatus
    payment_date: datetime
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    processed_by_user_id: Optional[int] = None
    external_payment_id: Optional[str] = None


# Balance schemas
class BalanceResponse(BaseModel):
    """Schema for balance response"""
    model_config = ConfigDict(from_attributes=True)
    
    student_id: int
    current_balance: int
    total_lessons_paid: int
    lessons_consumed: int
    total_amount_paid: Decimal
    total_amount_spent: Decimal
    last_payment_date: Optional[datetime] = None
    last_lesson_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class BalanceUpdate(BaseModel):
    """Schema for balance operations"""
    student_id: int
    lessons_count: int = Field(..., description="Lessons to add (positive) or deduct (negative)")
    amount: Optional[Decimal] = Field(None, description="Associated amount")
    description: str = Field(..., description="Description of the operation")
    reference_id: Optional[str] = Field(None, description="External reference ID")
    lesson_id: Optional[int] = Field(None, description="Associated lesson ID")
    created_by_user_id: Optional[int] = Field(None, description="User who created the operation")


# Transaction schemas
class TransactionBase(BaseModel):
    """Base transaction schema"""
    student_id: int
    transaction_type: TransactionType
    amount: Decimal = Field(..., description="Money amount")
    lessons_count: int = Field(..., description="Lessons count change")
    description: str = Field(..., max_length=255)
    reference_id: Optional[str] = None
    lesson_id: Optional[int] = None


class TransactionResponse(TransactionBase):
    """Schema for transaction response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    balance_before: int
    balance_after: int
    payment_id: Optional[int] = None
    balance_id: int
    created_at: datetime
    created_by_user_id: Optional[int] = None


# Invoice schemas
class InvoiceBase(BaseModel):
    """Base invoice schema"""
    student_id: int
    amount: Decimal = Field(..., gt=0)
    lessons_count: int = Field(..., gt=0)
    price_per_lesson: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None


class InvoiceCreate(InvoiceBase):
    """Schema for creating invoice"""
    pass


class InvoiceResponse(InvoiceBase):
    """Schema for invoice response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    invoice_number: str
    status: PaymentStatus
    issue_date: datetime
    paid_date: Optional[datetime] = None
    payment_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# List schemas
class PaymentListResponse(BaseModel):
    """Schema for paginated payment list"""
    payments: List[PaymentResponse]
    total: int
    page: int
    per_page: int
    pages: int


class TransactionListResponse(BaseModel):
    """Schema for paginated transaction list"""
    transactions: List[TransactionResponse]
    total: int
    page: int
    per_page: int
    pages: int


class InvoiceListResponse(BaseModel):
    """Schema for paginated invoice list"""
    invoices: List[InvoiceResponse]
    total: int
    page: int
    per_page: int
    pages: int


# Quick operation schemas
class QuickPaymentRequest(BaseModel):
    """Schema for quick payment processing"""
    student_id: int = Field(..., description="Student ID")
    lessons_count: int = Field(..., gt=0, description="Number of lessons to pay for")
    price_per_lesson: Optional[Decimal] = Field(None, description="Price per lesson (auto-calculated if not provided)")
    payment_method: Optional[str] = Field(None, description="Payment method")
    description: Optional[str] = Field(None, description="Payment description")


class BalanceAdjustmentRequest(BaseModel):
    """Schema for manual balance adjustment"""
    student_id: int = Field(..., description="Student ID")
    lessons_adjustment: int = Field(..., description="Lessons to add (+) or subtract (-)")
    reason: str = Field(..., description="Reason for adjustment")
    authorized_by: int = Field(..., description="User ID who authorized the adjustment")


class PaymentSummaryResponse(BaseModel):
    """Schema for payment summary"""
    student_id: int
    total_payments: int
    total_amount_paid: Decimal
    total_lessons_paid: int
    current_balance: int
    average_price_per_lesson: Decimal
    last_payment_date: Optional[datetime] = None
    first_payment_date: Optional[datetime] = None


# Health check schema
class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    database_status: str
    event_handler_status: str