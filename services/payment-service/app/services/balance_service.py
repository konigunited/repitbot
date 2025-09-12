# -*- coding: utf-8 -*-
"""
Balance Service Business Logic
Student balance calculation and management functionality
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from ..models.payment import (
    Balance, Transaction, TransactionType,
    Payment, PaymentStatus
)
from ..schemas.payment import (
    BalanceResponse, BalanceUpdate, TransactionResponse
)
from ..database.connection import db_manager
from ..core.config import settings

logger = logging.getLogger(__name__)


class BalanceService:
    """Service for balance management and calculation"""
    
    async def get_balance(
        self,
        student_id: int,
        session: Optional[AsyncSession] = None
    ) -> Optional[BalanceResponse]:
        """Get student balance, create if doesn't exist"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            result = await session.execute(
                select(Balance).where(Balance.student_id == student_id)
            )
            balance = result.scalar_one_or_none()
            
            if not balance:
                # Create new balance record
                balance = await self._create_balance(student_id, session)
            
            return BalanceResponse.model_validate(balance)
            
        finally:
            if should_close:
                await session.close()
    
    async def add_lessons(
        self,
        student_id: int,
        lessons_count: int,
        amount: Decimal,
        description: str,
        payment_id: Optional[int] = None,
        reference_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> BalanceResponse:
        """Add lessons to student balance"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Get or create balance
            balance = await self._get_or_create_balance(student_id, session)
            balance_before = balance.current_balance
            
            # Update balance
            balance.current_balance += lessons_count
            balance.total_lessons_paid += lessons_count
            balance.total_amount_paid += amount
            balance.last_payment_date = datetime.utcnow()
            balance.updated_at = datetime.utcnow()
            
            # Create transaction record
            transaction = Transaction(
                student_id=student_id,
                transaction_type=TransactionType.DEBIT,
                amount=amount,
                lessons_count=lessons_count,
                balance_before=balance_before,
                balance_after=balance.current_balance,
                payment_id=payment_id,
                balance_id=balance.id,
                description=description,
                reference_id=reference_id,
                created_by_user_id=created_by_user_id
            )
            
            session.add(transaction)
            await session.flush()
            
            logger.info(f"Added {lessons_count} lessons to student {student_id}, new balance: {balance.current_balance}")
            
            return BalanceResponse.model_validate(balance)
            
        except Exception as e:
            logger.error(f"Error adding lessons to balance: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def deduct_lessons(
        self,
        student_id: int,
        lessons_count: int,
        amount: Decimal,
        description: str,
        lesson_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        reference_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> BalanceResponse:
        """Deduct lessons from student balance"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Get or create balance
            balance = await self._get_or_create_balance(student_id, session)
            balance_before = balance.current_balance
            
            # Check if sufficient balance
            if not settings.ENABLE_NEGATIVE_BALANCE and balance.current_balance < lessons_count:
                raise ValueError(f"Insufficient balance: {balance.current_balance} < {lessons_count}")
            
            # Update balance
            balance.current_balance -= lessons_count
            balance.lessons_consumed += lessons_count
            balance.total_amount_spent += amount
            balance.last_lesson_date = datetime.utcnow()
            balance.updated_at = datetime.utcnow()
            
            # Create transaction record
            transaction = Transaction(
                student_id=student_id,
                transaction_type=TransactionType.CREDIT,
                amount=amount,
                lessons_count=lessons_count,
                balance_before=balance_before,
                balance_after=balance.current_balance,
                payment_id=payment_id,
                balance_id=balance.id,
                lesson_id=lesson_id,
                description=description,
                reference_id=reference_id,
                created_by_user_id=created_by_user_id
            )
            
            session.add(transaction)
            await session.flush()
            
            logger.info(f"Deducted {lessons_count} lessons from student {student_id}, new balance: {balance.current_balance}")
            
            return BalanceResponse.model_validate(balance)
            
        except Exception as e:
            logger.error(f"Error deducting lessons from balance: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def calculate_balance_from_scratch(
        self,
        student_id: int,
        session: Optional[AsyncSession] = None
    ) -> BalanceResponse:
        """Recalculate balance from all transactions (for data integrity)"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Get all transactions for student
            result = await session.execute(
                select(Transaction)
                .where(Transaction.student_id == student_id)
                .order_by(Transaction.created_at)
            )
            transactions = result.scalars().all()
            
            # Calculate totals
            total_lessons_paid = 0
            lessons_consumed = 0
            total_amount_paid = Decimal('0.00')
            total_amount_spent = Decimal('0.00')
            last_payment_date = None
            last_lesson_date = None
            
            for transaction in transactions:
                if transaction.transaction_type == TransactionType.DEBIT:
                    total_lessons_paid += transaction.lessons_count
                    total_amount_paid += transaction.amount
                    if transaction.payment_id:  # Only update if it's a payment transaction
                        last_payment_date = transaction.created_at
                else:  # CREDIT
                    lessons_consumed += transaction.lessons_count
                    total_amount_spent += transaction.amount
                    if transaction.lesson_id:  # Only update if it's a lesson transaction
                        last_lesson_date = transaction.created_at
            
            current_balance = total_lessons_paid - lessons_consumed
            
            # Update or create balance record
            balance = await self._get_or_create_balance(student_id, session)
            balance.total_lessons_paid = total_lessons_paid
            balance.lessons_consumed = lessons_consumed
            balance.current_balance = current_balance
            balance.total_amount_paid = total_amount_paid
            balance.total_amount_spent = total_amount_spent
            balance.last_payment_date = last_payment_date
            balance.last_lesson_date = last_lesson_date
            balance.updated_at = datetime.utcnow()
            
            await session.flush()
            
            logger.info(f"Recalculated balance for student {student_id}: {current_balance}")
            
            return BalanceResponse.model_validate(balance)
            
        except Exception as e:
            logger.error(f"Error recalculating balance: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def get_balance_simple(self, student_id: int) -> int:
        """Get simple balance calculation (for compatibility with existing code)"""
        balance = await self.get_balance(student_id)
        return balance.current_balance if balance else 0
    
    async def adjust_balance(
        self,
        student_id: int,
        lessons_adjustment: int,
        reason: str,
        authorized_by: int,
        session: Optional[AsyncSession] = None
    ) -> BalanceResponse:
        """Manual balance adjustment (admin function)"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            if lessons_adjustment > 0:
                return await self.add_lessons(
                    student_id=student_id,
                    lessons_count=lessons_adjustment,
                    amount=Decimal('0.00'),  # No money involved in adjustments
                    description=f"Manual adjustment: {reason}",
                    created_by_user_id=authorized_by,
                    session=session
                )
            else:
                return await self.deduct_lessons(
                    student_id=student_id,
                    lessons_count=abs(lessons_adjustment),
                    amount=Decimal('0.00'),  # No money involved in adjustments
                    description=f"Manual adjustment: {reason}",
                    created_by_user_id=authorized_by,
                    session=session
                )
        finally:
            if should_close:
                await session.close()
    
    async def get_transactions(
        self,
        student_id: int,
        transaction_type: Optional[TransactionType] = None,
        page: int = 1,
        per_page: int = 20,
        session: Optional[AsyncSession] = None
    ) -> tuple[list[TransactionResponse], int]:
        """Get transactions for student with pagination"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Build query
            query = select(Transaction).where(Transaction.student_id == student_id)
            
            if transaction_type:
                query = query.where(Transaction.transaction_type == transaction_type)
            
            # Get total count
            count_result = await session.execute(
                select(func.count()).select_from(query.subquery())
            )
            total = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(Transaction.created_at.desc())
            query = query.offset((page - 1) * per_page).limit(per_page)
            
            # Execute query
            result = await session.execute(query)
            transactions = result.scalars().all()
            
            return [TransactionResponse.model_validate(t) for t in transactions], total
            
        finally:
            if should_close:
                await session.close()
    
    async def _get_or_create_balance(
        self,
        student_id: int,
        session: AsyncSession
    ) -> Balance:
        """Get existing balance or create new one"""
        result = await session.execute(
            select(Balance).where(Balance.student_id == student_id)
        )
        balance = result.scalar_one_or_none()
        
        if not balance:
            balance = await self._create_balance(student_id, session)
        
        return balance
    
    async def _create_balance(
        self,
        student_id: int,
        session: AsyncSession
    ) -> Balance:
        """Create new balance record"""
        balance = Balance(
            student_id=student_id,
            total_lessons_paid=0,
            lessons_consumed=0,
            current_balance=0,
            total_amount_paid=Decimal('0.00'),
            total_amount_spent=Decimal('0.00')
        )
        
        session.add(balance)
        await session.flush()
        
        logger.info(f"Created new balance record for student {student_id}")
        return balance
    
    async def sync_all_balances(self) -> int:
        """Sync all student balances (maintenance function)"""
        async with db_manager.session_maker() as session:
            # Get all unique student IDs from transactions
            result = await session.execute(
                select(Transaction.student_id).distinct()
            )
            student_ids = [row[0] for row in result.fetchall()]
            
            synced_count = 0
            for student_id in student_ids:
                try:
                    await self.calculate_balance_from_scratch(student_id, session)
                    synced_count += 1
                except Exception as e:
                    logger.error(f"Error syncing balance for student {student_id}: {e}")
            
            await session.commit()
            logger.info(f"Synced {synced_count} student balances")
            return synced_count