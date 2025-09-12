# -*- coding: utf-8 -*-
"""
Advanced File Processing Service
Handles thumbnails, previews, video processing, and file analysis
"""

import os
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageOps, ImageDraw, ImageFont
import magic
import json
from datetime import datetime

from ..core.config import settings
from ..models.material import FileType

logger = logging.getLogger(__name__)


class FileProcessor:
    """Advanced file processing for materials"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.thumbnails_dir = self.upload_dir / "thumbnails"
        self.previews_dir = self.upload_dir / "previews"
        self.temp_dir = self.upload_dir / "temp"
        
        # Image processing settings
        self.thumbnail_size = (150, 150)
        self.preview_size = (800, 600)
        self.quality = 85
        
        # Video processing settings
        self.video_thumbnail_time = "00:00:01"  # Extract frame at 1 second
        self.video_preview_duration = 30  # 30 second preview
    
    async def process_file(
        self,
        file_path: Path,
        file_type: FileType,
        original_filename: str
    ) -> Dict[str, Any]:
        """Process file based on type and generate metadata"""
        
        processing_result = {
            "thumbnail_path": None,
            "preview_path": None,
            "metadata": {},
            "processing_status": "completed",
            "error_message": None
        }
        
        try:
            if file_type.value in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
                result = await self._process_image(file_path, original_filename)
                processing_result.update(result)
                
            elif file_type.value in ["mp4", "avi", "mov", "wmv", "flv", "webm"]:
                result = await self._process_video(file_path, original_filename)
                processing_result.update(result)
                
            elif file_type.value in ["pdf"]:
                result = await self._process_pdf(file_path, original_filename)
                processing_result.update(result)
                
            elif file_type.value in ["docx", "doc", "odt"]:
                result = await self._process_document(file_path, original_filename)
                processing_result.update(result)
                
            elif file_type.value in ["pptx", "ppt", "odp"]:
                result = await self._process_presentation(file_path, original_filename)
                processing_result.update(result)
                
            else:
                # Generic file processing
                result = await self._process_generic_file(file_path, original_filename)
                processing_result.update(result)
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            processing_result["processing_status"] = "failed"
            processing_result["error_message"] = str(e)
        
        return processing_result
    
    async def _process_image(self, file_path: Path, filename: str) -> Dict[str, Any]:
        """Process image file - generate thumbnails and previews"""
        result = {"metadata": {}}
        
        try:
            # Open image
            with Image.open(file_path) as img:
                # Get image metadata
                result["metadata"] = {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "has_transparency": img.mode in ("RGBA", "LA") or "transparency" in img.info
                }
                
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                # Generate thumbnail
                thumbnail_path = await self._generate_image_thumbnail(img, filename)
                if thumbnail_path:
                    result["thumbnail_path"] = str(thumbnail_path)
                
                # Generate preview (resized version)
                preview_path = await self._generate_image_preview(img, filename)
                if preview_path:
                    result["preview_path"] = str(preview_path)
                
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
            raise
        
        return result
    
    async def _process_video(self, file_path: Path, filename: str) -> Dict[str, Any]:
        """Process video file - extract thumbnail and metadata"""
        result = {"metadata": {}}
        
        try:
            # Get video metadata using ffprobe
            metadata = await self._get_video_metadata(file_path)
            result["metadata"] = metadata
            
            # Extract thumbnail from video
            thumbnail_path = await self._extract_video_thumbnail(file_path, filename)
            if thumbnail_path:
                result["thumbnail_path"] = str(thumbnail_path)
            
            # Generate video preview (if enabled)
            if settings.ENABLE_VIDEO_PREVIEWS:
                preview_path = await self._generate_video_preview(file_path, filename)
                if preview_path:
                    result["preview_path"] = str(preview_path)
                    
        except Exception as e:
            logger.error(f"Error processing video {file_path}: {e}")
            raise
        
        return result
    
    async def _process_pdf(self, file_path: Path, filename: str) -> Dict[str, Any]:
        """Process PDF file - extract first page as thumbnail"""
        result = {"metadata": {}}
        
        try:
            # Extract PDF metadata
            metadata = await self._get_pdf_metadata(file_path)
            result["metadata"] = metadata
            
            # Generate thumbnail from first page
            thumbnail_path = await self._generate_pdf_thumbnail(file_path, filename)
            if thumbnail_path:
                result["thumbnail_path"] = str(thumbnail_path)
                
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            # PDF processing is optional, don't fail if libraries not available
            pass
        
        return result
    
    async def _process_document(self, file_path: Path, filename: str) -> Dict[str, Any]:
        """Process document file (Word, etc.)"""
        result = {"metadata": {}}
        
        try:
            # Extract document metadata
            metadata = await self._get_document_metadata(file_path)
            result["metadata"] = metadata
            
            # Generate generic document thumbnail
            thumbnail_path = await self._generate_document_thumbnail(filename, "document")
            if thumbnail_path:
                result["thumbnail_path"] = str(thumbnail_path)
                
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            pass
        
        return result
    
    async def _process_presentation(self, file_path: Path, filename: str) -> Dict[str, Any]:
        """Process presentation file (PowerPoint, etc.)"""
        result = {"metadata": {}}
        
        try:
            # Extract presentation metadata
            metadata = await self._get_document_metadata(file_path)
            result["metadata"] = metadata
            
            # Generate generic presentation thumbnail
            thumbnail_path = await self._generate_document_thumbnail(filename, "presentation")
            if thumbnail_path:
                result["thumbnail_path"] = str(thumbnail_path)
                
        except Exception as e:
            logger.error(f"Error processing presentation {file_path}: {e}")
            pass
        
        return result
    
    async def _process_generic_file(self, file_path: Path, filename: str) -> Dict[str, Any]:
        """Process generic file"""
        result = {"metadata": {}}
        
        try:
            # Get basic file metadata
            stat = file_path.stat()
            result["metadata"] = {
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
            # Generate generic file type thumbnail
            file_ext = file_path.suffix.lower().lstrip('.')
            thumbnail_path = await self._generate_document_thumbnail(filename, file_ext or "file")
            if thumbnail_path:
                result["thumbnail_path"] = str(thumbnail_path)
                
        except Exception as e:
            logger.error(f"Error processing generic file {file_path}: {e}")
            pass
        
        return result
    
    async def _generate_image_thumbnail(self, img: Image.Image, filename: str) -> Optional[Path]:
        """Generate thumbnail for image"""
        try:
            # Create thumbnail
            img_copy = img.copy()
            img_copy.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
            
            # Generate filename
            name = Path(filename).stem
            thumbnail_filename = f"{name}_thumb.jpg"
            thumbnail_path = self.thumbnails_dir / thumbnail_filename
            
            # Save thumbnail
            img_copy.save(thumbnail_path, "JPEG", quality=self.quality, optimize=True)
            
            return thumbnail_path.relative_to(self.upload_dir)
            
        except Exception as e:
            logger.error(f"Error generating image thumbnail: {e}")
            return None
    
    async def _generate_image_preview(self, img: Image.Image, filename: str) -> Optional[Path]:
        """Generate preview for image"""
        try:
            # Only generate preview if image is larger than preview size
            if img.width <= self.preview_size[0] and img.height <= self.preview_size[1]:
                return None
            
            # Resize image
            img_copy = img.copy()
            img_copy.thumbnail(self.preview_size, Image.Resampling.LANCZOS)
            
            # Generate filename
            name = Path(filename).stem
            preview_filename = f"{name}_preview.jpg"
            preview_path = self.previews_dir / preview_filename
            
            # Save preview
            img_copy.save(preview_path, "JPEG", quality=self.quality, optimize=True)
            
            return preview_path.relative_to(self.upload_dir)
            
        except Exception as e:
            logger.error(f"Error generating image preview: {e}")
            return None
    
    async def _extract_video_thumbnail(self, file_path: Path, filename: str) -> Optional[Path]:
        """Extract thumbnail from video using ffmpeg"""
        try:
            name = Path(filename).stem
            thumbnail_filename = f"{name}_thumb.jpg"
            thumbnail_path = self.thumbnails_dir / thumbnail_filename
            
            # Use ffmpeg to extract frame
            cmd = [
                "ffmpeg",
                "-i", str(file_path),
                "-ss", self.video_thumbnail_time,
                "-vframes", "1",
                "-vf", f"scale={self.thumbnail_size[0]}:{self.thumbnail_size[1]}:force_original_aspect_ratio=decrease,pad={self.thumbnail_size[0]}:{self.thumbnail_size[1]}:(ow-iw)/2:(oh-ih)/2",
                "-y",  # Overwrite output
                str(thumbnail_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and thumbnail_path.exists():
                return thumbnail_path.relative_to(self.upload_dir)
            else:
                logger.warning(f"ffmpeg failed for {file_path}: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting video thumbnail: {e}")
            return None
    
    async def _get_video_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get video metadata using ffprobe"""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(file_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                metadata = json.loads(stdout.decode())
                
                # Extract useful information
                format_info = metadata.get("format", {})
                video_stream = next(
                    (s for s in metadata.get("streams", []) if s.get("codec_type") == "video"),
                    {}
                )
                
                return {
                    "duration": float(format_info.get("duration", 0)),
                    "bitrate": int(format_info.get("bit_rate", 0)),
                    "size": int(format_info.get("size", 0)),
                    "width": int(video_stream.get("width", 0)),
                    "height": int(video_stream.get("height", 0)),
                    "codec": video_stream.get("codec_name", "unknown"),
                    "fps": eval(video_stream.get("r_frame_rate", "0/1")) if "/" in video_stream.get("r_frame_rate", "") else 0
                }
            else:
                logger.warning(f"ffprobe failed for {file_path}: {stderr.decode()}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting video metadata: {e}")
            return {}
    
    async def _generate_video_preview(self, file_path: Path, filename: str) -> Optional[Path]:
        """Generate video preview (short clip)"""
        try:
            name = Path(filename).stem
            preview_filename = f"{name}_preview.mp4"
            preview_path = self.previews_dir / preview_filename
            
            # Create short preview clip
            cmd = [
                "ffmpeg",
                "-i", str(file_path),
                "-t", str(self.video_preview_duration),
                "-vf", "scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-crf", "28",
                "-c:a", "aac",
                "-b:a", "64k",
                "-y",
                str(preview_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and preview_path.exists():
                return preview_path.relative_to(self.upload_dir)
            else:
                logger.warning(f"Video preview generation failed for {file_path}: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating video preview: {e}")
            return None
    
    async def _get_pdf_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get PDF metadata (requires PyPDF2 or similar)"""
        try:
            # This would require PyPDF2 or pdfplumber
            # For now, return basic metadata
            stat = file_path.stat()
            return {
                "size": stat.st_size,
                "pages": "unknown",  # Would extract with PDF library
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting PDF metadata: {e}")
            return {}
    
    async def _generate_pdf_thumbnail(self, file_path: Path, filename: str) -> Optional[Path]:
        """Generate thumbnail from PDF first page"""
        try:
            # This would require pdf2image or similar
            # For now, generate a generic PDF thumbnail
            return await self._generate_document_thumbnail(filename, "pdf")
        except Exception as e:
            logger.error(f"Error generating PDF thumbnail: {e}")
            return None
    
    async def _get_document_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get document metadata"""
        try:
            stat = file_path.stat()
            return {
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting document metadata: {e}")
            return {}
    
    async def _generate_document_thumbnail(self, filename: str, doc_type: str) -> Optional[Path]:
        """Generate generic document thumbnail with file type icon"""
        try:
            # Create thumbnail with file type text
            img = Image.new("RGB", self.thumbnail_size, color="white")
            draw = ImageDraw.Draw(img)
            
            # Try to load font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 20)
                small_font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Draw file type
            doc_type_upper = doc_type.upper()
            bbox = draw.textbbox((0, 0), doc_type_upper, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (self.thumbnail_size[0] - text_width) // 2
            y = (self.thumbnail_size[1] - text_height) // 2 - 10
            
            draw.text((x, y), doc_type_upper, fill="black", font=font)
            
            # Draw filename (truncated)
            name = Path(filename).stem
            if len(name) > 15:
                name = name[:12] + "..."
            
            bbox = draw.textbbox((0, 0), name, font=small_font)
            text_width = bbox[2] - bbox[0]
            x = (self.thumbnail_size[0] - text_width) // 2
            y = y + text_height + 10
            
            draw.text((x, y), name, fill="gray", font=small_font)
            
            # Add border
            draw.rectangle([0, 0, self.thumbnail_size[0]-1, self.thumbnail_size[1]-1], outline="gray")
            
            # Save thumbnail
            name = Path(filename).stem
            thumbnail_filename = f"{name}_thumb.jpg"
            thumbnail_path = self.thumbnails_dir / thumbnail_filename
            
            img.save(thumbnail_path, "JPEG", quality=self.quality)
            
            return thumbnail_path.relative_to(self.upload_dir)
            
        except Exception as e:
            logger.error(f"Error generating document thumbnail: {e}")
            return None
    
    async def cleanup(self):
        """Cleanup temporary files"""
        try:
            if self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
                logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}")


class SearchIndexer:
    """Text search indexing for materials"""
    
    def __init__(self):
        self.index_dir = Path(settings.UPLOAD_DIR) / "search_index"
    
    async def extract_text_from_file(self, file_path: Path, file_type: FileType) -> str:
        """Extract searchable text from file"""
        try:
            if file_type.value == "pdf":
                return await self._extract_text_from_pdf(file_path)
            elif file_type.value in ["docx", "doc"]:
                return await self._extract_text_from_document(file_path)
            elif file_type.value == "txt":
                return await self._extract_text_from_txt(file_path)
            else:
                return ""
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return ""
    
    async def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF (requires PyPDF2 or pdfplumber)"""
        # Placeholder - would implement with actual PDF library
        return ""
    
    async def _extract_text_from_document(self, file_path: Path) -> str:
        """Extract text from Word document (requires python-docx)"""
        # Placeholder - would implement with actual document library
        return ""
    
    async def _extract_text_from_txt(self, file_path: Path) -> str:
        """Extract text from plain text file"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return ""
    
    async def index_material_content(self, material_id: int, content: str):
        """Index material content for search"""
        # Placeholder for full-text search implementation
        # Could use Elasticsearch, Whoosh, or similar
        pass