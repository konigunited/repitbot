# -*- coding: utf-8 -*-
"""
Payment Service Business Logic
Core payment processing and management functionality
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.orm import selectinload

from ..models.payment import (
    Payment, PaymentStatus, PaymentType, 
    TransactionType, Transaction, Invoice
)
from ..schemas.payment import (
    PaymentCreate, PaymentUpdate, PaymentResponse,
    QuickPaymentRequest, PaymentSummaryResponse,
    InvoiceCreate, InvoiceResponse
)
from ..database.connection import db_manager
from ..core.config import settings
from .balance_service import BalanceService
from ..clients.user_client import UserServiceClient, MockUserServiceClient
from ..clients.lesson_client import LessonServiceClient, MockLessonServiceClient

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for payment processing and management"""
    
    def __init__(self):
        self.balance_service = BalanceService()
        
        # Initialize service clients (use mock in development/testing)
        if settings.DEBUG:
            self.user_client = MockUserServiceClient()
            self.lesson_client = MockLessonServiceClient()
        else:
            self.user_client = UserServiceClient()
            self.lesson_client = LessonServiceClient()
    
    async def create_payment(
        self,
        payment_data: PaymentCreate,
        session: Optional[AsyncSession] = None
    ) -> PaymentResponse:
        """Create new payment and update balance"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Validate payment data
            await self._validate_payment_data(payment_data, session)
            
            # Create payment record
            payment = Payment(
                student_id=payment_data.student_id,
                amount=payment_data.amount,
                lessons_paid=payment_data.lessons_paid,
                price_per_lesson=payment_data.price_per_lesson,
                payment_type=payment_data.payment_type,
                payment_method=payment_data.payment_method,
                description=payment_data.description,
                notes=payment_data.notes,
                status=PaymentStatus.COMPLETED,  # Auto-complete for now
                payment_date=datetime.utcnow(),
                processed_at=datetime.utcnow()
            )
            
            session.add(payment)
            await session.flush()  # Get ID
            
            # Update student balance
            await self.balance_service.add_lessons(
                student_id=payment_data.student_id,
                lessons_count=payment_data.lessons_paid,
                amount=payment_data.amount,
                description=f"Payment #{payment.id}: {payment_data.lessons_paid} lessons",
                payment_id=payment.id,
                session=session
            )
            
            await session.commit()
            logger.info(f"Payment created: {payment.id} for student {payment_data.student_id}")
            
            return PaymentResponse.model_validate(payment)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating payment: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def get_payment(self, payment_id: int) -> Optional[PaymentResponse]:
        """Get payment by ID"""
        async with db_manager.session_maker() as session:
            result = await session.execute(
                select(Payment).where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()
            return PaymentResponse.model_validate(payment) if payment else None
    
    async def get_payments(
        self,
        student_id: Optional[int] = None,
        status: Optional[PaymentStatus] = None,
        payment_type: Optional[PaymentType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[PaymentResponse], int]:
        """Get payments with filtering and pagination"""
        async with db_manager.session_maker() as session:
            # Build query
            query = select(Payment)
            
            if student_id:
                query = query.where(Payment.student_id == student_id)
            if status:
                query = query.where(Payment.status == status)
            if payment_type:
                query = query.where(Payment.payment_type == payment_type)
            if start_date:
                query = query.where(Payment.payment_date >= start_date)
            if end_date:
                query = query.where(Payment.payment_date <= end_date)
            
            # Get total count
            count_result = await session.execute(
                select(func.count()).select_from(query.subquery())
            )
            total = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(desc(Payment.payment_date))
            query = query.offset((page - 1) * per_page).limit(per_page)
            
            # Execute query
            result = await session.execute(query)
            payments = result.scalars().all()
            
            return [PaymentResponse.model_validate(p) for p in payments], total
    
    async def update_payment(
        self,
        payment_id: int,
        payment_update: PaymentUpdate
    ) -> Optional[PaymentResponse]:
        """Update payment"""
        async with db_manager.session_maker() as session:
            result = await session.execute(
                select(Payment).where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()
            
            if not payment:
                return None
            
            # Update fields
            for field, value in payment_update.model_dump(exclude_unset=True).items():
                setattr(payment, field, value)
            
            payment.updated_at = datetime.utcnow()
            
            # Mark as processed if status changed to completed
            if payment_update.status == PaymentStatus.COMPLETED and not payment.processed_at:
                payment.processed_at = datetime.utcnow()
            
            await session.commit()
            return PaymentResponse.model_validate(payment)
    
    async def quick_payment(
        self,
        request: QuickPaymentRequest
    ) -> PaymentResponse:
        """Process quick payment with automatic price calculation"""
        price_per_lesson = request.price_per_lesson or settings.DEFAULT_PRICE_PER_LESSON
        total_amount = price_per_lesson * request.lessons_count
        
        payment_data = PaymentCreate(
            student_id=request.student_id,
            lessons_paid=request.lessons_count,
            amount=total_amount,
            price_per_lesson=price_per_lesson,
            payment_method=request.payment_method,
            description=request.description or f"Quick payment: {request.lessons_count} lessons"
        )
        
        return await self.create_payment(payment_data)
    
    async def get_payment_summary(self, student_id: int) -> PaymentSummaryResponse:
        """Get payment summary for student"""
        async with db_manager.session_maker() as session:
            # Get payment statistics
            result = await session.execute(
                select(
                    func.count(Payment.id).label('total_payments'),
                    func.sum(Payment.amount).label('total_amount_paid'),
                    func.sum(Payment.lessons_paid).label('total_lessons_paid'),
                    func.avg(Payment.price_per_lesson).label('avg_price_per_lesson'),
                    func.max(Payment.payment_date).label('last_payment_date'),
                    func.min(Payment.payment_date).label('first_payment_date')
                ).where(
                    and_(
                        Payment.student_id == student_id,
                        Payment.status == PaymentStatus.COMPLETED
                    )
                )
            )
            
            stats = result.first()
            
            # Get current balance
            balance = await self.balance_service.get_balance(student_id)
            current_balance = balance.current_balance if balance else 0
            
            return PaymentSummaryResponse(
                student_id=student_id,
                total_payments=stats.total_payments or 0,
                total_amount_paid=stats.total_amount_paid or Decimal('0.00'),
                total_lessons_paid=stats.total_lessons_paid or 0,
                current_balance=current_balance,
                average_price_per_lesson=stats.avg_price_per_lesson or Decimal('0.00'),
                last_payment_date=stats.last_payment_date,
                first_payment_date=stats.first_payment_date
            )
    
    async def get_monthly_payments(
        self,
        student_id: int,
        year: int,
        month: int
    ) -> List[PaymentResponse]:
        """Get payments for specific month (for compatibility)"""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        payments, _ = await self.get_payments(
            student_id=student_id,
            start_date=start_date,
            end_date=end_date,
            per_page=1000  # Get all for the month
        )
        
        return payments
    
    async def create_invoice(
        self,
        invoice_data: InvoiceCreate
    ) -> InvoiceResponse:
        """Create invoice for payment"""
        async with db_manager.session_maker() as session:
            # Generate invoice number
            invoice_number = await self._generate_invoice_number(session)
            
            invoice = Invoice(
                invoice_number=invoice_number,
                student_id=invoice_data.student_id,
                amount=invoice_data.amount,
                lessons_count=invoice_data.lessons_count,
                price_per_lesson=invoice_data.price_per_lesson,
                description=invoice_data.description,
                notes=invoice_data.notes,
                due_date=invoice_data.due_date,
                status=PaymentStatus.PENDING
            )
            
            session.add(invoice)
            await session.commit()
            
            logger.info(f"Invoice created: {invoice.invoice_number} for student {invoice_data.student_id}")
            return InvoiceResponse.model_validate(invoice)
    
    async def _validate_payment_data(
        self,
        payment_data: PaymentCreate,
        session: AsyncSession
    ) -> None:
        """Validate payment data"""
        if payment_data.lessons_paid <= 0:
            raise ValueError("Lessons count must be positive")
        
        if payment_data.amount <= 0:
            raise ValueError("Payment amount must be positive")
        
        if payment_data.price_per_lesson <= 0:
            raise ValueError("Price per lesson must be positive")
        
        # Check if calculated amount matches
        expected_amount = payment_data.price_per_lesson * payment_data.lessons_paid
        if abs(payment_data.amount - expected_amount) > Decimal('0.01'):
            raise ValueError(f"Amount mismatch: expected {expected_amount}, got {payment_data.amount}")
        
        # Validate student exists
        student = await self.user_client.get_student(payment_data.student_id)
        if not student:
            raise ValueError(f"Student {payment_data.student_id} not found")
        
        if not student.get("is_active", True):
            raise ValueError(f"Student {payment_data.student_id} is not active")
        
        # Check student balance limits
        balance = await self.balance_service.get_balance(payment_data.student_id, session)
        if balance:
            new_balance = balance.current_balance + payment_data.lessons_paid
            if new_balance > settings.MAX_BALANCE:
                raise ValueError(f"Balance limit exceeded: max {settings.MAX_BALANCE} lessons")
    
    async def _generate_invoice_number(self, session: AsyncSession) -> str:
        """Generate unique invoice number"""
        today = datetime.now().strftime("%Y%m%d")
        
        # Get last invoice number for today
        result = await session.execute(
            select(func.count(Invoice.id)).where(
                Invoice.invoice_number.like(f"{settings.INVOICE_NUMBER_PREFIX}{today}%")
            )
        )
        
        count = result.scalar() + 1
        return f"{settings.INVOICE_NUMBER_PREFIX}{today}{count:04d}"
    
    async def cancel_payment(self, payment_id: int, reason: str) -> Optional[PaymentResponse]:
        """Cancel payment and adjust balance"""
        async with db_manager.session_maker() as session:
            try:
                result = await session.execute(
                    select(Payment).where(Payment.id == payment_id)
                )
                payment = result.scalar_one_or_none()
                
                if not payment:
                    return None
                
                if payment.status == PaymentStatus.CANCELLED:
                    raise ValueError("Payment already cancelled")
                
                if payment.status == PaymentStatus.REFUNDED:
                    raise ValueError("Payment already refunded")
                
                # Update payment status
                payment.status = PaymentStatus.CANCELLED
                payment.notes = f"{payment.notes or ''}\nCancelled: {reason}".strip()
                payment.updated_at = datetime.utcnow()
                
                # Reverse balance changes
                await self.balance_service.deduct_lessons(
                    student_id=payment.student_id,
                    lessons_count=payment.lessons_paid,
                    amount=payment.amount,
                    description=f"Payment cancellation #{payment.id}: {reason}",
                    payment_id=payment.id,
                    session=session
                )
                
                await session.commit()
                logger.info(f"Payment cancelled: {payment.id}, reason: {reason}")
                
                return PaymentResponse.model_validate(payment)
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error cancelling payment: {e}")
                raise
    
    async def validate_payment_access(
        self,
        payment_id: int,
        user_id: int
    ) -> bool:
        """Validate if user has access to payment (student/parent/tutor)"""
        try:
            # Get payment
            payment = await self.get_payment(payment_id)
            if not payment:
                return False
            
            # Check access through student
            return await self.user_client.validate_student_access(
                payment.student_id, user_id
            )
            
        except Exception as e:
            logger.error(f"Error validating payment access: {e}")
            return False
    
    async def get_enriched_payments(
        self,
        student_id: Optional[int] = None,
        user_id: Optional[int] = None,
        **kwargs
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get payments enriched with student/user information"""
        try:
            # Get payments
            payments, total = await self.get_payments(student_id=student_id, **kwargs)
            
            # If user_id provided, filter by access
            if user_id and not student_id:
                # Get students accessible to user
                accessible_students = await self.user_client.get_students_by_parent(user_id)
                if not accessible_students:
                    accessible_students = await self.user_client.get_students_by_tutor(user_id)
                
                accessible_student_ids = [s['id'] for s in accessible_students]
                payments = [p for p in payments if p.student_id in accessible_student_ids]
            
            # Enrich with student data
            enriched_payments = []
            for payment in payments:
                payment_dict = payment.model_dump()
                
                # Add student information
                student = await self.user_client.get_student(payment.student_id)
                if student:
                    payment_dict['student'] = {
                        'id': student['id'],
                        'name': student.get('name', 'Unknown'),
                        'grade': student.get('grade')
                    }
                
                enriched_payments.append(payment_dict)
            
            return enriched_payments, total
            
        except Exception as e:
            logger.error(f"Error getting enriched payments: {e}")
            return [], 0
    
    async def recalculate_student_balance(self, student_id: int) -> Dict[str, Any]:
        """Recalculate and sync student balance with lesson data"""
        try:
            # Get all completed lessons for student
            completed_lessons = await self.lesson_client.get_completed_lessons(student_id)
            
            # Get all payments for student
            payments, _ = await self.get_payments(
                student_id=student_id,
                status=PaymentStatus.COMPLETED,
                per_page=1000
            )
            
            # Calculate expected vs actual balance
            total_lessons_paid = sum(p.lessons_paid for p in payments)
            total_lessons_used = len(completed_lessons)
            expected_balance = total_lessons_paid - total_lessons_used
            
            # Get current balance
            current_balance_record = await self.balance_service.get_balance(student_id)
            current_balance = current_balance_record.current_balance if current_balance_record else 0
            
            # Check for discrepancy
            discrepancy = current_balance - expected_balance
            
            result = {
                "student_id": student_id,
                "total_lessons_paid": total_lessons_paid,
                "total_lessons_used": total_lessons_used,
                "expected_balance": expected_balance,
                "current_balance": current_balance,
                "discrepancy": discrepancy,
                "needs_adjustment": abs(discrepancy) > 0
            }
            
            # Auto-correct if discrepancy found
            if abs(discrepancy) > 0:
                logger.warning(f"Balance discrepancy for student {student_id}: {discrepancy}")
                
                # Adjust balance
                if discrepancy > 0:
                    # Current balance too high, deduct
                    await self.balance_service.deduct_lessons(
                        student_id=student_id,
                        lessons_count=abs(discrepancy),
                        amount=Decimal('0.00'),
                        description="Balance correction - overstated balance",
                        reference_id=f"correction_{student_id}_{datetime.utcnow().timestamp()}"
                    )
                else:
                    # Current balance too low, add
                    await self.balance_service.add_lessons(
                        student_id=student_id,
                        lessons_count=abs(discrepancy),
                        amount=Decimal('0.00'),
                        description="Balance correction - understated balance",
                        reference_id=f"correction_{student_id}_{datetime.utcnow().timestamp()}"
                    )
                
                result["adjustment_applied"] = True
                result["corrected_balance"] = expected_balance
            
            # Update cache in User Service
            await self.user_client.update_student_balance_cache(
                student_id, expected_balance
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error recalculating balance for student {student_id}: {e}")
            raise
    
    async def get_payment_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get payment analytics across all students"""
        try:
            # Get payments in date range
            payments, total = await self.get_payments(
                start_date=start_date,
                end_date=end_date,
                per_page=10000  # Get all for analytics
            )
            
            if not payments:
                return {
                    "total_payments": 0,
                    "total_amount": 0,
                    "total_lessons": 0,
                    "average_payment": 0,
                    "payments_by_method": {},
                    "top_students": []
                }
            
            # Calculate analytics
            total_amount = sum(p.amount for p in payments)
            total_lessons = sum(p.lessons_paid for p in payments)
            average_payment = total_amount / len(payments) if payments else 0
            
            # Group by payment method
            payments_by_method = {}
            for payment in payments:
                method = payment.payment_method or "unknown"
                if method not in payments_by_method:
                    payments_by_method[method] = {"count": 0, "amount": Decimal('0.00')}
                payments_by_method[method]["count"] += 1
                payments_by_method[method]["amount"] += payment.amount
            
            # Top students by payment volume
            student_payments = {}
            for payment in payments:
                student_id = payment.student_id
                if student_id not in student_payments:
                    student_payments[student_id] = {"count": 0, "amount": Decimal('0.00')}
                student_payments[student_id]["count"] += 1
                student_payments[student_id]["amount"] += payment.amount
            
            # Sort and get top 10
            top_students_data = sorted(
                student_payments.items(),
                key=lambda x: x[1]["amount"],
                reverse=True
            )[:10]
            
            # Enrich with student names
            top_students = []
            for student_id, data in top_students_data:
                student = await self.user_client.get_student(student_id)
                top_students.append({
                    "student_id": student_id,
                    "student_name": student.get('name', 'Unknown') if student else 'Unknown',
                    "payment_count": data["count"],
                    "total_amount": float(data["amount"])
                })
            
            return {
                "total_payments": len(payments),
                "total_amount": float(total_amount),
                "total_lessons": total_lessons,
                "average_payment": float(average_payment),
                "payments_by_method": {
                    method: {
                        "count": data["count"],
                        "amount": float(data["amount"])
                    } for method, data in payments_by_method.items()
                },
                "top_students": top_students
            }
            
        except Exception as e:
            logger.error(f"Error getting payment analytics: {e}")
            raise
    
    async def close_clients(self):
        """Close HTTP clients"""
        if hasattr(self.user_client, 'close'):
            await self.user_client.close()
        if hasattr(self.lesson_client, 'close'):
            await self.lesson_client.close()