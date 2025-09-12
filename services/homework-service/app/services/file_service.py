# -*- coding: utf-8 -*-
"""
File Service для управления файлами домашних заданий.
Реализует загрузку, обработку, сжатие и безопасность файлов.
"""

import os
import uuid
import hashlib
import logging
import mimetypes
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import aiofiles
from PIL import Image
import io

from ..config.settings import get_settings
from ..models.homework import HomeworkFile, SubmissionFile, FileType

logger = logging.getLogger(__name__)
settings = get_settings()

# Разрешенные типы файлов
ALLOWED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'
}

ALLOWED_DOCUMENT_TYPES = {
    'application/pdf', 'application/msword', 
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain', 'text/rtf'
}

ALLOWED_VIDEO_TYPES = {
    'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo'
}

ALLOWED_AUDIO_TYPES = {
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4'
}

ALL_ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_DOCUMENT_TYPES | ALLOWED_VIDEO_TYPES | ALLOWED_AUDIO_TYPES

# Максимальные размеры файлов (в байтах)
MAX_FILE_SIZES = {
    FileType.IMAGE: 10 * 1024 * 1024,      # 10MB
    FileType.DOCUMENT: 50 * 1024 * 1024,   # 50MB
    FileType.VIDEO: 100 * 1024 * 1024,     # 100MB
    FileType.AUDIO: 25 * 1024 * 1024,      # 25MB
    FileType.OTHER: 10 * 1024 * 1024,      # 10MB
}


