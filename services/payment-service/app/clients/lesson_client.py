# -*- coding: utf-8 -*-
"""
Lesson Service HTTP Client  
Handles communication with Lesson Service for lesson data
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal

from .base_client import BaseServiceClient, ServiceClientError
from ..core.config import settings

logger = logging.getLogger(__name__)


class LessonServiceClient(BaseServiceClient):
    """Client for Lesson Service API"""
    
    def __init__(self):
        super().__init__(
            base_url=settings.LESSON_SERVICE_URL,
            service_name="lesson-service"
        )
    
    async def get_lesson(self, lesson_id: int, auth_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get lesson information by ID"""
        try:
            response = await self.get(
                f"/api/v1/lessons/{lesson_id}",
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get lesson {lesson_id}: {e}")
            return None
    
    async def get_lessons(
        self,
        student_id: Optional[int] = None,
        tutor_id: Optional[int] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        per_page: int = 20,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get lessons list with filters"""
        try:
            params = {
                "page": page,
                "per_page": per_page
            }
            
            if student_id:
                params["student_id"] = student_id
            if tutor_id:
                params["tutor_id"] = tutor_id
            if status:
                params["status"] = status
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
            
            response = await self.get(
                "/api/v1/lessons",
                params=params,
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get lessons: {e}")
            return {"lessons": [], "total": 0}
    
    async def get_lesson_price(self, lesson_id: int, auth_token: Optional[str] = None) -> Optional[Decimal]:
        """Get lesson price"""
        try:
            response = await self.get(
                f"/api/v1/lessons/{lesson_id}/price",
                auth_token=auth_token
            )
            price = response.get("price")
            return Decimal(str(price)) if price else None
            
        except ServiceClientError as e:
            logger.error(f"Failed to get price for lesson {lesson_id}: {e}")
            return None
    
    async def get_student_lesson_stats(
        self,
        student_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get lesson statistics for student"""
        try:
            params = {}
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
            
            response = await self.get(
                f"/api/v1/students/{student_id}/lesson-stats",
                params=params,
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get lesson stats for student {student_id}: {e}")
            return {}
    
    async def get_completed_lessons(
        self,
        student_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get completed lessons for student"""
        try:
            params = {"status": "completed"}
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
            
            response = await self.get_lessons(
                student_id=student_id,
                **params,
                per_page=1000,  # Get all completed lessons
                auth_token=auth_token
            )
            return response.get("lessons", [])
            
        except ServiceClientError as e:
            logger.error(f"Failed to get completed lessons for student {student_id}: {e}")
            return []
    
    async def get_cancelled_lessons(
        self,
        student_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get cancelled lessons for student"""
        try:
            params = {"status": "cancelled"}
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
            
            response = await self.get_lessons(
                student_id=student_id,
                **params,
                per_page=1000,  # Get all cancelled lessons
                auth_token=auth_token
            )
            return response.get("lessons", [])
            
        except ServiceClientError as e:
            logger.error(f"Failed to get cancelled lessons for student {student_id}: {e}")
            return []
    
    async def get_upcoming_lessons(
        self,
        student_id: int,
        days_ahead: int = 7,
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get upcoming lessons for student"""
        try:
            from datetime import timedelta
            start_date = date.today()
            end_date = start_date + timedelta(days=days_ahead)
            
            response = await self.get_lessons(
                student_id=student_id,
                status="scheduled",
                start_date=start_date,
                end_date=end_date,
                per_page=100,
                auth_token=auth_token
            )
            return response.get("lessons", [])
            
        except ServiceClientError as e:
            logger.error(f"Failed to get upcoming lessons for student {student_id}: {e}")
            return []
    
    async def validate_lesson_access(
        self,
        lesson_id: int,
        user_id: int,
        auth_token: Optional[str] = None
    ) -> bool:
        """Validate if user has access to lesson (student/parent/tutor check)"""
        try:
            response = await self.get(
                f"/api/v1/lessons/{lesson_id}/access/{user_id}",
                auth_token=auth_token
            )
            return response.get("has_access", False)
            
        except ServiceClientError as e:
            logger.error(f"Failed to validate access for user {user_id} to lesson {lesson_id}: {e}")
            return False
    
    async def get_lesson_pricing_rules(
        self,
        student_id: Optional[int] = None,
        tutor_id: Optional[int] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get pricing rules for lessons"""
        try:
            params = {}
            if student_id:
                params["student_id"] = student_id
            if tutor_id:
                params["tutor_id"] = tutor_id
            
            response = await self.get(
                "/api/v1/pricing-rules",
                params=params,
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get pricing rules: {e}")
            return {}
    
    async def calculate_lesson_cost(
        self,
        student_id: int,
        lesson_type: str = "regular",
        duration_minutes: int = 60,
        auth_token: Optional[str] = None
    ) -> Optional[Decimal]:
        """Calculate cost for a lesson"""
        try:
            data = {
                "student_id": student_id,
                "lesson_type": lesson_type,
                "duration_minutes": duration_minutes
            }
            
            response = await self.post(
                "/api/v1/lessons/calculate-cost",
                data=data,
                auth_token=auth_token
            )
            
            cost = response.get("cost")
            return Decimal(str(cost)) if cost else None
            
        except ServiceClientError as e:
            logger.error(f"Failed to calculate lesson cost: {e}")
            return None
    
    async def mark_lesson_paid(
        self,
        lesson_id: int,
        payment_id: int,
        auth_token: Optional[str] = None
    ) -> bool:
        """Mark lesson as paid with payment reference"""
        try:
            data = {
                "payment_id": payment_id,
                "paid_at": datetime.utcnow().isoformat(),
                "paid_by_service": "payment-service"
            }
            
            await self.patch(
                f"/api/v1/lessons/{lesson_id}/payment",
                data=data,
                auth_token=auth_token
            )
            return True
            
        except ServiceClientError as e:
            logger.error(f"Failed to mark lesson {lesson_id} as paid: {e}")
            return False
    
    async def get_monthly_lesson_summary(
        self,
        student_id: int,
        year: int,
        month: int,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get monthly lesson summary for student"""
        try:
            params = {
                "year": year,
                "month": month
            }
            
            response = await self.get(
                f"/api/v1/students/{student_id}/monthly-summary",
                params=params,
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get monthly summary for student {student_id}: {e}")
            return {}


class MockLessonServiceClient(LessonServiceClient):
    """Mock Lesson Service client for testing and development"""
    
    async def get_lesson(self, lesson_id: int, auth_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Mock get lesson"""
        return {
            "id": lesson_id,
            "student_id": 1,
            "tutor_id": 100,
            "topic": f"Test Lesson {lesson_id}",
            "status": "completed",
            "scheduled_at": "2024-01-15T10:00:00Z",
            "duration_minutes": 60,
            "price": str(settings.DEFAULT_PRICE_PER_LESSON)
        }
    
    async def get_lessons(self, **kwargs) -> Dict[str, Any]:
        """Mock get lessons"""
        return {
            "lessons": [
                await self.get_lesson(1),
                await self.get_lesson(2)
            ],
            "total": 2
        }
    
    async def get_lesson_price(self, lesson_id: int, auth_token: Optional[str] = None) -> Optional[Decimal]:
        """Mock get lesson price"""
        return settings.DEFAULT_PRICE_PER_LESSON
    
    async def validate_lesson_access(self, lesson_id: int, user_id: int, auth_token: Optional[str] = None) -> bool:
        """Mock validate access - always return True for testing"""
        return True
    
    async def health_check(self) -> bool:
        """Mock health check"""
        return True