# -*- coding: utf-8 -*-
"""
User Service HTTP Client
Handles communication with User Service for student/user data
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal

from .base_client import BaseServiceClient, ServiceClientError
from ..core.config import settings

logger = logging.getLogger(__name__)


class UserServiceClient(BaseServiceClient):
    """Client for User Service API"""
    
    def __init__(self):
        super().__init__(
            base_url=settings.USER_SERVICE_URL,
            service_name="user-service"
        )
    
    async def get_student(self, student_id: int, auth_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get student information by ID"""
        try:
            response = await self.get(
                f"/api/v1/students/{student_id}",
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get student {student_id}: {e}")
            return None
    
    async def get_students(
        self,
        user_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        tutor_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get students list with filters"""
        try:
            params = {
                "page": page,
                "per_page": per_page
            }
            
            if user_id:
                params["user_id"] = user_id
            if parent_id:
                params["parent_id"] = parent_id
            if tutor_id:
                params["tutor_id"] = tutor_id
            
            response = await self.get(
                "/api/v1/students",
                params=params,
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get students: {e}")
            return {"students": [], "total": 0}
    
    async def get_user(self, user_id: int, auth_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get user information by ID"""
        try:
            response = await self.get(
                f"/api/v1/users/{user_id}",
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def get_parent_by_student(self, student_id: int, auth_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get parent information for a student"""
        try:
            response = await self.get(
                f"/api/v1/students/{student_id}/parent",
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get parent for student {student_id}: {e}")
            return None
    
    async def get_tutor_by_student(self, student_id: int, auth_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get tutor information for a student"""
        try:
            response = await self.get(
                f"/api/v1/students/{student_id}/tutor",
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get tutor for student {student_id}: {e}")
            return None
    
    async def validate_student_access(
        self,
        student_id: int,
        user_id: int,
        auth_token: Optional[str] = None
    ) -> bool:
        """Validate if user has access to student data (parent/tutor check)"""
        try:
            response = await self.get(
                f"/api/v1/students/{student_id}/access/{user_id}",
                auth_token=auth_token
            )
            return response.get("has_access", False)
            
        except ServiceClientError as e:
            logger.error(f"Failed to validate access for user {user_id} to student {student_id}: {e}")
            return False
    
    async def get_students_by_parent(self, parent_id: int, auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all students for a parent"""
        try:
            response = await self.get(
                f"/api/v1/parents/{parent_id}/students",
                auth_token=auth_token
            )
            return response.get("students", [])
            
        except ServiceClientError as e:
            logger.error(f"Failed to get students for parent {parent_id}: {e}")
            return []
    
    async def get_students_by_tutor(self, tutor_id: int, auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all students for a tutor"""
        try:
            response = await self.get(
                f"/api/v1/tutors/{tutor_id}/students",
                auth_token=auth_token
            )
            return response.get("students", [])
            
        except ServiceClientError as e:
            logger.error(f"Failed to get students for tutor {tutor_id}: {e}")
            return []
    
    async def update_student_balance_cache(
        self,
        student_id: int,
        balance: int,
        auth_token: Optional[str] = None
    ) -> bool:
        """Update student balance cache in User Service"""
        try:
            data = {
                "balance": balance,
                "updated_by_service": "payment-service"
            }
            
            await self.patch(
                f"/api/v1/students/{student_id}/balance",
                data=data,
                auth_token=auth_token
            )
            return True
            
        except ServiceClientError as e:
            logger.error(f"Failed to update balance cache for student {student_id}: {e}")
            return False
    
    async def get_student_contact_info(self, student_id: int, auth_token: Optional[str] = None) -> Dict[str, Any]:
        """Get student contact information for notifications"""
        try:
            response = await self.get(
                f"/api/v1/students/{student_id}/contacts",
                auth_token=auth_token
            )
            return response
            
        except ServiceClientError as e:
            logger.error(f"Failed to get contact info for student {student_id}: {e}")
            return {}
    
    async def verify_user_role(
        self,
        user_id: int,
        required_role: str,
        auth_token: Optional[str] = None
    ) -> bool:
        """Verify if user has required role"""
        try:
            response = await self.get(
                f"/api/v1/users/{user_id}/role",
                auth_token=auth_token
            )
            user_role = response.get("role", "").lower()
            return user_role == required_role.lower()
            
        except ServiceClientError as e:
            logger.error(f"Failed to verify role for user {user_id}: {e}")
            return False
    
    async def get_user_permissions(self, user_id: int, auth_token: Optional[str] = None) -> List[str]:
        """Get user permissions"""
        try:
            response = await self.get(
                f"/api/v1/users/{user_id}/permissions",
                auth_token=auth_token
            )
            return response.get("permissions", [])
            
        except ServiceClientError as e:
            logger.error(f"Failed to get permissions for user {user_id}: {e}")
            return []


class MockUserServiceClient(UserServiceClient):
    """Mock User Service client for testing and development"""
    
    async def get_student(self, student_id: int, auth_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Mock get student"""
        return {
            "id": student_id,
            "name": f"Test Student {student_id}",
            "grade": 10,
            "parent_id": student_id + 1000,
            "tutor_id": student_id + 2000,
            "is_active": True
        }
    
    async def get_students(self, **kwargs) -> Dict[str, Any]:
        """Mock get students"""
        return {
            "students": [
                await self.get_student(1),
                await self.get_student(2)
            ],
            "total": 2
        }
    
    async def validate_student_access(self, student_id: int, user_id: int, auth_token: Optional[str] = None) -> bool:
        """Mock validate access - always return True for testing"""
        return True
    
    async def health_check(self) -> bool:
        """Mock health check"""
        return True