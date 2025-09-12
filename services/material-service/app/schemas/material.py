# -*- coding: utf-8 -*-
"""
Material Service Schemas
Pydantic models for request/response validation
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator, ConfigDict, HttpUrl

from ..models.material import MaterialType, FileType, AccessLevel


# Base schemas
class MaterialCategoryBase(BaseModel):
    """Base category schema"""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class MaterialCategoryCreate(MaterialCategoryBase):
    """Schema for creating category"""
    pass


class MaterialCategoryUpdate(BaseModel):
    """Schema for updating category"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MaterialCategoryResponse(MaterialCategoryBase):
    """Schema for category response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
    children: List['MaterialCategoryResponse'] = []


class MaterialBase(BaseModel):
    """Base material schema"""
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    link: Optional[HttpUrl] = None
    material_type: MaterialType = Field(default=MaterialType.OTHER)
    grade: int = Field(..., ge=1, le=11)
    subject: Optional[str] = Field(None, max_length=100)
    topic: Optional[str] = Field(None, max_length=200)
    access_level: AccessLevel = Field(default=AccessLevel.PUBLIC)
    tags: Optional[List[str]] = []
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    estimated_time: Optional[int] = Field(None, ge=1)  # minutes
    language: str = Field(default="ru", max_length=10)
    category_id: Optional[int] = None
    is_featured: bool = Field(default=False)

    @validator('grade')
    def validate_grade(cls, v):
        """Validate grade range"""
        if v < 1 or v > 11:
            raise ValueError('Grade must be between 1 and 11')
        return v

    @validator('tags', pre=True)
    def validate_tags(cls, v):
        """Convert tags to list if needed"""
        if isinstance(v, str):
            # Parse JSON string or comma-separated
            import json
            try:
                return json.loads(v)
            except:
                return [tag.strip() for tag in v.split(',') if tag.strip()]
        return v or []


class MaterialCreate(MaterialBase):
    """Schema for creating material"""
    created_by_user_id: Optional[int] = None


class MaterialUpdate(BaseModel):
    """Schema for updating material"""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    link: Optional[HttpUrl] = None
    material_type: Optional[MaterialType] = None
    grade: Optional[int] = Field(None, ge=1, le=11)
    subject: Optional[str] = Field(None, max_length=100)
    topic: Optional[str] = Field(None, max_length=200)
    access_level: Optional[AccessLevel] = None
    tags: Optional[List[str]] = None
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    estimated_time: Optional[int] = Field(None, ge=1)
    language: Optional[str] = Field(None, max_length=10)
    category_id: Optional[int] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


class MaterialFileBase(BaseModel):
    """Base material file schema"""
    filename: str = Field(..., max_length=255)
    original_filename: str = Field(..., max_length=255)
    file_type: FileType
    file_size: int = Field(..., ge=0)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_primary: bool = Field(default=False)
    is_downloadable: bool = Field(default=True)


class MaterialFileCreate(MaterialFileBase):
    """Schema for creating material file"""
    material_id: int
    uploaded_by_user_id: Optional[int] = None


class MaterialFileResponse(MaterialFileBase):
    """Schema for material file response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    file_path: str
    file_url: Optional[str] = None
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    thumbnail_path: Optional[str] = None
    preview_path: Optional[str] = None
    has_preview: bool
    access_count: int
    sort_order: int
    is_active: bool
    upload_completed: bool
    processing_status: str
    created_at: datetime
    updated_at: datetime


class MaterialResponse(MaterialBase):
    """Schema for material response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    view_count: int
    download_count: int
    rating_sum: int
    rating_count: int
    average_rating: float = 0.0
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[int] = None
    category: Optional[MaterialCategoryResponse] = None
    files: List[MaterialFileResponse] = []

    @validator('average_rating')
    def calculate_average_rating(cls, v, values):
        """Calculate average rating"""
        if 'rating_count' in values and values['rating_count'] > 0:
            return round(values['rating_sum'] / values['rating_count'], 1)
        return 0.0


class MaterialReviewBase(BaseModel):
    """Base review schema"""
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None
    is_anonymous: bool = Field(default=False)


class MaterialReviewCreate(MaterialReviewBase):
    """Schema for creating review"""
    material_id: int
    user_id: int


class MaterialReviewResponse(MaterialReviewBase):
    """Schema for review response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    material_id: int
    user_id: int
    is_verified: bool
    helpful_count: int
    is_approved: bool
    is_flagged: bool
    created_at: datetime
    updated_at: datetime


# List and pagination schemas
class MaterialListResponse(BaseModel):
    """Schema for paginated material list"""
    materials: List[MaterialResponse]
    total: int
    page: int
    per_page: int
    pages: int
    filters: Dict[str, Any] = {}


class MaterialCategoryListResponse(BaseModel):
    """Schema for category list"""
    categories: List[MaterialCategoryResponse]
    total: int


class MaterialFileListResponse(BaseModel):
    """Schema for file list"""
    files: List[MaterialFileResponse]
    total: int
    material_id: int


# Search and filter schemas
class MaterialSearchRequest(BaseModel):
    """Schema for material search"""
    query: Optional[str] = Field(None, description="Search query")
    grade: Optional[int] = Field(None, ge=1, le=11)
    material_type: Optional[MaterialType] = None
    subject: Optional[str] = None
    category_id: Optional[int] = None
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    tags: Optional[List[str]] = []
    is_featured: Optional[bool] = None
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    created_by_user_id: Optional[int] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", regex="^(asc|desc)$")


class MaterialStatsResponse(BaseModel):
    """Schema for material statistics"""
    total_materials: int
    total_files: int
    total_downloads: int
    total_views: int
    materials_by_grade: Dict[int, int]
    materials_by_type: Dict[str, int]
    materials_by_subject: Dict[str, int]
    popular_materials: List[MaterialResponse]
    recent_materials: List[MaterialResponse]


# File upload schemas
class FileUploadResponse(BaseModel):
    """Schema for file upload response"""
    file_id: int
    filename: str
    file_url: str
    file_size: int
    upload_status: str
    message: str


class BatchFileUploadResponse(BaseModel):
    """Schema for batch file upload response"""
    uploaded_files: List[FileUploadResponse]
    failed_uploads: List[Dict[str, str]]
    total_uploaded: int
    total_failed: int


# Compatibility schemas (for migration from existing system)
class LegacyMaterialResponse(BaseModel):
    """Legacy material format for compatibility"""
    id: int
    title: str
    link: Optional[str] = None
    description: Optional[str] = None
    grade: int
    created_at: datetime


# Health check schema
class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    database_status: str
    storage_status: str
    files_count: int


# Update MaterialCategoryResponse to handle self-reference
MaterialCategoryResponse.model_rebuild()