class FileService:
    """Сервис для управления файлами."""
    
    def __init__(self):
        self.storage_path = Path(settings.FILE_STORAGE_PATH)
        self.thumbnail_path = self.storage_path / "thumbnails"
        self.compressed_path = self.storage_path / "compressed"
    
    async def initialize(self):
        """Инициализация файлового сервиса."""
        try:
            # Создание директорий
            self.storage_path.mkdir(exist_ok=True)
            self.thumbnail_path.mkdir(exist_ok=True)
            self.compressed_path.mkdir(exist_ok=True)
            
            # Создание поддиректорий по типам файлов
            for file_type in FileType:
                (self.storage_path / file_type.value).mkdir(exist_ok=True)
                (self.thumbnail_path / file_type.value).mkdir(exist_ok=True)
                (self.compressed_path / file_type.value).mkdir(exist_ok=True)
            
            logger.info("File service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize file service: {e}")
            raise
    
    async def cleanup(self):
        """Очистка временных файлов."""
        try:
            # Удаление файлов старше 30 дней в temp директории
            temp_path = self.storage_path / "temp"
            if temp_path.exists():
                import time
                current_time = time.time()
                
                for file_path in temp_path.iterdir():
                    if file_path.is_file():
                        file_age = current_time - file_path.stat().st_mtime
                        if file_age > 30 * 24 * 3600:  # 30 дней
                            file_path.unlink()
            
            logger.info("File cleanup completed")
            
        except Exception as e:
            logger.error(f"File cleanup error: {e}")
    
    def get_file_type(self, mime_type: str) -> FileType:
        """Определение типа файла по MIME type."""
        if mime_type in ALLOWED_IMAGE_TYPES:
            return FileType.IMAGE
        elif mime_type in ALLOWED_DOCUMENT_TYPES:
            return FileType.DOCUMENT
        elif mime_type in ALLOWED_VIDEO_TYPES:
            return FileType.VIDEO
        elif mime_type in ALLOWED_AUDIO_TYPES:
            return FileType.AUDIO
        else:
            return FileType.OTHER
    
    def validate_file(self, file_data: bytes, filename: str, mime_type: str) -> Tuple[bool, str]:
        """Валидация файла перед сохранением."""
        # Проверка MIME type
        if mime_type not in ALL_ALLOWED_TYPES:
            return False, f"File type {mime_type} is not allowed"
        
        # Проверка размера
        file_type = self.get_file_type(mime_type)
        max_size = MAX_FILE_SIZES.get(file_type, settings.MAX_FILE_SIZE_MB * 1024 * 1024)
        
        if len(file_data) > max_size:
            return False, f"File size exceeds maximum allowed size ({max_size} bytes)"
        
        # Проверка расширения файла
        file_ext = Path(filename).suffix.lower()
        allowed_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.webp',  # images
            '.pdf', '.doc', '.docx', '.txt', '.rtf',   # documents
            '.mp4', '.mpeg', '.mov', '.avi',           # videos
            '.mp3', '.wav', '.ogg', '.m4a'             # audio
        }
        
        if file_ext not in allowed_extensions:
            return False, f"File extension {file_ext} is not allowed"
        
        # Дополнительная проверка для изображений
        if file_type == FileType.IMAGE:
            try:
                with Image.open(io.BytesIO(file_data)) as img:
                    # Проверка максимального разрешения
                    if img.width > 4096 or img.height > 4096:
                        return False, "Image resolution too high (max 4096x4096)"
            except Exception:
                return False, "Invalid image file"
        
        return True, "File is valid"
    
    async def save_file(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        uploaded_by: int,
        upload_source: str = "api"
    ) -> Dict[str, Any]:
        """
        Сохранение файла в файловую систему.
        
        Returns:
            Dict с информацией о сохраненном файле
        """
        try:
            # Валидация файла
            is_valid, error_message = self.validate_file(file_data, filename, mime_type)
            if not is_valid:
                raise ValueError(error_message)
            
            # Определение типа файла
            file_type = self.get_file_type(mime_type)
            
            # Генерация уникального имени файла
            file_uuid = str(uuid.uuid4())
            file_ext = Path(filename).suffix.lower()
            new_filename = f"{file_uuid}{file_ext}"
            
            # Путь для сохранения
            type_dir = self.storage_path / file_type.value
            file_path = type_dir / new_filename
            
            # Сохранение файла
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_data)
            
            # Расчет хеша файла
            file_hash = hashlib.sha256(file_data).hexdigest()
            
            # Создание миниатюры для изображений
            thumbnail_path = None
            if file_type == FileType.IMAGE:
                thumbnail_path = await self._create_thumbnail(file_path, file_type)
            
            # Сжатие для больших файлов
            compressed_path = None
            if len(file_data) > 1024 * 1024:  # Больше 1MB
                compressed_path = await self._create_compressed_version(file_path, file_type)
            
            return {
                "filename": new_filename,
                "original_filename": filename,
                "file_path": str(file_path.relative_to(self.storage_path)),
                "file_size": len(file_data),
                "file_type": file_type,
                "mime_type": mime_type,
                "file_hash": file_hash,
                "thumbnail_path": str(thumbnail_path.relative_to(self.storage_path)) if thumbnail_path else None,
                "compressed_path": str(compressed_path.relative_to(self.storage_path)) if compressed_path else None,
                "uploaded_by": uploaded_by,
                "upload_source": upload_source
            }
            
        except Exception as e:
            logger.error(f"Failed to save file {filename}: {e}")
            raise
    
    async def _create_thumbnail(self, file_path: Path, file_type: FileType) -> Optional[Path]:
        """Создание миниатюры для изображения."""
        if file_type != FileType.IMAGE:
            return None
        
        try:
            thumbnail_dir = self.thumbnail_path / file_type.value
            thumbnail_path = thumbnail_dir / f"thumb_{file_path.name}"
            
            # Создание миниатюры
            with Image.open(file_path) as img:
                # Конвертация в RGB если необходимо
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Создание миниатюры 200x200
                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                img.save(thumbnail_path, 'JPEG', quality=80, optimize=True)
            
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Failed to create thumbnail for {file_path}: {e}")
            return None
    
    async def _create_compressed_version(self, file_path: Path, file_type: FileType) -> Optional[Path]:
        """Создание сжатой версии файла."""
        if file_type != FileType.IMAGE:
            return None
        
        try:
            compressed_dir = self.compressed_path / file_type.value
            compressed_path = compressed_dir / f"comp_{file_path.stem}.jpg"
            
            # Сжатие изображения
            with Image.open(file_path) as img:
                # Конвертация в RGB
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Уменьшение размера если больше 1920x1080
                if img.width > 1920 or img.height > 1080:
                    img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                
                # Сохранение с сжатием
                img.save(compressed_path, 'JPEG', quality=70, optimize=True)
            
            return compressed_path
            
        except Exception as e:
            logger.error(f"Failed to create compressed version for {file_path}: {e}")
            return None
    
    async def get_file_data(self, file_path: str) -> bytes:
        """Получение данных файла."""
        try:
            full_path = self.storage_path / file_path
            
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            async with aiofiles.open(full_path, 'rb') as f:
                return await f.read()
                
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise
    
    async def delete_file(self, file_path: str) -> bool:
        """Удаление файла и связанных миниатюр."""
        try:
            full_path = self.storage_path / file_path
            
            if full_path.exists():
                full_path.unlink()
            
            # Удаление миниатюры
            thumbnail_file = self.thumbnail_path / f"thumb_{full_path.name}"
            if thumbnail_file.exists():
                thumbnail_file.unlink()
            
            # Удаление сжатой версии
            compressed_file = self.compressed_path / f"comp_{full_path.stem}.jpg"
            if compressed_file.exists():
                compressed_file.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Получение информации о файле."""
        try:
            full_path = self.storage_path / file_path
            
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            stat = full_path.stat()
            mime_type, _ = mimetypes.guess_type(str(full_path))
            
            return {
                "file_path": file_path,
                "file_size": stat.st_size,
                "mime_type": mime_type,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
                "modified_at": datetime.fromtimestamp(stat.st_mtime),
                "exists": True
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info {file_path}: {e}")
            return {"exists": False, "error": str(e)}
    
    def get_file_url(self, file_path: str, file_type: str = "original") -> str:
        """Получение URL для доступа к файлу."""
        base_url = f"http://localhost:{settings.PORT}"
        
        if file_type == "thumbnail":
            return f"{base_url}/static/thumbnails/{file_path}"
        elif file_type == "compressed":
            return f"{base_url}/static/compressed/{file_path}"
        else:
            return f"{base_url}/static/{file_path}"
    
    async def process_telegram_file(
        self,
        telegram_file_id: str,
        telegram_file_unique_id: str,
        file_data: bytes,
        filename: str,
        uploaded_by: int
    ) -> Dict[str, Any]:
        """
        Обработка файла из Telegram.
        Для обратной совместимости с существующим ботом.
        """
        try:
            # Определение MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                # Попытка определить по содержимому
                if file_data.startswith(b'\xff\xd8\xff'):
                    mime_type = 'image/jpeg'
                elif file_data.startswith(b'\x89PNG'):
                    mime_type = 'image/png'
                else:
                    mime_type = 'application/octet-stream'
            
            # Сохранение файла
            file_info = await self.save_file(
                file_data, filename, mime_type, uploaded_by, "telegram"
            )
            
            # Добавление Telegram метаданных
            file_info.update({
                "telegram_file_id": telegram_file_id,
                "telegram_file_unique_id": telegram_file_unique_id
            })
            
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to process Telegram file {telegram_file_id}: {e}")
            raise
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Получение статистики хранилища."""
        try:
            stats = {
                "total_files": 0,
                "total_size": 0,
                "by_type": {}
            }
            
            for file_type in FileType:
                type_dir = self.storage_path / file_type.value
                if type_dir.exists():
                    type_files = list(type_dir.glob("*"))
                    type_size = sum(f.stat().st_size for f in type_files if f.is_file())
                    
                    stats["by_type"][file_type.value] = {
                        "count": len(type_files),
                        "size": type_size
                    }
                    
                    stats["total_files"] += len(type_files)
                    stats["total_size"] += type_size
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"error": str(e)}