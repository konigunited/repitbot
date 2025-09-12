# -*- coding: utf-8 -*-
"""
Payment Service Models
SQLAlchemy models for payment, balance, transaction, and invoice management
"""

import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Enum as SAEnum, 
    Boolean, Numeric, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class PaymentStatus(enum.Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentType(enum.Enum):
    """Payment type enumeration"""
    LESSON_PAYMENT = "lesson_payment"  # Payment for lessons
    BALANCE_TOPUP = "balance_topup"    # Balance top-up
    REFUND = "refund"                  # Refund payment


class TransactionType(enum.Enum):
    """Transaction type enumeration"""
    DEBIT = "debit"    # Money in / lessons added
    CREDIT = "credit"  # Money out / lessons deducted


class Payment(Base):
    """
    Payment model - records of payments made by students/parents
    Migrated and enhanced from existing Payment model
    """
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Payment details
    amount = Column(Numeric(10, 2), nullable=False, default=0.00)  # Payment amount in currency
    lessons_paid = Column(Integer, nullable=False, default=0)      # Number of lessons paid for
    price_per_lesson = Column(Numeric(8, 2), nullable=False, default=0.00)  # Price per lesson
    
    # Payment metadata
    payment_type = Column(SAEnum(PaymentType), default=PaymentType.LESSON_PAYMENT, nullable=False)
    status = Column(SAEnum(PaymentStatus), default=PaymentStatus.COMPLETED, nullable=False)
    payment_method = Column(String(50), nullable=True)  # cash, card, transfer, etc.
    external_payment_id = Column(String(255), nullable=True)  # External payment system ID
    
    # Dates
    payment_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # References
    student_id = Column(Integer, nullable=False, index=True)  # Reference to User service
    processed_by_user_id = Column(Integer, nullable=True)    # Who processed the payment
    
    # Additional info
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="payment", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_payments_student_date', 'student_id', 'payment_date'),
        Index('idx_payments_status', 'status'),
    )


class Balance(Base):
    """
    Balance model - current balance of lessons for each student
    Calculated from payments and lesson consumption
    """
    __tablename__ = 'balances'
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, nullable=False, unique=True, index=True)  # Reference to User service
    
    # Balance details
    total_lessons_paid = Column(Integer, nullable=False, default=0)      # Total lessons ever paid for
    lessons_consumed = Column(Integer, nullable=False, default=0)        # Total lessons consumed
    current_balance = Column(Integer, nullable=False, default=0)         # Current available lessons
    
    # Financial tracking
    total_amount_paid = Column(Numeric(10, 2), nullable=False, default=0.00)
    total_amount_spent = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    # Metadata
    last_payment_date = Column(DateTime, nullable=True)
    last_lesson_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="balance", cascade="all, delete-orphan")


class Transaction(Base):
    """
    Transaction model - detailed log of all balance changes
    Provides audit trail for financial operations
    """
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Transaction details
    transaction_type = Column(SAEnum(TransactionType), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False, default=0.00)  # Money amount
    lessons_count = Column(Integer, nullable=False, default=0)     # Lessons count change
    
    # Balance snapshot (for audit)
    balance_before = Column(Integer, nullable=False, default=0)
    balance_after = Column(Integer, nullable=False, default=0)
    
    # References
    student_id = Column(Integer, nullable=False, index=True)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=True)
    balance_id = Column(Integer, ForeignKey('balances.id'), nullable=False)
    lesson_id = Column(Integer, nullable=True, index=True)  # Reference to Lesson service
    
    # Metadata
    description = Column(String(255), nullable=False)
    reference_id = Column(String(255), nullable=True)  # External reference
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_user_id = Column(Integer, nullable=True)  # Who created the transaction
    
    # Relationships
    payment = relationship("Payment", back_populates="transactions")
    balance = relationship("Balance", back_populates="transactions")
    
    # Indexes
    __table_args__ = (
        Index('idx_transactions_student_date', 'student_id', 'created_at'),
        Index('idx_transactions_type', 'transaction_type'),
        Index('idx_transactions_payment', 'payment_id'),
    )


class Invoice(Base):
    """
    Invoice model - generated invoices for payments
    """
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Invoice details
    student_id = Column(Integer, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    lessons_count = Column(Integer, nullable=False)
    price_per_lesson = Column(Numeric(8, 2), nullable=False)
    
    # Status and dates
    status = Column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    issue_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    paid_date = Column(DateTime, nullable=True)
    
    # References
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=True)
    
    # Invoice content
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    payment = relationship("Payment", foreign_keys=[payment_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_invoices_student', 'student_id'),
        Index('idx_invoices_status', 'status'),
    )