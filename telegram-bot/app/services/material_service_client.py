# -*- coding: utf-8 -*-
"""
Material Service HTTP Client
Client for interacting with Material microservice
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, BinaryIO
from dataclasses import dataclass

from .api_client import APIClient

logger = logging.getLogger(__name__)


@dataclass
class MaterialInfo:
    """Material information data class"""
    id: int
    title: str
    description: Optional[str]
    link: Optional[str]
    grade: int
    subject: Optional[str]
    topic: Optional[str]
    material_type: str
    tags: List[str]
    difficulty_level: Optional[int]
    estimated_time: Optional[int]
    view_count: int
    download_count: int
    average_rating: float
    is_featured: bool
    created_at: datetime
    created_by_user_id: Optional[int] = None
    category: Optional[Dict[str, Any]] = None
    files: List[Dict[str, Any]] = None


@dataclass
class MaterialCategoryInfo:
    """Material category information data class"""
    id: int
    name: str
    description: Optional[str]
    color: Optional[str]
    icon: Optional[str]
    sort_order: int
    is_active: bool
    parent_id: Optional[int] = None
    children: List['MaterialCategoryInfo'] = None


@dataclass
class MaterialFileInfo:
    """Material file information data class"""
    id: int
    filename: str
    original_filename: str
    file_url: Optional[str]
    file_type: str
    file_size: int
    title: Optional[str]
    description: Optional[str]
    is_primary: bool
    is_downloadable: bool
    access_count: int
    created_at: datetime


class MaterialServiceClient(APIClient):
    """Client for Material Service API"""
    
    def __init__(self, base_url: str = "http://localhost:8004"):
        super().__init__(base_url)
        self.service_name = "material-service"
    
    async def create_material(
        self,
        title: str,
        grade: int,
        description: Optional[str] = None,
        link: Optional[str] = None,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        material_type: str = "other",
        tags: List[str] = None,
        created_by_user_id: Optional[int] = None
    ) -> Optional[MaterialInfo]:
        """Create new material"""
        try:
            payload = {
                "title": title,
                "grade": grade,
                "description": description,
                "link": link,
                "subject": subject,
                "topic": topic,
                "material_type": material_type,
                "tags": tags or [],
                "created_by_user_id": created_by_user_id
            }
            
            response = await self._post("/api/v1/materials", json=payload)
            
            if response:
                return self._parse_material(response)
        except Exception as e:
            logger.error(f"Error creating material: {e}")
            return None
    
    async def get_material(self, material_id: int) -> Optional[MaterialInfo]:
        """Get material by ID"""
        try:
            response = await self._get(f"/api/v1/materials/{material_id}")
            
            if response:
                return self._parse_material(response)
        except Exception as e:
            logger.error(f"Error getting material {material_id}: {e}")
            return None
    
    async def update_material(
        self,
        material_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        link: Optional[str] = None,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_featured: Optional[bool] = None
    ) -> Optional[MaterialInfo]:
        """Update material"""
        try:
            payload = {}
            if title is not None:
                payload["title"] = title
            if description is not None:
                payload["description"] = description
            if link is not None:
                payload["link"] = link
            if subject is not None:
                payload["subject"] = subject
            if topic is not None:
                payload["topic"] = topic
            if tags is not None:
                payload["tags"] = tags
            if is_featured is not None:
                payload["is_featured"] = is_featured
            
            if not payload:
                return await self.get_material(material_id)
            
            response = await self._put(f"/api/v1/materials/{material_id}", json=payload)
            
            if response:
                return self._parse_material(response)
        except Exception as e:
            logger.error(f"Error updating material: {e}")
            return None
    
    async def delete_material(self, material_id: int) -> bool:
        """Delete material"""
        try:
            response = await self._delete(f"/api/v1/materials/{material_id}")
            return response is not None
        except Exception as e:
            logger.error(f"Error deleting material: {e}")
            return False
    
    async def search_materials(
        self,
        query: Optional[str] = None,
        grade: Optional[int] = None,
        material_type: Optional[str] = None,
        subject: Optional[str] = None,
        is_featured: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20
    ) -> List[MaterialInfo]:
        """Search materials with filters"""
        try:
            params = {
                "page": page,
                "per_page": per_page
            }
            
            if query:
                params["query"] = query
            if grade:
                params["grade"] = grade
            if material_type:
                params["material_type"] = material_type
            if subject:
                params["subject"] = subject
            if is_featured is not None:
                params["is_featured"] = is_featured
            
            response = await self._get("/api/v1/materials", params=params)
            
            if response and "materials" in response:
                return [self._parse_material(material_data) for material_data in response["materials"]]
            return []
        except Exception as e:
            logger.error(f"Error searching materials: {e}")
            return []
    
    async def get_materials_by_grade(self, grade: int) -> List[Dict[str, Any]]:
        """Get materials by grade (legacy compatibility)"""
        try:
            response = await self._get(f"/api/v1/materials/grade/{grade}")
            
            if response:
                return response
            return []
        except Exception as e:
            logger.error(f"Error getting materials by grade: {e}")
            return []
    
    async def get_all_materials(self) -> List[Dict[str, Any]]:
        """Get all materials (legacy compatibility)"""
        try:
            all_materials = []
            page = 1
            per_page = 100
            
            while True:
                response = await self._get(
                    "/api/v1/materials",
                    params={"page": page, "per_page": per_page}
                )
                
                if not response or "materials" not in response:
                    break
                
                materials = response["materials"]
                if not materials:
                    break
                
                # Convert to legacy format
                for material in materials:
                    all_materials.append({
                        "id": material["id"],
                        "title": material["title"],
                        "link": material.get("link"),
                        "description": material.get("description"),
                        "grade": material["grade"],
                        "created_at": material["created_at"]
                    })
                
                if len(materials) < per_page:
                    break
                
                page += 1
            
            return all_materials
        except Exception as e:
            logger.error(f"Error getting all materials: {e}")
            return []
    
    async def increment_view_count(self, material_id: int, user_id: Optional[int] = None) -> bool:
        """Increment material view count"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            
            response = await self._post(f"/api/v1/materials/{material_id}/view", params=params)
            return response is not None
        except Exception as e:
            logger.error(f"Error incrementing view count: {e}")
            return False
    
    async def get_material_stats(self) -> Optional[Dict[str, Any]]:
        """Get material statistics"""
        try:
            response = await self._get("/api/v1/materials/stats")
            return response
        except Exception as e:
            logger.error(f"Error getting material stats: {e}")
            return None
    
    # Category management
    async def create_category(
        self,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None
    ) -> Optional[MaterialCategoryInfo]:
        """Create material category"""
        try:
            payload = {
                "name": name,
                "description": description,
                "parent_id": parent_id,
                "color": color,
                "icon": icon
            }
            
            response = await self._post("/api/v1/categories", json=payload)
            
            if response:
                return self._parse_category(response)
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return None
    
    async def get_categories(self, include_children: bool = True) -> List[MaterialCategoryInfo]:
        """Get all categories"""
        try:
            params = {"include_children": include_children}
            response = await self._get("/api/v1/categories", params=params)
            
            if response and "categories" in response:
                return [self._parse_category(cat_data) for cat_data in response["categories"]]
            return []
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    # File management
    async def upload_file(
        self,
        material_id: int,
        file_data: bytes,
        filename: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        uploaded_by_user_id: Optional[int] = None
    ) -> Optional[MaterialFileInfo]:
        """Upload file for material"""
        try:
            files = {
                "file": (filename, file_data)
            }
            
            data = {}
            if title:
                data["title"] = title
            if description:
                data["description"] = description
            if uploaded_by_user_id:
                data["uploaded_by_user_id"] = uploaded_by_user_id
            
            response = await self._post_files(
                f"/api/v1/materials/{material_id}/files",
                files=files,
                data=data
            )
            
            if response:
                return self._parse_file(response)
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None
    
    async def get_material_files(self, material_id: int) -> List[MaterialFileInfo]:
        """Get files for material"""
        try:
            response = await self._get(f"/api/v1/materials/{material_id}/files")
            
            if response and "files" in response:
                return [self._parse_file(file_data) for file_data in response["files"]]
            return []
        except Exception as e:
            logger.error(f"Error getting material files: {e}")
            return []
    
    async def download_file(self, file_id: int, user_id: Optional[int] = None) -> Optional[bytes]:
        """Download file"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            
            response = await self._get_bytes(f"/api/v1/files/{file_id}/download", params=params)
            return response
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    async def delete_file(self, file_id: int) -> bool:
        """Delete file"""
        try:
            response = await self._delete(f"/api/v1/files/{file_id}")
            return response is not None
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def _parse_material(self, data: Dict[str, Any]) -> MaterialInfo:
        """Parse material data from API response"""
        return MaterialInfo(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            link=data.get("link"),
            grade=data["grade"],
            subject=data.get("subject"),
            topic=data.get("topic"),
            material_type=data["material_type"],
            tags=data.get("tags", []),
            difficulty_level=data.get("difficulty_level"),
            estimated_time=data.get("estimated_time"),
            view_count=data["view_count"],
            download_count=data["download_count"],
            average_rating=data["average_rating"],
            is_featured=data["is_featured"],
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')),
            created_by_user_id=data.get("created_by_user_id"),
            category=data.get("category"),
            files=data.get("files", [])
        )
    
    def _parse_category(self, data: Dict[str, Any]) -> MaterialCategoryInfo:
        """Parse category data from API response"""
        children = []
        if data.get("children"):
            children = [self._parse_category(child) for child in data["children"]]
        
        return MaterialCategoryInfo(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            color=data.get("color"),
            icon=data.get("icon"),
            sort_order=data["sort_order"],
            is_active=data["is_active"],
            parent_id=data.get("parent_id"),
            children=children
        )
    
    def _parse_file(self, data: Dict[str, Any]) -> MaterialFileInfo:
        """Parse file data from API response"""
        return MaterialFileInfo(
            id=data["id"],
            filename=data["filename"],
            original_filename=data["original_filename"],
            file_url=data.get("file_url"),
            file_type=data["file_type"],
            file_size=data["file_size"],
            title=data.get("title"),
            description=data.get("description"),
            is_primary=data["is_primary"],
            is_downloadable=data["is_downloadable"],
            access_count=data["access_count"],
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        )