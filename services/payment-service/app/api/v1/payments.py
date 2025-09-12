# -*- coding: utf-8 -*-
"""
Payment Service API Endpoints
RESTful API for payment processing and balance management
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...services.payment_service import PaymentService
from ...services.balance_service import BalanceService
from ...schemas.payment import (
    PaymentCreate, PaymentUpdate, PaymentResponse,
    PaymentListResponse, QuickPaymentRequest,
    BalanceResponse, BalanceUpdate, BalanceAdjustmentRequest,
    TransactionResponse, TransactionListResponse,
    PaymentSummaryResponse, InvoiceCreate, InvoiceResponse,
    HealthResponse
)
from ...models.payment import PaymentStatus, PaymentType, TransactionType
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
payment_service = PaymentService()
balance_service = BalanceService()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Extended health check with database status"""
    try:
        # Test database connection
        await db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        database_status=db_status,
        event_handler_status="healthy"  # TODO: Add actual event handler status
    )


# Payment endpoints
@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new payment"""
    try:
        return await payment_service.create_payment(payment_data, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/payments/quick", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def quick_payment(request: QuickPaymentRequest):
    """Process quick payment with automatic calculations"""
    try:
        return await payment_service.quick_payment(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing quick payment: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int):
    """Get payment by ID"""
    payment = await payment_service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.put("/payments/{payment_id}", response_model=PaymentResponse)
async def update_payment(payment_id: int, payment_update: PaymentUpdate):
    """Update payment"""
    payment = await payment_service.update_payment(payment_id, payment_update)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.post("/payments/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(payment_id: int, reason: str = Query(..., description="Cancellation reason")):
    """Cancel payment and adjust balance"""
    try:
        payment = await payment_service.cancel_payment(payment_id, reason)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return payment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling payment: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/payments", response_model=PaymentListResponse)
async def get_payments(
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    payment_type: Optional[PaymentType] = Query(None, description="Filter by payment type"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page")
):
    """Get payments with filtering and pagination"""
    try:
        payments, total = await payment_service.get_payments(
            student_id=student_id,
            status=status,
            payment_type=payment_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=per_page
        )
        
        return PaymentListResponse(
            payments=payments,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page
        )
    except Exception as e:
        logger.error(f"Error getting payments: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/payments/student/{student_id}/summary", response_model=PaymentSummaryResponse)
async def get_payment_summary(student_id: int):
    """Get payment summary for student"""
    try:
        return await payment_service.get_payment_summary(student_id)
    except Exception as e:
        logger.error(f"Error getting payment summary: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/payments/student/{student_id}/monthly/{year}/{month}")
async def get_monthly_payments(student_id: int, year: int, month: int):
    """Get payments for specific month (compatibility endpoint)"""
    try:
        return await payment_service.get_monthly_payments(student_id, year, month)
    except Exception as e:
        logger.error(f"Error getting monthly payments: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# Balance endpoints
@router.get("/balances/{student_id}", response_model=BalanceResponse)
async def get_balance(student_id: int):
    """Get student balance"""
    try:
        balance = await balance_service.get_balance(student_id)
        if not balance:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Balance not found")
        return balance
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/balances/{student_id}/simple")
async def get_balance_simple(student_id: int):
    """Get simple balance (compatibility endpoint)"""
    try:
        balance = await balance_service.get_balance_simple(student_id)
        return {"balance": balance}
    except Exception as e:
        logger.error(f"Error getting simple balance: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/balances/add", response_model=BalanceResponse)
async def add_lessons_to_balance(request: BalanceUpdate):
    """Add lessons to balance (manual operation)"""
    if request.lessons_count <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lessons count must be positive")
    
    try:
        return await balance_service.add_lessons(
            student_id=request.student_id,
            lessons_count=request.lessons_count,
            amount=request.amount or 0,
            description=request.description,
            reference_id=request.reference_id,
            created_by_user_id=request.created_by_user_id
        )
    except Exception as e:
        logger.error(f"Error adding lessons to balance: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/balances/deduct", response_model=BalanceResponse)
async def deduct_lessons_from_balance(request: BalanceUpdate):
    """Deduct lessons from balance (manual operation)"""
    if request.lessons_count <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lessons count must be positive")
    
    try:
        return await balance_service.deduct_lessons(
            student_id=request.student_id,
            lessons_count=request.lessons_count,
            amount=request.amount or 0,
            description=request.description,
            lesson_id=request.lesson_id,
            reference_id=request.reference_id,
            created_by_user_id=request.created_by_user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error deducting lessons from balance: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/balances/{student_id}/adjust", response_model=BalanceResponse)
async def adjust_balance(student_id: int, request: BalanceAdjustmentRequest):
    """Manual balance adjustment (admin function)"""
    try:
        return await balance_service.adjust_balance(
            student_id=student_id,
            lessons_adjustment=request.lessons_adjustment,
            reason=request.reason,
            authorized_by=request.authorized_by
        )
    except Exception as e:
        logger.error(f"Error adjusting balance: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/balances/{student_id}/recalculate", response_model=BalanceResponse)
async def recalculate_balance(student_id: int):
    """Recalculate balance from transactions (maintenance function)"""
    try:
        return await balance_service.calculate_balance_from_scratch(student_id)
    except Exception as e:
        logger.error(f"Error recalculating balance: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# Transaction endpoints
@router.get("/transactions/{student_id}", response_model=TransactionListResponse)
async def get_transactions(
    student_id: int,
    transaction_type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page")
):
    """Get transactions for student"""
    try:
        transactions, total = await balance_service.get_transactions(
            student_id=student_id,
            transaction_type=transaction_type,
            page=page,
            per_page=per_page
        )
        
        return TransactionListResponse(
            transactions=transactions,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page
        )
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# Invoice endpoints
@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(invoice_data: InvoiceCreate):
    """Create invoice"""
    try:
        return await payment_service.create_invoice(invoice_data)
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# Admin endpoints
@router.post("/admin/sync-balances")
async def sync_all_balances():
    """Sync all student balances (admin function)"""
    try:
        synced_count = await balance_service.sync_all_balances()
        return {"message": f"Synced {synced_count} student balances"}
    except Exception as e:
        logger.error(f"Error syncing balances: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")