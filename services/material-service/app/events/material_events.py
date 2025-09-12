# -*- coding: utf-8 -*-
"""
Material Service Event Handler
Handles events from other services and publishes material events
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from ..services.material_service import MaterialService
from ..services.file_service import FileService
from ..core.config import settings
from .rabbitmq_client import RabbitMQClient, MaterialEventPublisher, MockRabbitMQClient

logger = logging.getLogger(__name__)


class MaterialEventHandler:
    """Handles events related to materials and files"""
    
    def __init__(self):
        self.material_service = MaterialService()
        self.file_service = FileService()
        self.is_running = False
        
        # Initialize RabbitMQ client (use mock in development)
        if settings.EVENT_PROCESSING_ENABLED and not settings.DEBUG:
            self.rabbitmq_client = RabbitMQClient()
        else:
            self.rabbitmq_client = MockRabbitMQClient()
        
        self.event_publisher = MaterialEventPublisher(self.rabbitmq_client)
    
    async def start(self):
        """Start event handler"""
        if settings.EVENT_PROCESSING_ENABLED:
            # Connect to RabbitMQ
            connected = await self.rabbitmq_client.connect()
            if not connected:
                logger.error("Failed to connect to RabbitMQ, starting in mock mode")
                self.rabbitmq_client = MockRabbitMQClient()
                await self.rabbitmq_client.connect()
            
            # Setup event consumers
            await self._setup_event_consumers()
            
            self.is_running = True
            logger.info("Material Event Handler started")
        else:
            logger.info("Event processing disabled by configuration")
    
    async def stop(self):
        """Stop event handler"""
        self.is_running = False
        
        # Stop all consumers
        await self.rabbitmq_client.stop_consumer("material_user_events")
        await self.rabbitmq_client.stop_consumer("material_lesson_events")
        
        # Disconnect from RabbitMQ
        await self.rabbitmq_client.disconnect()
        
        logger.info("Material Event Handler stopped")
    
    async def _setup_event_consumers(self):
        """Setup event consumers for different event types"""
        logger.info("Setting up event consumers for:")
        
        # Setup DLQ for failed messages
        await self.rabbitmq_client.setup_dead_letter_queue("material_user_events")
        await self.rabbitmq_client.setup_dead_letter_queue("material_lesson_events")
        
        # Consumer for user events
        await self.rabbitmq_client.create_consumer(
            queue_name="material_user_events",
            routing_keys=[
                "user.student.created",
                "user.tutor.created",
                "user.updated",
                "user.deleted"
            ],
            handler=self._handle_user_event,
            dead_letter_exchange=f"dlq.{settings.RABBITMQ_EXCHANGE}"
        )
        logger.info("- User events consumer (user.student.created, user.tutor.created, user.updated, user.deleted)")
        
        # Consumer for lesson events
        await self.rabbitmq_client.create_consumer(
            queue_name="material_lesson_events",
            routing_keys=[
                "lesson.created",
                "lesson.updated",
                "lesson.completed"
            ],
            handler=self._handle_lesson_event,
            dead_letter_exchange=f"dlq.{settings.RABBITMQ_EXCHANGE}"
        )
        logger.info("- Lesson events consumer (lesson.created, lesson.updated, lesson.completed)")
    
    async def _handle_user_event(self, event_message: Dict[str, Any]):
        """Route user events to appropriate handlers"""
        try:
            event_type = event_message.get('event_type')
            event_data = event_message.get('data', {})
            
            if event_type == "student_created":
                await self.handle_user_created(event_data)
            elif event_type == "tutor_created":
                await self.handle_user_created(event_data)
            elif event_type == "user_updated":
                await self.handle_user_updated(event_data)
            elif event_type == "user_deleted":
                await self.handle_user_deleted(event_data)
            else:
                logger.warning(f"Unknown user event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling user event: {e}")
            raise
    
    async def _handle_lesson_event(self, event_message: Dict[str, Any]):
        """Route lesson events to appropriate handlers"""
        try:
            event_type = event_message.get('event_type')
            event_data = event_message.get('data', {})
            
            if event_type == "lesson_created":
                await self.handle_lesson_created(event_data)
            elif event_type == "lesson_updated":
                await self.handle_lesson_updated(event_data)
            elif event_type == "lesson_completed":
                await self.handle_lesson_completed(event_data)
            else:
                logger.warning(f"Unknown lesson event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling lesson event: {e}")
            raise
    
    async def handle_user_created(self, event: Dict[str, Any]):
        """
        Handle user creation event
        Could set up default materials or user preferences
        """
        try:
            user_id = event.get('user_id')
            user_role = event.get('role', 'student')
            user_grade = event.get('grade')
            
            logger.info(f"Processing user created event: user_id={user_id}, role={user_role}")
            
            # For students, could create personalized material recommendations
            if user_role == 'student' and user_grade:
                await self._create_material_recommendations(user_id, user_grade)
            
            logger.info(f"Successfully processed user created event for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling user created event: {e}")
    
    async def handle_lesson_created(self, event: Dict[str, Any]):
        """
        Handle lesson creation event
        Could suggest relevant materials based on lesson topic
        """
        try:
            lesson_id = event.get('lesson_id')
            student_id = event.get('student_id')
            lesson_topic = event.get('topic')
            lesson_grade = event.get('grade')
            
            logger.info(f"Processing lesson created event: lesson_id={lesson_id}, topic={lesson_topic}")
            
            # Find relevant materials for the lesson topic
            relevant_materials = await self._find_relevant_materials(
                topic=lesson_topic,
                grade=lesson_grade
            )
            
            if relevant_materials:
                # Publish event with suggested materials
                await self.event_publisher.publish_material_accessed({
                    "lesson_id": lesson_id,
                    "student_id": student_id,
                    "lesson_topic": lesson_topic,
                    "suggested_materials": [{"id": m.id, "title": m.title} for m in relevant_materials[:5]],
                    "timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": event.get('correlation_id')
                })
            
            logger.info(f"Successfully processed lesson created event for lesson {lesson_id}")
            
        except Exception as e:
            logger.error(f"Error handling lesson created event: {e}")
    
    async def handle_material_created(self, material_id: int, created_by_user_id: Optional[int]):
        """
        Handle internal material creation
        Publish event to notify other services
        """
        try:
            # Get material details
            material = await self.material_service.get_material(material_id)
            
            if material:
                await self.event_publisher.publish_material_created({
                    "material_id": material_id,
                    "title": material.title,
                    "grade": material.grade,
                    "subject": material.subject,
                    "material_type": material.material_type.value,
                    "created_by_user_id": created_by_user_id,
                    "is_featured": material.is_featured,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error publishing material created event: {e}")
    
    async def handle_file_uploaded(self, file_id: int, material_id: int, uploaded_by_user_id: Optional[int]):
        """
        Handle file upload completion
        Publish event and trigger processing if needed
        """
        try:
            # Get file details
            file = await self.file_service.get_file(file_id)
            
            if file:
                await self.event_publisher.publish_file_uploaded({
                    "file_id": file_id,
                    "material_id": material_id,
                    "filename": file.original_filename,
                    "file_type": file.file_type.value,
                    "file_size": file.file_size,
                    "uploaded_by_user_id": uploaded_by_user_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Trigger additional processing if needed
                await self._trigger_file_processing(file)
            
        except Exception as e:
            logger.error(f"Error publishing file uploaded event: {e}")
    
    async def handle_material_accessed(self, material_id: int, access_type: str, user_id: Optional[int]):
        """
        Handle material access (view, download)
        Update analytics and publish event
        """
        try:
            await self.event_publisher.publish_material_accessed({
                "material_id": material_id,
                "access_type": access_type,  # view, download, share
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error publishing material accessed event: {e}")
    
    async def handle_user_updated(self, event: Dict[str, Any]):
        """Handle user update event"""
        try:
            user_id = event.get('user_id')
            updated_fields = event.get('updated_fields', [])
            
            logger.info(f"Processing user updated event: user_id={user_id}")
            
            # If grade was updated, could update material recommendations
            if 'grade' in updated_fields:
                new_grade = event.get('grade')
                if new_grade:
                    await self._create_material_recommendations(user_id, new_grade)
            
        except Exception as e:
            logger.error(f"Error handling user updated event: {e}")
    
    async def handle_user_deleted(self, event: Dict[str, Any]):
        """Handle user deletion event"""
        try:
            user_id = event.get('user_id')
            logger.info(f"Processing user deleted event: user_id={user_id}")
            
            # Could clean up user-specific material data
            # For now, just log
            
        except Exception as e:
            logger.error(f"Error handling user deleted event: {e}")
    
    async def handle_lesson_updated(self, event: Dict[str, Any]):
        """Handle lesson update event"""
        try:
            lesson_id = event.get('lesson_id')
            updated_fields = event.get('updated_fields', [])
            
            logger.info(f"Processing lesson updated event: lesson_id={lesson_id}")
            
            # If topic was updated, could suggest new materials
            if 'topic' in updated_fields:
                lesson_topic = event.get('topic')
                lesson_grade = event.get('grade')
                student_id = event.get('student_id')
                
                if lesson_topic:
                    relevant_materials = await self._find_relevant_materials(
                        topic=lesson_topic,
                        grade=lesson_grade
                    )
                    
                    if relevant_materials:
                        await self.event_publisher.publish_material_accessed({
                            "lesson_id": lesson_id,
                            "student_id": student_id,
                            "lesson_topic": lesson_topic,
                            "updated_suggested_materials": [{"id": m.id, "title": m.title} for m in relevant_materials[:5]],
                            "timestamp": datetime.utcnow().isoformat(),
                            "correlation_id": event.get('correlation_id')
                        })
            
        except Exception as e:
            logger.error(f"Error handling lesson updated event: {e}")
    
    async def handle_lesson_completed(self, event: Dict[str, Any]):
        """Handle lesson completion event"""
        try:
            lesson_id = event.get('lesson_id')
            student_id = event.get('student_id')
            lesson_topic = event.get('topic')
            
            logger.info(f"Processing lesson completed event: lesson_id={lesson_id}")
            
            # Could track material effectiveness
            # If materials were suggested for this lesson, track completion
            
        except Exception as e:
            logger.error(f"Error handling lesson completed event: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check event handler health"""
        return {
            "is_running": self.is_running,
            "rabbitmq_connected": await self.rabbitmq_client.health_check() if self.rabbitmq_client else False,
            "consumers_active": len(self.rabbitmq_client.consumers) if self.rabbitmq_client else 0
        }
    
    async def _create_material_recommendations(self, user_id: int, user_grade: int):
        """Create personalized material recommendations for new student"""
        try:
            # Get popular materials for the user's grade
            popular_materials = await self.material_service.get_materials_by_grade(user_grade)
            
            if popular_materials:
                # Could store recommendations in a separate service or table
                logger.info(f"Created {len(popular_materials)} material recommendations for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error creating material recommendations: {e}")
    
    async def _find_relevant_materials(self, topic: str, grade: Optional[int]) -> list:
        """Find materials relevant to lesson topic"""
        try:
            from ..schemas.material import MaterialSearchRequest
            
            search_request = MaterialSearchRequest(
                query=topic,
                grade=grade,
                per_page=10,
                sort_by="view_count",
                sort_order="desc"
            )
            
            materials, _ = await self.material_service.search_materials(search_request)
            return materials
            
        except Exception as e:
            logger.error(f"Error finding relevant materials: {e}")
            return []
    
    async def _trigger_file_processing(self, file):
        """Trigger additional file processing if needed"""
        try:
            # Could trigger:
            # - Text extraction from PDFs
            # - Image optimization
            # - Video transcoding
            # - Virus scanning
            # etc.
            
            if file.file_type.value in ['pdf', 'doc', 'docx']:
                logger.info(f"Could extract text from {file.filename} for search indexing")
            
            if file.file_type.value in ['jpg', 'jpeg', 'png']:
                logger.info(f"Could optimize image {file.filename}")
            
        except Exception as e:
            logger.error(f"Error in file processing: {e}")


class MockEventHandler(MaterialEventHandler):
    """Mock event handler for testing and development"""
    
    async def start(self):
        """Start mock event handler"""
        self.is_running = True
        logger.info("Mock Material Event Handler started")
    
    async def stop(self):
        """Stop mock event handler"""
        self.is_running = False
        logger.info("Mock Material Event Handler stopped")
    
    async def simulate_user_created(self, user_id: int, role: str = "student", grade: Optional[int] = None):
        """Simulate user created event for testing"""
        event = {
            "user_id": user_id,
            "role": role,
            "grade": grade,
            "created_at": datetime.utcnow().isoformat()
        }
        await self.handle_user_created(event)
    
    async def simulate_lesson_created(self, lesson_id: int, student_id: int, topic: str, grade: int):
        """Simulate lesson created event for testing"""
        event = {
            "lesson_id": lesson_id,
            "student_id": student_id,
            "topic": topic,
            "grade": grade,
            "created_at": datetime.utcnow().isoformat()
        }
        await self.handle_lesson_created(event)
    
    async def simulate_material_access(self, material_id: int, access_type: str = "view", user_id: Optional[int] = None):
        """Simulate material access for testing"""
        await self.handle_material_accessed(material_id, access_type, user_id)