# -*- coding: utf-8 -*-
"""
File Service Business Logic
File upload, management, and processing for materials
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple, BinaryIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from fastapi import UploadFile, HTTPException

from ..models.material import MaterialFile, Material, MaterialAccess
from ..schemas.material import (
    MaterialFileCreate, MaterialFileResponse,
    FileUploadResponse, BatchFileUploadResponse
)
from ..database.connection import db_manager
from ..storage.file_storage import (
    FileStorageManager, get_file_type_from_extension,
    validate_file_type, get_mime_type
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class FileService:
    """Service for file management"""
    
    def __init__(self):
        self.storage = FileStorageManager()
    
    async def upload_file(
        self,
        material_id: int,
        upload_file: UploadFile,
        title: Optional[str] = None,
        description: Optional[str] = None,
        uploaded_by_user_id: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> MaterialFileResponse:
        """Upload file for material"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Validate file
            await self._validate_upload_file(upload_file)
            
            # Check if material exists
            material_result = await session.execute(
                select(Material).where(Material.id == material_id)
            )
            material = material_result.scalar_one_or_none()
            if not material:
                raise HTTPException(status_code=404, detail="Material not found")
            
            # Read file data
            file_data = await upload_file.read()
            
            # Store file
            file_path, filename, checksum, file_size = await self.storage.store_file(
                file_data, upload_file.filename
            )
            
            # Determine file type
            file_type = get_file_type_from_extension(upload_file.filename)
            mime_type = get_mime_type(upload_file.filename)
            
            # Create file record
            material_file = MaterialFile(
                material_id=material_id,
                filename=filename,
                original_filename=upload_file.filename,
                file_path=file_path,
                file_type=file_type,
                mime_type=mime_type,
                file_size=file_size,
                checksum=checksum,
                title=title or upload_file.filename,
                description=description,
                uploaded_by_user_id=uploaded_by_user_id,
                upload_completed=True,
                processing_status="completed"
            )
            
            session.add(material_file)
            await session.flush()
            
            # Generate thumbnail and preview for images
            if file_type.value in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                try:
                    thumbnail_path = await self.storage.generate_thumbnail(file_path)
                    if thumbnail_path:
                        material_file.thumbnail_path = thumbnail_path
                    
                    preview_path = await self.storage.generate_preview(file_path)
                    if preview_path:
                        material_file.preview_path = preview_path
                        material_file.has_preview = True
                except Exception as e:
                    logger.warning(f"Failed to generate thumbnail/preview: {e}")
            
            # Set as primary if it's the first file
            file_count_result = await session.execute(
                select(func.count(MaterialFile.id))
                .where(MaterialFile.material_id == material_id)
            )
            if file_count_result.scalar() == 1:
                material_file.is_primary = True
            
            # Generate file URL
            material_file.file_url = f"/files/{file_path}"
            
            await session.commit()
            
            logger.info(f"File uploaded: {material_file.id} - {upload_file.filename}")
            
            return MaterialFileResponse.model_validate(material_file)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error uploading file: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def batch_upload_files(
        self,
        material_id: int,
        upload_files: List[UploadFile],
        uploaded_by_user_id: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> BatchFileUploadResponse:
        """Upload multiple files for material"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            uploaded_files = []
            failed_uploads = []
            
            for upload_file in upload_files:
                try:
                    file_response = await self.upload_file(
                        material_id=material_id,
                        upload_file=upload_file,
                        uploaded_by_user_id=uploaded_by_user_id,
                        session=session
                    )
                    
                    uploaded_files.append(FileUploadResponse(
                        file_id=file_response.id,
                        filename=file_response.original_filename,
                        file_url=file_response.file_url,
                        file_size=file_response.file_size,
                        upload_status="success",
                        message="File uploaded successfully"
                    ))
                    
                except Exception as e:
                    failed_uploads.append({
                        "filename": upload_file.filename,
                        "error": str(e)
                    })
                    logger.error(f"Failed to upload {upload_file.filename}: {e}")
            
            return BatchFileUploadResponse(
                uploaded_files=uploaded_files,
                failed_uploads=failed_uploads,
                total_uploaded=len(uploaded_files),
                total_failed=len(failed_uploads)
            )
            
        finally:
            if should_close:
                await session.close()
    
    async def get_file(
        self,
        file_id: int,
        session: Optional[AsyncSession] = None
    ) -> Optional[MaterialFileResponse]:
        """Get file by ID"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            result = await session.execute(
                select(MaterialFile).where(MaterialFile.id == file_id)
            )
            file = result.scalar_one_or_none()
            
            return MaterialFileResponse.model_validate(file) if file else None
            
        finally:
            if should_close:
                await session.close()
    
    async def get_material_files(
        self,
        material_id: int,
        session: Optional[AsyncSession] = None
    ) -> List[MaterialFileResponse]:
        """Get all files for material"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            result = await session.execute(
                select(MaterialFile)
                .where(
                    and_(
                        MaterialFile.material_id == material_id,
                        MaterialFile.is_active == True
                    )
                )
                .order_by(MaterialFile.sort_order, MaterialFile.created_at)
            )
            files = result.scalars().all()
            
            return [MaterialFileResponse.model_validate(f) for f in files]
            
        finally:
            if should_close:
                await session.close()
    
    async def delete_file(
        self,
        file_id: int,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """Delete file"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            result = await session.execute(
                select(MaterialFile).where(MaterialFile.id == file_id)
            )
            file = result.scalar_one_or_none()
            
            if not file:
                return False
            
            # Delete from storage
            await self.storage.delete_file(file.file_path)
            
            # Delete record
            await session.delete(file)
            await session.commit()
            
            logger.info(f"File deleted: {file_id}")
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting file: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def download_file(
        self,
        file_id: int,
        user_id: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> Tuple[str, str, str]:
        """
        Get file download info and log access
        Returns: (file_path, filename, mime_type)
        """
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            result = await session.execute(
                select(MaterialFile, Material)
                .join(Material, MaterialFile.material_id == Material.id)
                .where(MaterialFile.id == file_id)
            )
            row = result.first()
            
            if not row:
                raise HTTPException(status_code=404, detail="File not found")
            
            file, material = row
            
            # Check if file exists in storage
            file_path = await self.storage.get_file_path(file.file_path)
            if not await self.storage.file_exists(file.file_path):
                raise HTTPException(status_code=404, detail="File not found in storage")
            
            # Increment download counts
            file.access_count += 1
            material.download_count += 1
            
            # Log access if enabled
            if settings.ENABLE_DOWNLOAD_TRACKING:
                access_log = MaterialAccess(
                    material_id=material.id,
                    file_id=file.id,
                    user_id=user_id,
                    access_type="download",
                    accessed_at=datetime.utcnow()
                )
                session.add(access_log)
            
            await session.commit()
            
            return str(file_path), file.original_filename, file.mime_type or "application/octet-stream"
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error downloading file: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def update_file(
        self,
        file_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        is_primary: Optional[bool] = None,
        sort_order: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> Optional[MaterialFileResponse]:
        """Update file metadata"""
        if session is None:
            session = await db_manager.get_session()
            should_close = True
        else:
            should_close = False
        
        try:
            result = await session.execute(
                select(MaterialFile).where(MaterialFile.id == file_id)
            )
            file = result.scalar_one_or_none()
            
            if not file:
                return None
            
            # Update fields
            if title is not None:
                file.title = title
            if description is not None:
                file.description = description
            if is_primary is not None:
                # If setting as primary, unset other primary files for the same material
                if is_primary:
                    await session.execute(
                        MaterialFile.__table__.update()
                        .where(MaterialFile.material_id == file.material_id)
                        .values(is_primary=False)
                    )
                file.is_primary = is_primary
            if sort_order is not None:
                file.sort_order = sort_order
            
            file.updated_at = datetime.utcnow()
            await session.commit()
            
            return MaterialFileResponse.model_validate(file)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating file: {e}")
            raise
        finally:
            if should_close:
                await session.close()
    
    async def _validate_upload_file(self, upload_file: UploadFile):
        """Validate uploaded file"""
        # Check file size
        if upload_file.size and upload_file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes"
            )
        
        # Check file type
        if not validate_file_type(upload_file.filename):
            raise HTTPException(
                status_code=422,
                detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}"
            )
        
        # Check filename
        if not upload_file.filename or upload_file.filename.strip() == "":
            raise HTTPException(status_code=422, detail="Invalid filename")
        
        return True
    
    async def get_file_stats(self) -> dict:
        """Get file statistics"""
        async with db_manager.session_maker() as session:
            # Total files count
            total_files_result = await session.execute(
                select(func.count(MaterialFile.id))
                .where(MaterialFile.is_active == True)
            )
            total_files = total_files_result.scalar()
            
            # Total storage size
            total_size_result = await session.execute(
                select(func.sum(MaterialFile.file_size))
                .where(MaterialFile.is_active == True)
            )
            total_size = total_size_result.scalar() or 0
            
            # Files by type
            type_stats_result = await session.execute(
                select(MaterialFile.file_type, func.count(MaterialFile.id))
                .where(MaterialFile.is_active == True)
                .group_by(MaterialFile.file_type)
            )
            files_by_type = {row[0].value: row[1] for row in type_stats_result.fetchall()}
            
            # Storage stats
            storage_stats = await self.storage.get_storage_stats()
            
            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "files_by_type": files_by_type,
                "storage_stats": storage_stats
            }