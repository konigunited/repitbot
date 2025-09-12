# -*- coding: utf-8 -*-
"""
HTTP клиент для взаимодействия с Homework Service.
Обеспечивает интеграцию Telegram Bot с микросервисом домашних заданий.
"""

import logging
import httpx
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import io

logger = logging.getLogger(__name__)


@dataclass
class HomeworkData:
    """Данные домашнего задания для создания."""
    lesson_id: int
    student_id: int
    tutor_id: int
    description: str
    deadline: Optional[datetime] = None
    max_attempts: int = 1
    weight: float = 1.0
    auto_check: bool = False


@dataclass
class HomeworkResponse:
    """Ответ от Homework Service."""
    id: int
    lesson_id: int
    student_id: int
    tutor_id: int
    description: str
    status: str
    deadline: Optional[datetime]
    created_at: datetime
    submitted_at: Optional[datetime]
    checked_at: Optional[datetime]
    grade: Optional[float]
    feedback: Optional[str]
    max_attempts: int
    current_attempt: int


@dataclass
class FileUploadData:
    """Данные файла для загрузки."""
    filename: str
    content: bytes
    mime_type: str
    uploaded_by: int


class HomeworkServiceClient:
    """HTTP клиент для Homework Service."""
    
    def __init__(self, base_url: str = "http://localhost:8003", timeout: float = 60.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("HomeworkServiceClient must be used as async context manager")
        return self._client
    
    async def create_homework(self, homework_data: HomeworkData) -> Optional[HomeworkResponse]:
        """Создание нового домашнего задания."""
        try:
            payload = {
                "lesson_id": homework_data.lesson_id,
                "student_id": homework_data.student_id,
                "tutor_id": homework_data.tutor_id,
                "description": homework_data.description,
                "max_attempts": homework_data.max_attempts,
                "weight": homework_data.weight,
                "auto_check": homework_data.auto_check
            }
            
            if homework_data.deadline:
                payload["deadline"] = homework_data.deadline.isoformat()
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/homework",
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                return self._parse_homework_response(data)
            else:
                logger.error(f"Failed to create homework: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating homework: {e}")
            return None
    
    async def get_homework(self, homework_id: int) -> Optional[HomeworkResponse]:
        """Получение домашнего задания по ID."""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/homework/{homework_id}")
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_homework_response(data)
            else:
                logger.error(f"Failed to get homework {homework_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting homework {homework_id}: {e}")
            return None
    
    async def update_homework(
        self, 
        homework_id: int, 
        updates: Dict[str, Any]
    ) -> Optional[HomeworkResponse]:
        """Обновление домашнего задания."""
        try:
            # Конвертация datetime в ISO формат
            if "deadline" in updates and isinstance(updates["deadline"], datetime):
                updates["deadline"] = updates["deadline"].isoformat()
            
            response = await self.client.put(
                f"{self.base_url}/api/v1/homework/{homework_id}",
                json=updates
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_homework_response(data)
            else:
                logger.error(f"Failed to update homework {homework_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating homework {homework_id}: {e}")
            return None
    
    async def submit_homework(
        self,
        homework_id: int,
        text_content: Optional[str] = None,
        files: Optional[List[FileUploadData]] = None
    ) -> bool:
        """Сдача домашнего задания."""
        try:
            submission_data = {}
            
            if text_content:
                submission_data["text_content"] = text_content
                submission_data["submission_type"] = "mixed" if files else "text"
            elif files:
                submission_data["submission_type"] = "file"
            
            # Создание отправки
            response = await self.client.post(
                f"{self.base_url}/api/v1/homework/{homework_id}/submit",
                json=submission_data
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to submit homework {homework_id}: {response.status_code}")
                return False
            
            submission_data = response.json()
            submission_id = submission_data["id"]
            
            # Загрузка файлов если есть
            if files:
                for file_data in files:
                    await self._upload_submission_file(submission_id, file_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error submitting homework {homework_id}: {e}")
            return False
    
    async def _upload_submission_file(
        self, 
        submission_id: int, 
        file_data: FileUploadData
    ) -> Optional[Dict[str, Any]]:
        """Загрузка файла для отправки."""
        try:
            files = {
                "file": (file_data.filename, io.BytesIO(file_data.content), file_data.mime_type)
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/submissions/{submission_id}/files",
                files=files,
                data={"uploaded_by": str(file_data.uploaded_by)}
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"Failed to upload file for submission {submission_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading file for submission {submission_id}: {e}")
            return None
    
    async def check_homework(
        self,
        homework_id: int,
        check_status: str,
        grade: Optional[float] = None,
        feedback: Optional[str] = None
    ) -> Optional[HomeworkResponse]:
        """Проверка домашнего задания."""
        try:
            data = {
                "check_status": check_status
            }
            
            if grade is not None:
                data["grade"] = grade
            if feedback:
                data["feedback"] = feedback
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/homework/{homework_id}/check",
                json=data
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_homework_response(data)
            else:
                logger.error(f"Failed to check homework {homework_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error checking homework {homework_id}: {e}")
            return None
    
    async def get_homework_list(
        self,
        student_id: Optional[int] = None,
        tutor_id: Optional[int] = None,
        lesson_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Optional[Dict[str, Any]]:
        """Получение списка домашних заданий с фильтрами."""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            
            if student_id:
                params["student_id"] = student_id
            if tutor_id:
                params["tutor_id"] = tutor_id
            if lesson_id:
                params["lesson_id"] = lesson_id
            if status:
                params["status"] = status
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/homework",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                # Конвертация дат в datetime объекты
                for homework in data["homework"]:
                    homework["created_at"] = datetime.fromisoformat(homework["created_at"])
                    if homework["deadline"]:
                        homework["deadline"] = datetime.fromisoformat(homework["deadline"])
                    if homework["submitted_at"]:
                        homework["submitted_at"] = datetime.fromisoformat(homework["submitted_at"])
                    if homework["checked_at"]:
                        homework["checked_at"] = datetime.fromisoformat(homework["checked_at"])
                
                return data
            else:
                logger.error(f"Failed to get homework list: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting homework list: {e}")
            return None
    
    async def upload_homework_file(
        self,
        homework_id: int,
        file_data: FileUploadData
    ) -> Optional[Dict[str, Any]]:
        """Загрузка файла к домашнему заданию (от репетитора)."""
        try:
            files = {
                "file": (file_data.filename, io.BytesIO(file_data.content), file_data.mime_type)
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/homework/{homework_id}/files",
                files=files,
                data={"uploaded_by": str(file_data.uploaded_by)}
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"Failed to upload homework file: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading homework file: {e}")
            return None
    
    async def download_file(self, file_id: int) -> Optional[Tuple[bytes, str, str]]:
        """Скачивание файла."""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/files/{file_id}")
            
            if response.status_code == 200:
                content = response.content
                filename = response.headers.get("X-Filename", "file")
                mime_type = response.headers.get("Content-Type", "application/octet-stream")
                return content, filename, mime_type
            else:
                logger.error(f"Failed to download file {file_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return None
    
    async def get_homework_stats(
        self,
        student_id: Optional[int] = None,
        tutor_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Получение статистики по домашним заданиям."""
        try:
            params = {}
            
            if student_id:
                params["student_id"] = student_id
            if tutor_id:
                params["tutor_id"] = tutor_id
            if date_from:
                params["date_from"] = date_from.isoformat()
            if date_to:
                params["date_to"] = date_to.isoformat()
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/homework/stats",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get homework stats: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting homework stats: {e}")
            return None
    
    async def process_telegram_file(
        self,
        homework_id: int,
        telegram_file_id: str,
        telegram_file_unique_id: str,
        file_content: bytes,
        filename: str,
        uploaded_by: int
    ) -> Optional[Dict[str, Any]]:
        """Обработка файла из Telegram для обратной совместимости."""
        try:
            files = {
                "file": (filename, io.BytesIO(file_content), "application/octet-stream")
            }
            
            data = {
                "uploaded_by": str(uploaded_by),
                "telegram_file_id": telegram_file_id,
                "telegram_file_unique_id": telegram_file_unique_id,
                "upload_source": "telegram"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/homework/{homework_id}/files/telegram",
                files=files,
                data=data
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"Failed to process Telegram file: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing Telegram file: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Проверка состояния Homework Service."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Homework Service health check failed: {e}")
            return False
    
    def _parse_homework_response(self, data: Dict[str, Any]) -> HomeworkResponse:
        """Парсинг ответа API в HomeworkResponse."""
        return HomeworkResponse(
            id=data["id"],
            lesson_id=data["lesson_id"],
            student_id=data["student_id"],
            tutor_id=data["tutor_id"],
            description=data["description"],
            status=data["status"],
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            submitted_at=datetime.fromisoformat(data["submitted_at"]) if data.get("submitted_at") else None,
            checked_at=datetime.fromisoformat(data["checked_at"]) if data.get("checked_at") else None,
            grade=data.get("grade"),
            feedback=data.get("feedback"),
            max_attempts=data.get("max_attempts", 1),
            current_attempt=data.get("current_attempt", 1)
        )


# Fallback функции для обратной совместимости с монолитом
async def create_homework_fallback(homework_data: HomeworkData) -> Optional[int]:
    """Fallback создание ДЗ через монолитную БД."""
    try:
        from ...src.database import SessionLocal, Homework, HomeworkStatus
        
        db = SessionLocal()
        try:
            homework = Homework(
                lesson_id=homework_data.lesson_id,
                description=homework_data.description,
                deadline=homework_data.deadline,
                status=HomeworkStatus.PENDING,
                created_by=homework_data.tutor_id,
                max_attempts=homework_data.max_attempts,
                weight=homework_data.weight
            )
            
            db.add(homework)
            db.commit()
            db.refresh(homework)
            
            logger.info(f"Created homework {homework.id} via fallback")
            return homework.id
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Fallback homework creation failed: {e}")
        return None


# Создание глобального клиента с fallback логикой
class HomeworkServiceManager:
    """Менеджер для работы с Homework Service с fallback на монолит."""
    
    def __init__(self, service_url: str = "http://localhost:8003"):
        self.service_url = service_url
        self._service_available = None
    
    async def _check_service_availability(self) -> bool:
        """Проверка доступности сервиса."""
        if self._service_available is not None:
            return self._service_available
        
        try:
            async with HomeworkServiceClient(self.service_url) as client:
                self._service_available = await client.health_check()
                return self._service_available
        except Exception:
            self._service_available = False
            return False
    
    async def create_homework(self, homework_data: HomeworkData) -> Optional[int]:
        """Создание ДЗ с fallback."""
        if await self._check_service_availability():
            try:
                async with HomeworkServiceClient(self.service_url) as client:
                    homework = await client.create_homework(homework_data)
                    return homework.id if homework else None
            except Exception as e:
                logger.warning(f"Homework service failed, using fallback: {e}")
                self._service_available = False
        
        # Fallback на монолитную БД
        return await create_homework_fallback(homework_data)
    
    async def get_homework(self, homework_id: int) -> Optional[HomeworkResponse]:
        """Получение ДЗ с fallback."""
        if await self._check_service_availability():
            try:
                async with HomeworkServiceClient(self.service_url) as client:
                    return await client.get_homework(homework_id)
            except Exception as e:
                logger.warning(f"Homework service failed, using fallback: {e}")
                self._service_available = False
        
        # TODO: Реализовать fallback получение из монолитной БД
        return None
    
    async def submit_homework(
        self,
        homework_id: int,
        text_content: Optional[str] = None,
        files: Optional[List[FileUploadData]] = None
    ) -> bool:
        """Сдача ДЗ с fallback."""
        if await self._check_service_availability():
            try:
                async with HomeworkServiceClient(self.service_url) as client:
                    return await client.submit_homework(homework_id, text_content, files)
            except Exception as e:
                logger.warning(f"Homework service failed: {e}")
                self._service_available = False
        
        # TODO: Реализовать fallback через монолитную БД
        return False


# Глобальный экземпляр менеджера
homework_service_manager = HomeworkServiceManager()