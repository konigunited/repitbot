"""
Event Consumer for Analytics Service
Consumes events from RabbitMQ and updates analytics data
"""

import json
import asyncio
import logging
from typing import Dict, Any, Callable
from datetime import datetime
import aio_pika
from aio_pika import connect, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
import os

from ..database import get_db_session
from ..models import User, Lesson, Payment, Homework, Material
from ..services.lesson_analytics import LessonAnalyticsService
from ..services.payment_analytics import PaymentAnalyticsService
from ..services.user_analytics import UserAnalyticsService
from ..services.material_analytics import MaterialAnalyticsService

logger = logging.getLogger(__name__)

class AnalyticsEventConsumer:
    """Event consumer for analytics service"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queues = {}
        
        # Services
        self.lesson_service = LessonAnalyticsService()
        self.payment_service = PaymentAnalyticsService()
        self.user_service = UserAnalyticsService()
        self.material_service = MaterialAnalyticsService()
        
        # Event handlers mapping
        self.event_handlers = {
            "lesson.completed": self.handle_lesson_completed,
            "lesson.created": self.handle_lesson_created,
            "lesson.cancelled": self.handle_lesson_cancelled,
            "payment.processed": self.handle_payment_processed,
            "payment.failed": self.handle_payment_failed,
            "homework.submitted": self.handle_homework_submitted,
            "homework.graded": self.handle_homework_graded,
            "material.accessed": self.handle_material_accessed,
            "material.uploaded": self.handle_material_uploaded,
            "user.login": self.handle_user_login,
            "user.registered": self.handle_user_registered,
            "user.profile_updated": self.handle_user_profile_updated
        }

    async def connect(self):
        """Connect to RabbitMQ"""
        try:
            rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
            self.connection = await connect(rabbitmq_url)
            self.channel = await self.connection.channel()
            
            # Set QoS for fair dispatch
            await self.channel.set_qos(prefetch_count=1)
            
            logger.info("Connected to RabbitMQ for analytics events")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    async def setup_queues(self):
        """Setup queues and exchanges for analytics events"""
        try:
            # Declare exchanges
            analytics_exchange = await self.channel.declare_exchange(
                "analytics", aio_pika.ExchangeType.TOPIC, durable=True
            )
            
            # Declare analytics queue
            analytics_queue = await self.channel.declare_queue(
                "analytics.events", durable=True
            )
            
            # Bind queue to exchange with different routing keys
            routing_keys = [
                "lesson.*",
                "payment.*", 
                "homework.*",
                "material.*",
                "user.*"
            ]
            
            for routing_key in routing_keys:
                await analytics_queue.bind(analytics_exchange, routing_key)
            
            self.queues["analytics"] = analytics_queue
            
            logger.info("Analytics queues and bindings setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup queues: {str(e)}")
            raise

    async def start_consuming(self):
        """Start consuming events"""
        try:
            await self.connect()
            await self.setup_queues()
            
            # Start consuming from analytics queue
            await self.queues["analytics"].consume(self.process_message)
            
            logger.info("Started consuming analytics events")
            
        except Exception as e:
            logger.error(f"Failed to start consuming: {str(e)}")
            raise

    async def process_message(self, message: aio_pika.IncomingMessage):
        """Process incoming event message"""
        async with message.process():
            try:
                # Parse message
                event_data = json.loads(message.body.decode())
                event_type = message.routing_key
                
                logger.info(f"Processing analytics event: {event_type}")
                
                # Get handler for event type
                handler = self.event_handlers.get(event_type)
                if handler:
                    await handler(event_data)
                else:
                    logger.warning(f"No handler found for event type: {event_type}")
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                # Message will be requeued due to exception

    async def handle_lesson_completed(self, event_data: Dict[str, Any]):
        """Handle lesson completion event"""
        try:
            lesson_id = event_data.get("lesson_id")
            student_id = event_data.get("student_id") 
            tutor_id = event_data.get("tutor_id")
            rating = event_data.get("rating")
            completed_at = event_data.get("completed_at")
            
            # Update lesson analytics
            await self.lesson_service.update_lesson_completion_stats(
                lesson_id, student_id, tutor_id, rating, completed_at
            )
            
            # Update tutor performance metrics
            await self.lesson_service.update_tutor_performance(tutor_id, rating)
            
            # Update student progress
            await self.lesson_service.update_student_progress(student_id, lesson_id)
            
            logger.info(f"Processed lesson completion for lesson {lesson_id}")
            
        except Exception as e:
            logger.error(f"Error handling lesson completed event: {str(e)}")
            raise

    async def handle_lesson_created(self, event_data: Dict[str, Any]):
        """Handle lesson creation event"""
        try:
            lesson_id = event_data.get("lesson_id")
            tutor_id = event_data.get("tutor_id")
            student_id = event_data.get("student_id")
            subject_id = event_data.get("subject_id")
            scheduled_at = event_data.get("scheduled_at")
            
            # Update lesson creation stats
            await self.lesson_service.update_lesson_creation_stats(
                lesson_id, tutor_id, student_id, subject_id, scheduled_at
            )
            
            logger.info(f"Processed lesson creation for lesson {lesson_id}")
            
        except Exception as e:
            logger.error(f"Error handling lesson created event: {str(e)}")
            raise

    async def handle_lesson_cancelled(self, event_data: Dict[str, Any]):
        """Handle lesson cancellation event"""
        try:
            lesson_id = event_data.get("lesson_id")
            cancelled_by = event_data.get("cancelled_by")
            cancellation_reason = event_data.get("reason")
            cancelled_at = event_data.get("cancelled_at")
            
            # Update cancellation statistics
            await self.lesson_service.update_cancellation_stats(
                lesson_id, cancelled_by, cancellation_reason, cancelled_at
            )
            
            logger.info(f"Processed lesson cancellation for lesson {lesson_id}")
            
        except Exception as e:
            logger.error(f"Error handling lesson cancelled event: {str(e)}")
            raise

    async def handle_payment_processed(self, event_data: Dict[str, Any]):
        """Handle payment processed event"""
        try:
            payment_id = event_data.get("payment_id")
            amount = event_data.get("amount")
            tutor_id = event_data.get("tutor_id")
            student_id = event_data.get("student_id")
            payment_method = event_data.get("payment_method")
            processed_at = event_data.get("processed_at")
            
            # Update payment analytics
            await self.payment_service.update_payment_stats(
                payment_id, amount, tutor_id, student_id, 
                payment_method, processed_at
            )
            
            # Update revenue metrics
            await self.payment_service.update_revenue_metrics(
                amount, tutor_id, processed_at
            )
            
            # Update tutor earnings
            await self.payment_service.update_tutor_earnings(
                tutor_id, amount, processed_at
            )
            
            logger.info(f"Processed payment for payment {payment_id}")
            
        except Exception as e:
            logger.error(f"Error handling payment processed event: {str(e)}")
            raise

    async def handle_payment_failed(self, event_data: Dict[str, Any]):
        """Handle payment failure event"""
        try:
            payment_id = event_data.get("payment_id")
            amount = event_data.get("amount")
            failure_reason = event_data.get("failure_reason")
            failed_at = event_data.get("failed_at")
            
            # Update payment failure statistics
            await self.payment_service.update_payment_failure_stats(
                payment_id, amount, failure_reason, failed_at
            )
            
            logger.info(f"Processed payment failure for payment {payment_id}")
            
        except Exception as e:
            logger.error(f"Error handling payment failed event: {str(e)}")
            raise

    async def handle_homework_submitted(self, event_data: Dict[str, Any]):
        """Handle homework submission event"""
        try:
            homework_id = event_data.get("homework_id")
            student_id = event_data.get("student_id")
            lesson_id = event_data.get("lesson_id")
            submitted_at = event_data.get("submitted_at")
            submission_time = event_data.get("submission_time")  # Time taken to submit
            
            # Update homework submission stats
            await self.lesson_service.update_homework_submission_stats(
                homework_id, student_id, lesson_id, 
                submitted_at, submission_time
            )
            
            # Update student engagement metrics
            await self.user_service.update_engagement_metrics(
                student_id, "homework_submission", submitted_at
            )
            
            logger.info(f"Processed homework submission for homework {homework_id}")
            
        except Exception as e:
            logger.error(f"Error handling homework submitted event: {str(e)}")
            raise

    async def handle_homework_graded(self, event_data: Dict[str, Any]):
        """Handle homework grading event"""
        try:
            homework_id = event_data.get("homework_id")
            student_id = event_data.get("student_id")
            tutor_id = event_data.get("tutor_id")
            grade = event_data.get("grade")
            graded_at = event_data.get("graded_at")
            
            # Update homework grading stats
            await self.lesson_service.update_homework_grading_stats(
                homework_id, student_id, tutor_id, grade, graded_at
            )
            
            # Update student performance metrics
            await self.lesson_service.update_student_performance(
                student_id, grade, graded_at
            )
            
            logger.info(f"Processed homework grading for homework {homework_id}")
            
        except Exception as e:
            logger.error(f"Error handling homework graded event: {str(e)}")
            raise

    async def handle_material_accessed(self, event_data: Dict[str, Any]):
        """Handle material access event"""
        try:
            material_id = event_data.get("material_id")
            user_id = event_data.get("user_id")
            access_type = event_data.get("access_type")  # view, download
            accessed_at = event_data.get("accessed_at")
            
            # Update material usage stats
            await self.material_service.update_material_access_stats(
                material_id, user_id, access_type, accessed_at
            )
            
            # Update user engagement
            await self.user_service.update_engagement_metrics(
                user_id, "material_access", accessed_at
            )
            
            logger.info(f"Processed material access for material {material_id}")
            
        except Exception as e:
            logger.error(f"Error handling material accessed event: {str(e)}")
            raise

    async def handle_material_uploaded(self, event_data: Dict[str, Any]):
        """Handle material upload event"""
        try:
            material_id = event_data.get("material_id")
            uploaded_by = event_data.get("uploaded_by")
            subject_id = event_data.get("subject_id")
            file_size = event_data.get("file_size")
            uploaded_at = event_data.get("uploaded_at")
            
            # Update material upload stats
            await self.material_service.update_material_upload_stats(
                material_id, uploaded_by, subject_id, 
                file_size, uploaded_at
            )
            
            # Update tutor activity metrics
            await self.user_service.update_engagement_metrics(
                uploaded_by, "material_upload", uploaded_at
            )
            
            logger.info(f"Processed material upload for material {material_id}")
            
        except Exception as e:
            logger.error(f"Error handling material uploaded event: {str(e)}")
            raise

    async def handle_user_login(self, event_data: Dict[str, Any]):
        """Handle user login event"""
        try:
            user_id = event_data.get("user_id")
            login_time = event_data.get("login_time")
            ip_address = event_data.get("ip_address")
            user_agent = event_data.get("user_agent")
            
            # Update user activity stats
            await self.user_service.update_login_stats(
                user_id, login_time, ip_address, user_agent
            )
            
            # Update session metrics
            await self.user_service.update_session_metrics(
                user_id, login_time
            )
            
            logger.info(f"Processed user login for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling user login event: {str(e)}")
            raise

    async def handle_user_registered(self, event_data: Dict[str, Any]):
        """Handle user registration event"""
        try:
            user_id = event_data.get("user_id")
            role = event_data.get("role")
            registration_source = event_data.get("registration_source")
            registered_at = event_data.get("registered_at")
            
            # Update user registration stats
            await self.user_service.update_registration_stats(
                user_id, role, registration_source, registered_at
            )
            
            # Update role distribution metrics
            await self.user_service.update_role_distribution()
            
            logger.info(f"Processed user registration for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling user registered event: {str(e)}")
            raise

    async def handle_user_profile_updated(self, event_data: Dict[str, Any]):
        """Handle user profile update event"""
        try:
            user_id = event_data.get("user_id")
            updated_fields = event_data.get("updated_fields", [])
            updated_at = event_data.get("updated_at")
            
            # Update user engagement metrics
            await self.user_service.update_engagement_metrics(
                user_id, "profile_update", updated_at
            )
            
            logger.info(f"Processed profile update for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling user profile updated event: {str(e)}")
            raise

    async def close(self):
        """Close connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Analytics event consumer connection closed")

# Global consumer instance
analytics_consumer = AnalyticsEventConsumer()

async def start_analytics_consumer():
    """Start the analytics event consumer"""
    try:
        await analytics_consumer.start_consuming()
        
        # Keep consuming
        await asyncio.Future()  # Run forever
        
    except KeyboardInterrupt:
        logger.info("Shutting down analytics consumer...")
    except Exception as e:
        logger.error(f"Analytics consumer error: {str(e)}")
    finally:
        await analytics_consumer.close()

if __name__ == "__main__":
    # Run consumer directly
    asyncio.run(start_analytics_consumer())