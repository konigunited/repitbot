# -*- coding: utf-8 -*-
"""
Payment Service HTTP Client
Client for interacting with Payment microservice
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .api_client import APIClient

logger = logging.getLogger(__name__)


@dataclass
class PaymentInfo:
    """Payment information data class"""
    id: int
    student_id: int
    lessons_paid: int
    amount: float
    price_per_lesson: float
    payment_date: datetime
    status: str
    payment_method: Optional[str] = None
    description: Optional[str] = None


@dataclass
class BalanceInfo:
    """Balance information data class"""
    student_id: int
    current_balance: int
    total_lessons_paid: int
    lessons_consumed: int
    total_amount_paid: float
    total_amount_spent: float
    last_payment_date: Optional[datetime] = None
    last_lesson_date: Optional[datetime] = None


@dataclass
class TransactionInfo:
    """Transaction information data class"""
    id: int
    student_id: int
    transaction_type: str
    amount: float
    lessons_count: int
    balance_before: int
    balance_after: int
    description: str
    created_at: datetime
    payment_id: Optional[int] = None
    lesson_id: Optional[int] = None


class PaymentServiceClient(APIClient):
    """Client for Payment Service API"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        super().__init__(base_url)
        self.service_name = "payment-service"
    
    async def create_payment(
        self,
        student_id: int,
        lessons_count: int,
        price_per_lesson: float,
        payment_method: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[PaymentInfo]:
        """Create new payment"""
        try:
            amount = Decimal(str(price_per_lesson)) * lessons_count
            
            payload = {
                "student_id": student_id,
                "lessons_paid": lessons_count,
                "amount": float(amount),
                "price_per_lesson": price_per_lesson,
                "payment_method": payment_method,
                "description": description or f"Payment for {lessons_count} lessons"
            }
            
            response = await self._post("/api/v1/payments", json=payload)
            
            if response:
                return PaymentInfo(
                    id=response["id"],
                    student_id=response["student_id"],
                    lessons_paid=response["lessons_paid"],
                    amount=response["amount"],
                    price_per_lesson=response["price_per_lesson"],
                    payment_date=datetime.fromisoformat(response["payment_date"].replace('Z', '+00:00')),
                    status=response["status"],
                    payment_method=response.get("payment_method"),
                    description=response.get("description")
                )
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return None
    
    async def quick_payment(
        self,
        student_id: int,
        lessons_count: int,
        price_per_lesson: Optional[float] = None,
        payment_method: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[PaymentInfo]:
        """Process quick payment with automatic calculations"""
        try:
            payload = {
                "student_id": student_id,
                "lessons_count": lessons_count,
                "payment_method": payment_method,
                "description": description
            }
            
            if price_per_lesson:
                payload["price_per_lesson"] = price_per_lesson
            
            response = await self._post("/api/v1/payments/quick", json=payload)
            
            if response:
                return PaymentInfo(
                    id=response["id"],
                    student_id=response["student_id"],
                    lessons_paid=response["lessons_paid"],
                    amount=response["amount"],
                    price_per_lesson=response["price_per_lesson"],
                    payment_date=datetime.fromisoformat(response["payment_date"].replace('Z', '+00:00')),
                    status=response["status"],
                    payment_method=response.get("payment_method"),
                    description=response.get("description")
                )
        except Exception as e:
            logger.error(f"Error processing quick payment: {e}")
            return None
    
    async def get_payment(self, payment_id: int) -> Optional[PaymentInfo]:
        """Get payment by ID"""
        try:
            response = await self._get(f"/api/v1/payments/{payment_id}")
            
            if response:
                return PaymentInfo(
                    id=response["id"],
                    student_id=response["student_id"],
                    lessons_paid=response["lessons_paid"],
                    amount=response["amount"],
                    price_per_lesson=response["price_per_lesson"],
                    payment_date=datetime.fromisoformat(response["payment_date"].replace('Z', '+00:00')),
                    status=response["status"],
                    payment_method=response.get("payment_method"),
                    description=response.get("description")
                )
        except Exception as e:
            logger.error(f"Error getting payment {payment_id}: {e}")
            return None
    
    async def get_student_payments(
        self,
        student_id: int,
        page: int = 1,
        per_page: int = 20
    ) -> List[PaymentInfo]:
        """Get payments for student"""
        try:
            response = await self._get(
                "/api/v1/payments",
                params={
                    "student_id": student_id,
                    "page": page,
                    "per_page": per_page
                }
            )
            
            if response and "payments" in response:
                payments = []
                for payment_data in response["payments"]:
                    payments.append(PaymentInfo(
                        id=payment_data["id"],
                        student_id=payment_data["student_id"],
                        lessons_paid=payment_data["lessons_paid"],
                        amount=payment_data["amount"],
                        price_per_lesson=payment_data["price_per_lesson"],
                        payment_date=datetime.fromisoformat(payment_data["payment_date"].replace('Z', '+00:00')),
                        status=payment_data["status"],
                        payment_method=payment_data.get("payment_method"),
                        description=payment_data.get("description")
                    ))
                return payments
            return []
        except Exception as e:
            logger.error(f"Error getting student payments: {e}")
            return []
    
    async def get_monthly_payments(
        self,
        student_id: int,
        year: int,
        month: int
    ) -> List[PaymentInfo]:
        """Get payments for specific month (compatibility method)"""
        try:
            response = await self._get(f"/api/v1/payments/student/{student_id}/monthly/{year}/{month}")
            
            if response:
                payments = []
                for payment_data in response:
                    payments.append(PaymentInfo(
                        id=payment_data["id"],
                        student_id=payment_data["student_id"],
                        lessons_paid=payment_data["lessons_paid"],
                        amount=payment_data["amount"],
                        price_per_lesson=payment_data["price_per_lesson"],
                        payment_date=datetime.fromisoformat(payment_data["payment_date"].replace('Z', '+00:00')),
                        status=payment_data["status"],
                        payment_method=payment_data.get("payment_method"),
                        description=payment_data.get("description")
                    ))
                return payments
            return []
        except Exception as e:
            logger.error(f"Error getting monthly payments: {e}")
            return []
    
    async def get_student_balance(self, student_id: int) -> Optional[BalanceInfo]:
        """Get student balance"""
        try:
            response = await self._get(f"/api/v1/balances/{student_id}")
            
            if response:
                return BalanceInfo(
                    student_id=response["student_id"],
                    current_balance=response["current_balance"],
                    total_lessons_paid=response["total_lessons_paid"],
                    lessons_consumed=response["lessons_consumed"],
                    total_amount_paid=response["total_amount_paid"],
                    total_amount_spent=response["total_amount_spent"],
                    last_payment_date=datetime.fromisoformat(response["last_payment_date"].replace('Z', '+00:00')) if response.get("last_payment_date") else None,
                    last_lesson_date=datetime.fromisoformat(response["last_lesson_date"].replace('Z', '+00:00')) if response.get("last_lesson_date") else None
                )
        except Exception as e:
            logger.error(f"Error getting student balance: {e}")
            return None
    
    async def get_simple_balance(self, student_id: int) -> int:
        """Get simple balance (compatibility method)"""
        try:
            response = await self._get(f"/api/v1/balances/{student_id}/simple")
            
            if response and "balance" in response:
                return response["balance"]
            return 0
        except Exception as e:
            logger.error(f"Error getting simple balance: {e}")
            return 0
    
    async def deduct_lesson_from_balance(
        self,
        student_id: int,
        lesson_id: int,
        amount: float = 0.0,
        description: str = "Lesson completed"
    ) -> Optional[BalanceInfo]:
        """Deduct lesson from balance"""
        try:
            payload = {
                "student_id": student_id,
                "lessons_count": 1,
                "amount": amount,
                "description": description,
                "lesson_id": lesson_id
            }
            
            response = await self._post("/api/v1/balances/deduct", json=payload)
            
            if response:
                return BalanceInfo(
                    student_id=response["student_id"],
                    current_balance=response["current_balance"],
                    total_lessons_paid=response["total_lessons_paid"],
                    lessons_consumed=response["lessons_consumed"],
                    total_amount_paid=response["total_amount_paid"],
                    total_amount_spent=response["total_amount_spent"],
                    last_payment_date=datetime.fromisoformat(response["last_payment_date"].replace('Z', '+00:00')) if response.get("last_payment_date") else None,
                    last_lesson_date=datetime.fromisoformat(response["last_lesson_date"].replace('Z', '+00:00')) if response.get("last_lesson_date") else None
                )
        except Exception as e:
            logger.error(f"Error deducting lesson from balance: {e}")
            return None
    
    async def add_lessons_to_balance(
        self,
        student_id: int,
        lessons_count: int,
        amount: float = 0.0,
        description: str = "Manual balance adjustment"
    ) -> Optional[BalanceInfo]:
        """Add lessons to balance (for refunds, adjustments)"""
        try:
            payload = {
                "student_id": student_id,
                "lessons_count": lessons_count,
                "amount": amount,
                "description": description
            }
            
            response = await self._post("/api/v1/balances/add", json=payload)
            
            if response:
                return BalanceInfo(
                    student_id=response["student_id"],
                    current_balance=response["current_balance"],
                    total_lessons_paid=response["total_lessons_paid"],
                    lessons_consumed=response["lessons_consumed"],
                    total_amount_paid=response["total_amount_paid"],
                    total_amount_spent=response["total_amount_spent"],
                    last_payment_date=datetime.fromisoformat(response["last_payment_date"].replace('Z', '+00:00')) if response.get("last_payment_date") else None,
                    last_lesson_date=datetime.fromisoformat(response["last_lesson_date"].replace('Z', '+00:00')) if response.get("last_lesson_date") else None
                )
        except Exception as e:
            logger.error(f"Error adding lessons to balance: {e}")
            return None
    
    async def get_student_transactions(
        self,
        student_id: int,
        page: int = 1,
        per_page: int = 20
    ) -> List[TransactionInfo]:
        """Get transactions for student"""
        try:
            response = await self._get(
                f"/api/v1/transactions/{student_id}",
                params={"page": page, "per_page": per_page}
            )
            
            if response and "transactions" in response:
                transactions = []
                for trans_data in response["transactions"]:
                    transactions.append(TransactionInfo(
                        id=trans_data["id"],
                        student_id=trans_data["student_id"],
                        transaction_type=trans_data["transaction_type"],
                        amount=trans_data["amount"],
                        lessons_count=trans_data["lessons_count"],
                        balance_before=trans_data["balance_before"],
                        balance_after=trans_data["balance_after"],
                        description=trans_data["description"],
                        created_at=datetime.fromisoformat(trans_data["created_at"].replace('Z', '+00:00')),
                        payment_id=trans_data.get("payment_id"),
                        lesson_id=trans_data.get("lesson_id")
                    ))
                return transactions
            return []
        except Exception as e:
            logger.error(f"Error getting student transactions: {e}")
            return []
    
    async def cancel_payment(self, payment_id: int, reason: str) -> bool:
        """Cancel payment and adjust balance"""
        try:
            response = await self._post(
                f"/api/v1/payments/{payment_id}/cancel",
                params={"reason": reason}
            )
            return response is not None
        except Exception as e:
            logger.error(f"Error cancelling payment: {e}")
            return False
    
    async def get_payment_summary(self, student_id: int) -> Optional[Dict[str, Any]]:
        """Get payment summary for student"""
        try:
            response = await self._get(f"/api/v1/payments/student/{student_id}/summary")
            return response
        except Exception as e:
            logger.error(f"Error getting payment summary: {e}")
            return None
    
    # Compatibility methods (using existing database function names)
    async def get_student_balance_legacy(self, student_id: int) -> int:
        """Get student balance (legacy compatibility)"""
        return await self.get_simple_balance(student_id)
    
    async def get_payments_for_student_by_month(
        self,
        student_id: int,
        year: int,
        month: int
    ) -> List[Dict[str, Any]]:
        """Get payments for student by month (legacy compatibility)"""
        payments = await self.get_monthly_payments(student_id, year, month)
        
        # Convert to legacy format
        legacy_payments = []
        for payment in payments:
            legacy_payments.append({
                "id": payment.id,
                "student_id": payment.student_id,
                "lessons_paid": payment.lessons_paid,
                "payment_date": payment.payment_date
            })
        
        return legacy_payments