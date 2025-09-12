# -*- coding: utf-8 -*-
"""
Health Service для мониторинга состояния Homework Service.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any

from ..database.connection import check_database_connection, get_database_info
from ..config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HealthService:
    """Сервис для проверки состояния системы."""
    
    def __init__(self):
        self.start_time = datetime.now()
    
    async def check_health(self) -> Dict[str, Any]:
        """Комплексная проверка состояния сервиса."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "homework-service",
            "version": "1.0.0",
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "checks": {}
        }
        
        # Проверка базы данных
        db_healthy = await check_database_connection()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "details": await get_database_info() if db_healthy else {"error": "Connection failed"}
        }
        
        # Проверка файловой системы
        storage_healthy = await self._check_storage()
        health_status["checks"]["storage"] = {
            "status": "healthy" if storage_healthy else "unhealthy",
            "details": await self._get_storage_info()
        }
        
        # Проверка RabbitMQ (опционально)
        try:
            import aio_pika
            rabbitmq_healthy = await self._check_rabbitmq()
            health_status["checks"]["rabbitmq"] = {
                "status": "healthy" if rabbitmq_healthy else "unhealthy"
            }
        except ImportError:
            health_status["checks"]["rabbitmq"] = {
                "status": "skipped",
                "reason": "aio_pika not available"
            }
        
        # Определение общего статуса
        all_checks_healthy = all(
            check["status"] == "healthy" or check["status"] == "skipped"
            for check in health_status["checks"].values()
        )
        
        if not all_checks_healthy:
            health_status["status"] = "unhealthy"
        
        return health_status
    
    async def _check_storage(self) -> bool:
        """Проверка доступности файлового хранилища."""
        try:
            storage_path = settings.FILE_STORAGE_PATH
            
            # Создание директории если не существует
            os.makedirs(storage_path, exist_ok=True)
            
            # Проверка записи
            test_file = os.path.join(storage_path, ".health_check")
            with open(test_file, 'w') as f:
                f.write("health_check")
            
            # Проверка чтения
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Удаление тестового файла
            os.remove(test_file)
            
            return content == "health_check"
            
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return False
    
    async def _get_storage_info(self) -> Dict[str, Any]:
        """Получение информации о хранилище."""
        try:
            storage_path = settings.FILE_STORAGE_PATH
            
            if not os.path.exists(storage_path):
                return {"error": "Storage path does not exist"}
            
            # Статистика диска
            stat = os.statvfs(storage_path)
            free_space = stat.f_frsize * stat.f_availBlocks
            total_space = stat.f_frsize * stat.f_blocks
            used_space = total_space - free_space
            
            # Количество файлов
            file_count = sum(len(files) for _, _, files in os.walk(storage_path))
            
            return {
                "path": storage_path,
                "total_space_bytes": total_space,
                "used_space_bytes": used_space,
                "free_space_bytes": free_space,
                "usage_percent": (used_space / total_space * 100) if total_space > 0 else 0,
                "file_count": file_count
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _check_rabbitmq(self) -> bool:
        """Проверка подключения к RabbitMQ."""
        try:
            import aio_pika
            
            connection = await asyncio.wait_for(
                aio_pika.connect_robust(settings.RABBITMQ_URL),
                timeout=settings.HEALTH_CHECK_TIMEOUT
            )
            
            await connection.close()
            return True
            
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return False
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик сервиса."""
        try:
            from ..database.connection import get_db_session
            from ..models.homework import Homework, HomeworkFile
            from sqlalchemy import func, select
            
            async with get_db_session() as db:
                # Общее количество домашних заданий
                total_homework_stmt = select(func.count(Homework.id))
                total_homework_result = await db.execute(total_homework_stmt)
                total_homework = total_homework_result.scalar()
                
                # Количество по статусам
                status_stats = {}
                for status in ["pending", "submitted", "checked"]:
                    status_stmt = select(func.count(Homework.id)).where(
                        Homework.status == status
                    )
                    status_result = await db.execute(status_stmt)
                    status_stats[status] = status_result.scalar()
                
                # Статистика файлов
                total_files_stmt = select(func.count(HomeworkFile.id))
                total_files_result = await db.execute(total_files_stmt)
                total_files = total_files_result.scalar()
                
                # Размер файлов
                total_size_stmt = select(func.sum(HomeworkFile.file_size))
                total_size_result = await db.execute(total_size_stmt)
                total_size = total_size_result.scalar() or 0
                
            return {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "homework": {
                    "total": total_homework,
                    "by_status": status_stats
                },
                "files": {
                    "total_count": total_files,
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / 1024 / 1024, 2)
                },
                "storage": await self._get_storage_info()
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }