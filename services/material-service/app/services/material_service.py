# -*- coding: utf-8 -*-
"""
Material Service Business Logic
Core functionality for material management
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, text
from sqlalchemy.orm import selectinload

from ..models.material import (
    Material, MaterialCategory, MaterialFile, MaterialReview,
    MaterialType, AccessLevel, MaterialAccess
)
from ..schemas.material import (
    MaterialCreate, MaterialUpdate, MaterialResponse,
    MaterialSearchRequest, MaterialStatsResponse,
    MaterialCategoryCreate, MaterialCategoryResponse
)
from ..database.connection import db_manager
from ..core.config import settings
from .file_service import FileService

logger = logging.getLogger(__name__)


class MaterialService:
    """Service for material management"""
    
    def __init__(self):
        self.file_service = FileService()
    
    async def create_material(
        self,
        material_data: MaterialCreate,
        session: Optional[AsyncSession] = None
    ) -> MaterialResponse:
        """Create new material"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Convert tags to JSON string
            tags_json = json.dumps(material_data.tags) if material_data.tags else None
            
            # Create material record
            material = Material(
                title=material_data.title,
                description=material_data.description,
                link=str(material_data.link) if material_data.link else None,
                material_type=material_data.material_type,
                grade=material_data.grade,
                subject=material_data.subject,
                topic=material_data.topic,
                access_level=material_data.access_level,
                tags=tags_json,
                difficulty_level=material_data.difficulty_level,
                estimated_time=material_data.estimated_time,
                language=material_data.language,
                category_id=material_data.category_id,
                is_featured=material_data.is_featured,
                created_by_user_id=material_data.created_by_user_id
            )
            
            session.add(material)
            await session.flush()  # Get ID
            await session.commit()
            
            logger.info(f"Material created: {material.id} - {material.title}")
            
            # Load with relationships for response
            return await self.get_material(material.id, session)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating material: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def get_material(
        self,
        material_id: int,
        session: Optional[AsyncSession] = None
    ) -> Optional[MaterialResponse]:
        """Get material by ID with all relationships"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            result = await session.execute(
                select(Material)
                .options(
                    selectinload(Material.category),
                    selectinload(Material.files),
                    selectinload(Material.reviews)
                )
                .where(Material.id == material_id)
            )
            material = result.scalar_one_or_none()
            
            if not material:
                return None
            
            # Parse tags from JSON
            tags = []
            if material.tags:
                try:
                    tags = json.loads(material.tags)
                except:
                    pass
            
            # Create response with parsed tags
            response_data = {
                **{k: v for k, v in material.__dict__.items() if not k.startswith('_')},
                'tags': tags,
                'category': material.category,
                'files': material.files
            }
            
            return MaterialResponse.model_validate(response_data)
            
        finally:
            if should_close:
                await session.close()
    
    async def update_material(
        self,
        material_id: int,
        material_update: MaterialUpdate,
        session: Optional[AsyncSession] = None
    ) -> Optional[MaterialResponse]:
        """Update material"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            result = await session.execute(
                select(Material).where(Material.id == material_id)
            )
            material = result.scalar_one_or_none()
            
            if not material:
                return None
            
            # Update fields
            update_data = material_update.model_dump(exclude_unset=True)
            
            # Handle tags conversion
            if 'tags' in update_data:
                update_data['tags'] = json.dumps(update_data['tags']) if update_data['tags'] else None
            
            # Handle link conversion
            if 'link' in update_data and update_data['link']:
                update_data['link'] = str(update_data['link'])
            
            for field, value in update_data.items():
                setattr(material, field, value)
            
            material.updated_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(f"Material updated: {material_id}")
            return await self.get_material(material_id, session)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating material: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def delete_material(
        self,
        material_id: int,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """Delete material and associated files"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Get material with files
            result = await session.execute(
                select(Material)
                .options(selectinload(Material.files))
                .where(Material.id == material_id)
            )
            material = result.scalar_one_or_none()
            
            if not material:
                return False
            
            # Delete associated files from storage
            for file in material.files:
                await self.file_service.delete_file(file.id, session)
            
            # Delete material record (files will be cascade deleted)
            await session.delete(material)
            await session.commit()
            
            logger.info(f"Material deleted: {material_id}")
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting material: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def search_materials(
        self,
        search_request: MaterialSearchRequest,
        session: Optional[AsyncSession] = None
    ) -> Tuple[List[MaterialResponse], int]:
        """Search materials with filters and pagination"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Build base query
            query = select(Material).options(
                selectinload(Material.category),
                selectinload(Material.files)
            )
            
            # Apply filters
            conditions = [Material.is_active == True]
            
            if search_request.query:
                search_term = f"%{search_request.query}%"
                conditions.append(
                    or_(
                        Material.title.ilike(search_term),
                        Material.description.ilike(search_term),
                        Material.subject.ilike(search_term),
                        Material.topic.ilike(search_term),
                        Material.tags.ilike(search_term)
                    )
                )
            
            if search_request.grade:
                conditions.append(Material.grade == search_request.grade)
            
            if search_request.material_type:
                conditions.append(Material.material_type == search_request.material_type)
            
            if search_request.subject:
                conditions.append(Material.subject.ilike(f"%{search_request.subject}%"))
            
            if search_request.category_id:
                conditions.append(Material.category_id == search_request.category_id)
            
            if search_request.difficulty_level:
                conditions.append(Material.difficulty_level == search_request.difficulty_level)
            
            if search_request.is_featured is not None:
                conditions.append(Material.is_featured == search_request.is_featured)
            
            if search_request.created_by_user_id:
                conditions.append(Material.created_by_user_id == search_request.created_by_user_id)
            
            if search_request.tags:
                for tag in search_request.tags:
                    conditions.append(Material.tags.ilike(f'%"{tag}"%'))
            
            # Apply rating filter if specified
            if search_request.min_rating:
                # This requires a subquery to calculate average rating
                rating_subquery = (
                    select(func.avg(MaterialReview.rating).label('avg_rating'))
                    .where(MaterialReview.material_id == Material.id)
                    .where(MaterialReview.is_approved == True)
                    .subquery()
                )
                conditions.append(rating_subquery.c.avg_rating >= search_request.min_rating)
            
            # Apply all conditions
            if conditions:
                query = query.where(and_(*conditions))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await session.execute(count_query)
            total = count_result.scalar()
            
            # Apply sorting
            sort_column = getattr(Material, search_request.sort_by, Material.created_at)
            if search_request.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
            
            # Apply pagination
            query = query.offset((search_request.page - 1) * search_request.per_page)
            query = query.limit(search_request.per_page)
            
            # Execute query
            result = await session.execute(query)
            materials = result.scalars().all()
            
            # Convert to response models
            material_responses = []
            for material in materials:
                # Parse tags
                tags = []
                if material.tags:
                    try:
                        tags = json.loads(material.tags)
                    except:
                        pass
                
                response_data = {
                    **{k: v for k, v in material.__dict__.items() if not k.startswith('_')},
                    'tags': tags,
                    'category': material.category,
                    'files': material.files
                }
                material_responses.append(MaterialResponse.model_validate(response_data))
            
            return material_responses, total
            
        finally:
            if should_close:
                await session.close()
    
    async def get_materials_by_grade(self, grade: int) -> List[MaterialResponse]:
        """Get materials for specific grade (compatibility method)"""
        search_request = MaterialSearchRequest(
            grade=grade,
            per_page=1000,  # Get all for compatibility
            sort_by="created_at",
            sort_order="desc"
        )
        materials, _ = await self.search_materials(search_request)
        return materials
    
    async def increment_view_count(
        self,
        material_id: int,
        user_id: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ):
        """Increment material view count and log access"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Update view count
            result = await session.execute(
                select(Material).where(Material.id == material_id)
            )
            material = result.scalar_one_or_none()
            
            if material:
                material.view_count += 1
                material.updated_at = datetime.utcnow()
                
                # Log access if enabled
                if settings.ENABLE_VIEW_TRACKING:
                    access_log = MaterialAccess(
                        material_id=material_id,
                        user_id=user_id,
                        access_type="view",
                        accessed_at=datetime.utcnow()
                    )
                    session.add(access_log)
                
                await session.commit()
                
        except Exception as e:
            await session.rollback()
            logger.error(f"Error incrementing view count: {e}")
        finally:
            if should_close:
                await session.close()
    
    async def get_material_stats(
        self,
        session: Optional[AsyncSession] = None
    ) -> MaterialStatsResponse:
        """Get material statistics"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Get total counts
            total_materials_result = await session.execute(
                select(func.count(Material.id)).where(Material.is_active == True)
            )
            total_materials = total_materials_result.scalar()
            
            total_files_result = await session.execute(
                select(func.count(MaterialFile.id)).where(MaterialFile.is_active == True)
            )
            total_files = total_files_result.scalar()
            
            total_downloads_result = await session.execute(
                select(func.sum(Material.download_count)).where(Material.is_active == True)
            )
            total_downloads = total_downloads_result.scalar() or 0
            
            total_views_result = await session.execute(
                select(func.sum(Material.view_count)).where(Material.is_active == True)
            )
            total_views = total_views_result.scalar() or 0
            
            # Get materials by grade
            grade_stats_result = await session.execute(
                select(Material.grade, func.count(Material.id))
                .where(Material.is_active == True)
                .group_by(Material.grade)
            )
            materials_by_grade = {row[0]: row[1] for row in grade_stats_result.fetchall()}
            
            # Get materials by type
            type_stats_result = await session.execute(
                select(Material.material_type, func.count(Material.id))
                .where(Material.is_active == True)
                .group_by(Material.material_type)
            )
            materials_by_type = {row[0].value: row[1] for row in type_stats_result.fetchall()}
            
            # Get materials by subject
            subject_stats_result = await session.execute(
                select(Material.subject, func.count(Material.id))
                .where(and_(Material.is_active == True, Material.subject.isnot(None)))
                .group_by(Material.subject)
            )
            materials_by_subject = {row[0]: row[1] for row in subject_stats_result.fetchall()}
            
            # Get popular materials (top 10 by views)
            popular_result = await session.execute(
                select(Material)
                .options(selectinload(Material.category), selectinload(Material.files))
                .where(Material.is_active == True)
                .order_by(desc(Material.view_count))
                .limit(10)
            )
            popular_materials_data = popular_result.scalars().all()
            popular_materials = []
            for material in popular_materials_data:
                tags = []
                if material.tags:
                    try:
                        tags = json.loads(material.tags)
                    except:
                        pass
                response_data = {
                    **{k: v for k, v in material.__dict__.items() if not k.startswith('_')},
                    'tags': tags,
                    'category': material.category,
                    'files': material.files
                }
                popular_materials.append(MaterialResponse.model_validate(response_data))
            
            # Get recent materials (last 10)
            recent_result = await session.execute(
                select(Material)
                .options(selectinload(Material.category), selectinload(Material.files))
                .where(Material.is_active == True)
                .order_by(desc(Material.created_at))
                .limit(10)
            )
            recent_materials_data = recent_result.scalars().all()
            recent_materials = []
            for material in recent_materials_data:
                tags = []
                if material.tags:
                    try:
                        tags = json.loads(material.tags)
                    except:
                        pass
                response_data = {
                    **{k: v for k, v in material.__dict__.items() if not k.startswith('_')},
                    'tags': tags,
                    'category': material.category,
                    'files': material.files
                }
                recent_materials.append(MaterialResponse.model_validate(response_data))
            
            return MaterialStatsResponse(
                total_materials=total_materials,
                total_files=total_files,
                total_downloads=total_downloads,
                total_views=total_views,
                materials_by_grade=materials_by_grade,
                materials_by_type=materials_by_type,
                materials_by_subject=materials_by_subject,
                popular_materials=popular_materials,
                recent_materials=recent_materials
            )
            
        finally:
            if should_close:
                await session.close()
    
    # Category management methods
    async def create_category(
        self,
        category_data: MaterialCategoryCreate,
        session: Optional[AsyncSession] = None
    ) -> MaterialCategoryResponse:
        """Create material category"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            category = MaterialCategory(**category_data.model_dump())
            session.add(category)
            await session.flush()
            await session.commit()
            
            logger.info(f"Category created: {category.id} - {category.name}")
            return MaterialCategoryResponse.model_validate(category)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating category: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def get_categories(
        self,
        include_children: bool = True,
        session: Optional[AsyncSession] = None
    ) -> List[MaterialCategoryResponse]:
        """Get all categories with optional children"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            query = select(MaterialCategory).where(MaterialCategory.is_active == True)
            
            if include_children:
                query = query.options(selectinload(MaterialCategory.children))
            
            query = query.order_by(MaterialCategory.sort_order, MaterialCategory.name)
            
            result = await session.execute(query)
            categories = result.scalars().all()
            
            return [MaterialCategoryResponse.model_validate(cat) for cat in categories]
            
        finally:
            if should_close:
                await session.close()