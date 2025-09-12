# -*- coding: utf-8 -*-
"""
Material Service API Endpoints
RESTful API for materials library and file management
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...services.material_service import MaterialService
from ...services.file_service import FileService
from ...schemas.material import (
    MaterialCreate, MaterialUpdate, MaterialResponse,
    MaterialListResponse, MaterialSearchRequest, MaterialStatsResponse,
    MaterialCategoryCreate, MaterialCategoryResponse, MaterialCategoryListResponse,
    MaterialFileResponse, FileUploadResponse, BatchFileUploadResponse,
    MaterialFileListResponse, LegacyMaterialResponse, HealthResponse
)
from ...models.material import MaterialType, AccessLevel
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
material_service = MaterialService()
file_service = FileService()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Extended health check with database and storage status"""
    try:
        # Test database connection
        await db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    try:
        # Test storage
        storage_stats = await file_service.get_file_stats()
        storage_status = "healthy"
        files_count = storage_stats.get("total_files", 0)
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        storage_status = "unhealthy"
        files_count = -1
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" and storage_status == "healthy" else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        database_status=db_status,
        storage_status=storage_status,
        files_count=files_count
    )


# Material endpoints
@router.post("/materials", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    material_data: MaterialCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new material"""
    try:
        return await material_service.create_material(material_data, db)
    except Exception as e:
        logger.error(f"Error creating material: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/materials/{material_id}", response_model=MaterialResponse)
async def get_material(material_id: int):
    """Get material by ID"""
    material = await material_service.get_material(material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


@router.put("/materials/{material_id}", response_model=MaterialResponse)
async def update_material(material_id: int, material_update: MaterialUpdate):
    """Update material"""
    material = await material_service.update_material(material_id, material_update)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(material_id: int):
    """Delete material"""
    success = await material_service.delete_material(material_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")


@router.get("/materials", response_model=MaterialListResponse)
async def search_materials(
    query: Optional[str] = Query(None, description="Search query"),
    grade: Optional[int] = Query(None, ge=1, le=11, description="Filter by grade"),
    material_type: Optional[MaterialType] = Query(None, description="Filter by material type"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    difficulty_level: Optional[int] = Query(None, ge=1, le=5, description="Filter by difficulty level"),
    is_featured: Optional[bool] = Query(None, description="Filter featured materials"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating filter"),
    created_by_user_id: Optional[int] = Query(None, description="Filter by creator"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """Search materials with filtering and pagination"""
    try:
        search_request = MaterialSearchRequest(
            query=query,
            grade=grade,
            material_type=material_type,
            subject=subject,
            category_id=category_id,
            difficulty_level=difficulty_level,
            is_featured=is_featured,
            min_rating=min_rating,
            created_by_user_id=created_by_user_id,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        materials, total = await material_service.search_materials(search_request)
        
        return MaterialListResponse(
            materials=materials,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page,
            filters={
                "query": query,
                "grade": grade,
                "material_type": material_type.value if material_type else None,
                "subject": subject,
                "category_id": category_id,
                "difficulty_level": difficulty_level,
                "is_featured": is_featured,
                "min_rating": min_rating,
                "created_by_user_id": created_by_user_id
            }
        )
    except Exception as e:
        logger.error(f"Error searching materials: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/materials/grade/{grade}")
async def get_materials_by_grade(grade: int):
    """Get materials by grade (compatibility endpoint)"""
    if grade < 1 or grade > 11:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade must be between 1 and 11")
    
    try:
        materials = await material_service.get_materials_by_grade(grade)
        # Convert to legacy format for compatibility
        legacy_materials = []
        for material in materials:
            legacy_materials.append(LegacyMaterialResponse(
                id=material.id,
                title=material.title,
                link=material.link,
                description=material.description,
                grade=material.grade,
                created_at=material.created_at
            ))
        return legacy_materials
    except Exception as e:
        logger.error(f"Error getting materials by grade: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/materials/{material_id}/view")
async def increment_view_count(
    material_id: int,
    user_id: Optional[int] = Query(None, description="User ID (if logged in)")
):
    """Increment material view count"""
    try:
        await material_service.increment_view_count(material_id, user_id)
        return {"message": "View count incremented"}
    except Exception as e:
        logger.error(f"Error incrementing view count: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/materials/stats", response_model=MaterialStatsResponse)
async def get_material_stats():
    """Get material statistics"""
    try:
        return await material_service.get_material_stats()
    except Exception as e:
        logger.error(f"Error getting material stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# Category endpoints
@router.post("/categories", response_model=MaterialCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(category_data: MaterialCategoryCreate):
    """Create material category"""
    try:
        return await material_service.create_category(category_data)
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/categories", response_model=MaterialCategoryListResponse)
async def get_categories(include_children: bool = Query(True, description="Include child categories")):
    """Get all categories"""
    try:
        categories = await material_service.get_categories(include_children)
        return MaterialCategoryListResponse(
            categories=categories,
            total=len(categories)
        )
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# File management endpoints
@router.post("/materials/{material_id}/files", response_model=MaterialFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    material_id: int,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    uploaded_by_user_id: Optional[int] = Form(None)
):
    """Upload file for material"""
    try:
        return await file_service.upload_file(
            material_id=material_id,
            upload_file=file,
            title=title,
            description=description,
            uploaded_by_user_id=uploaded_by_user_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/materials/{material_id}/files/batch", response_model=BatchFileUploadResponse)
async def batch_upload_files(
    material_id: int,
    files: List[UploadFile] = File(...),
    uploaded_by_user_id: Optional[int] = Form(None)
):
    """Upload multiple files for material"""
    try:
        return await file_service.batch_upload_files(
            material_id=material_id,
            upload_files=files,
            uploaded_by_user_id=uploaded_by_user_id
        )
    except Exception as e:
        logger.error(f"Error batch uploading files: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/materials/{material_id}/files", response_model=MaterialFileListResponse)
async def get_material_files(material_id: int):
    """Get files for material"""
    try:
        files = await file_service.get_material_files(material_id)
        return MaterialFileListResponse(
            files=files,
            total=len(files),
            material_id=material_id
        )
    except Exception as e:
        logger.error(f"Error getting material files: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/files/{file_id}", response_model=MaterialFileResponse)
async def get_file(file_id: int):
    """Get file information"""
    file = await file_service.get_file(file_id)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    user_id: Optional[int] = Query(None, description="User ID (for tracking)")
):
    """Download file"""
    try:
        file_path, filename, mime_type = await file_service.download_file(file_id, user_id)
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=mime_type
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/files/{file_id}", response_model=MaterialFileResponse)
async def update_file(
    file_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    is_primary: Optional[bool] = None,
    sort_order: Optional[int] = None
):
    """Update file metadata"""
    try:
        file = await file_service.update_file(
            file_id=file_id,
            title=title,
            description=description,
            is_primary=is_primary,
            sort_order=sort_order
        )
        if not file:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return file
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating file: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: int):
    """Delete file"""
    try:
        success = await file_service.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# Admin endpoints
@router.get("/admin/stats")
async def get_admin_stats():
    """Get comprehensive statistics (admin function)"""
    try:
        material_stats = await material_service.get_material_stats()
        file_stats = await file_service.get_file_stats()
        
        return {
            "materials": material_stats,
            "files": file_stats
        }
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")