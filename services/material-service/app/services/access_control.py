# -*- coding: utf-8 -*-
"""
Access Control Service for Material Service
Handles permissions, role-based access, and material visibility
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..models.material import Material, MaterialAccess, AccessLevel
from ..database.connection import db_manager
from ..core.config import settings

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles in the system"""
    ADMIN = "admin"
    TUTOR = "tutor"
    PARENT = "parent"
    STUDENT = "student"
    GUEST = "guest"


class Permission(Enum):
    """Material permissions"""
    VIEW = "view"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    EDIT = "edit"
    DELETE = "delete"
    MANAGE_ACCESS = "manage_access"


class AccessControlService:
    """Service for managing material access control"""
    
    def __init__(self):
        # Role-based permissions matrix
        self.role_permissions = {
            UserRole.ADMIN: {
                Permission.VIEW, Permission.DOWNLOAD, Permission.UPLOAD,
                Permission.EDIT, Permission.DELETE, Permission.MANAGE_ACCESS
            },
            UserRole.TUTOR: {
                Permission.VIEW, Permission.DOWNLOAD, Permission.UPLOAD,
                Permission.EDIT
            },
            UserRole.PARENT: {
                Permission.VIEW, Permission.DOWNLOAD
            },
            UserRole.STUDENT: {
                Permission.VIEW, Permission.DOWNLOAD
            },
            UserRole.GUEST: {
                Permission.VIEW
            }
        }
        
        # Access level permissions
        self.access_level_permissions = {
            AccessLevel.PUBLIC: {Permission.VIEW, Permission.DOWNLOAD},
            AccessLevel.REGISTERED: {Permission.VIEW, Permission.DOWNLOAD},
            AccessLevel.PREMIUM: {Permission.VIEW, Permission.DOWNLOAD},
            AccessLevel.TUTOR_ONLY: {Permission.VIEW, Permission.DOWNLOAD},
            AccessLevel.ADMIN_ONLY: {Permission.VIEW, Permission.DOWNLOAD}
        }
    
    async def check_material_access(
        self,
        user_id: Optional[int],
        user_role: str,
        material_id: int,
        permission: Permission,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """Check if user has permission to access material"""
        
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Get material
            result = await session.execute(
                select(Material).where(Material.id == material_id)
            )
            material = result.scalar_one_or_none()
            
            if not material:
                return False
            
            # Check if material is active
            if not material.is_active:
                return False
            
            # Convert role string to enum
            try:
                role = UserRole(user_role.lower())
            except ValueError:
                role = UserRole.GUEST
            
            # Check role-based permissions
            if not self._has_role_permission(role, permission):
                return False
            
            # Check access level restrictions
            if not await self._check_access_level(user_id, role, material, session):
                return False
            
            # Check specific material permissions
            if not await self._check_material_specific_access(user_id, material, permission, session):
                return False
            
            # Check grade-level restrictions
            if not await self._check_grade_access(user_id, material, session):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking material access: {e}")
            return False
        finally:
            if should_close:
                await session.close()
    
    async def check_bulk_material_access(
        self,
        user_id: Optional[int],
        user_role: str,
        material_ids: List[int],
        permission: Permission,
        session: Optional[AsyncSession] = None
    ) -> Dict[int, bool]:
        """Check access for multiple materials at once"""
        
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            results = {}
            
            # Get all materials at once
            materials_result = await session.execute(
                select(Material).where(Material.id.in_(material_ids))
            )
            materials = {m.id: m for m in materials_result.scalars().all()}
            
            # Check access for each material
            for material_id in material_ids:
                if material_id in materials:
                    material = materials[material_id]
                    access = await self._check_single_material_access(
                        user_id, user_role, material, permission, session
                    )
                    results[material_id] = access
                else:
                    results[material_id] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Error checking bulk material access: {e}")
            return {material_id: False for material_id in material_ids}
        finally:
            if should_close:
                await session.close()
    
    async def filter_accessible_materials(
        self,
        user_id: Optional[int],
        user_role: str,
        materials: List[Material],
        permission: Permission = Permission.VIEW,
        session: Optional[AsyncSession] = None
    ) -> List[Material]:
        """Filter list of materials to only include accessible ones"""
        
        if not materials:
            return []
        
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            accessible_materials = []
            
            for material in materials:
                if await self._check_single_material_access(
                    user_id, user_role, material, permission, session
                ):
                    accessible_materials.append(material)
            
            return accessible_materials
            
        except Exception as e:
            logger.error(f"Error filtering accessible materials: {e}")
            return []
        finally:
            if should_close:
                await session.close()
    
    async def get_user_accessible_grades(
        self,
        user_id: Optional[int],
        user_role: str,
        session: Optional[AsyncSession] = None
    ) -> List[int]:
        """Get list of grades user can access"""
        
        try:
            role = UserRole(user_role.lower())
        except ValueError:
            role = UserRole.GUEST
        
        # Admins and tutors can access all grades
        if role in [UserRole.ADMIN, UserRole.TUTOR]:
            return list(range(1, 12))  # Grades 1-11
        
        # Parents and students can access specific grades
        if user_id and role in [UserRole.PARENT, UserRole.STUDENT]:
            # This would integrate with User Service to get student grades
            # For now, return default grades
            return [10, 11]  # Default grades
        
        # Guests can access public materials from all grades
        return list(range(1, 12))
    
    async def log_material_access(
        self,
        user_id: Optional[int],
        material_id: int,
        access_type: str,
        file_id: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ):
        """Log material access for analytics and auditing"""
        
        if not settings.ENABLE_ACCESS_LOGGING:
            return
        
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            access_log = MaterialAccess(
                material_id=material_id,
                file_id=file_id,
                user_id=user_id,
                access_type=access_type,
                accessed_at=datetime.utcnow(),
                ip_address="unknown",  # Would get from request context
                user_agent="unknown"   # Would get from request context
            )
            
            session.add(access_log)
            await session.commit()
            
        except Exception as e:
            logger.error(f"Error logging material access: {e}")
        finally:
            if should_close:
                await session.close()
    
    async def get_material_access_stats(
        self,
        material_id: int,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Get access statistics for material"""
        
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Get access logs
            from sqlalchemy import func
            
            result = await session.execute(
                select(
                    MaterialAccess.access_type,
                    func.count(MaterialAccess.id).label('count'),
                    func.count(func.distinct(MaterialAccess.user_id)).label('unique_users')
                )
                .where(MaterialAccess.material_id == material_id)
                .group_by(MaterialAccess.access_type)
            )
            
            stats = {}
            for row in result.fetchall():
                stats[row.access_type] = {
                    "total_accesses": row.count,
                    "unique_users": row.unique_users
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting material access stats: {e}")
            return {}
        finally:
            if should_close:
                await session.close()
    
    def _has_role_permission(self, role: UserRole, permission: Permission) -> bool:
        """Check if role has specific permission"""
        return permission in self.role_permissions.get(role, set())
    
    async def _check_access_level(
        self,
        user_id: Optional[int],
        role: UserRole,
        material: Material,
        session: AsyncSession
    ) -> bool:
        """Check access level restrictions"""
        
        material_access_level = material.access_level
        
        if material_access_level == AccessLevel.PUBLIC:
            return True
        
        if material_access_level == AccessLevel.REGISTERED:
            return user_id is not None
        
        if material_access_level == AccessLevel.PREMIUM:
            # Check if user has premium access
            return await self._check_premium_access(user_id, session)
        
        if material_access_level == AccessLevel.TUTOR_ONLY:
            return role in [UserRole.ADMIN, UserRole.TUTOR]
        
        if material_access_level == AccessLevel.ADMIN_ONLY:
            return role == UserRole.ADMIN
        
        return False
    
    async def _check_material_specific_access(
        self,
        user_id: Optional[int],
        material: Material,
        permission: Permission,
        session: AsyncSession
    ) -> bool:
        """Check material-specific access rules"""
        
        # Check if user is the creator
        if user_id and material.created_by_user_id == user_id:
            return True
        
        # Check if material is featured (more permissive access)
        if material.is_featured and permission == Permission.VIEW:
            return True
        
        # Additional material-specific rules can be added here
        
        return True
    
    async def _check_grade_access(
        self,
        user_id: Optional[int],
        material: Material,
        session: AsyncSession
    ) -> bool:
        """Check if user can access materials for this grade"""
        
        if not material.grade:
            return True  # No grade restriction
        
        # This would integrate with User Service to check if user
        # has access to this grade level
        
        return True  # Allow access for now
    
    async def _check_premium_access(
        self,
        user_id: Optional[int],
        session: AsyncSession
    ) -> bool:
        """Check if user has premium access"""
        
        if not user_id:
            return False
        
        # This would integrate with Payment Service to check subscription status
        # For now, return False (no premium access)
        
        return False
    
    async def _check_single_material_access(
        self,
        user_id: Optional[int],
        user_role: str,
        material: Material,
        permission: Permission,
        session: AsyncSession
    ) -> bool:
        """Check access for a single material (internal helper)"""
        
        try:
            # Check if material is active
            if not material.is_active:
                return False
            
            # Convert role string to enum
            try:
                role = UserRole(user_role.lower())
            except ValueError:
                role = UserRole.GUEST
            
            # Check role-based permissions
            if not self._has_role_permission(role, permission):
                return False
            
            # Check access level restrictions
            if not await self._check_access_level(user_id, role, material, session):
                return False
            
            # Check specific material permissions
            if not await self._check_material_specific_access(user_id, material, permission, session):
                return False
            
            # Check grade-level restrictions
            if not await self._check_grade_access(user_id, material, session):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking single material access: {e}")
            return False


class MockAccessControlService(AccessControlService):
    """Mock access control service for testing"""
    
    async def check_material_access(self, *args, **kwargs) -> bool:
        """Mock - always allow access"""
        return True
    
    async def check_bulk_material_access(self, user_id, user_role, material_ids, permission, session=None) -> Dict[int, bool]:
        """Mock - always allow access"""
        return {material_id: True for material_id in material_ids}
    
    async def filter_accessible_materials(self, user_id, user_role, materials, permission=Permission.VIEW, session=None) -> List[Material]:
        """Mock - return all materials"""
        return materials
    
    async def get_user_accessible_grades(self, user_id, user_role, session=None) -> List[int]:
        """Mock - return all grades"""
        return list(range(1, 12))