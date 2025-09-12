# -*- coding: utf-8 -*-
"""
Payment Service Event Handler
Handles events from other services and publishes payment events
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

from ..services.payment_service import PaymentService
from ..services.balance_service import BalanceService
from ..core.config import settings
from .rabbitmq_client import RabbitMQClient, EventPublisher, MockRabbitMQClient

logger = logging.getLogger(__name__)


class PaymentEventHandler:
    """Handles events related to payments and balance management"""
    
    def __init__(self):
        self.payment_service = PaymentService()
        self.balance_service = BalanceService()
        self.is_running = False
        
        # Initialize RabbitMQ client (use mock in development)
        if settings.EVENT_PROCESSING_ENABLED and not settings.DEBUG:
            self.rabbitmq_client = RabbitMQClient()
        else:
            self.rabbitmq_client = MockRabbitMQClient()
        
        self.event_publisher = EventPublisher(self.rabbitmq_client)
    
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
            logger.info("Payment Event Handler started")
        else:
            logger.info("Event processing disabled by configuration")
    
    async def stop(self):
        """Stop event handler"""
        self.is_running = False
        
        # Stop all consumers
        await self.rabbitmq_client.stop_consumer("payment_lesson_events")
        await self.rabbitmq_client.stop_consumer("payment_user_events")
        
        # Disconnect from RabbitMQ
        await self.rabbitmq_client.disconnect()
        
        logger.info("Payment Event Handler stopped")
    
    async def _setup_event_consumers(self):
        """Setup event consumers for different event types"""
        logger.info("Setting up event consumers for:")
        
        # Setup DLQ for failed messages
        await self.rabbitmq_client.setup_dead_letter_queue("payment_lesson_events")
        await self.rabbitmq_client.setup_dead_letter_queue("payment_user_events")
        
        # Consumer for lesson events
        await self.rabbitmq_client.create_consumer(
            queue_name="payment_lesson_events",
            routing_keys=[
                "lesson.completed",
                "lesson.cancelled",
                "lesson.rescheduled"
            ],
            handler=self._handle_lesson_event,
            dead_letter_exchange=f"dlq.{settings.RABBITMQ_EXCHANGE}"
        )
        logger.info("- Lesson events consumer (lesson.completed, lesson.cancelled, lesson.rescheduled)")
        
        # Consumer for user events
        await self.rabbitmq_client.create_consumer(
            queue_name="payment_user_events",
            routing_keys=[
                "user.student.created",
                "user.student.deleted"
            ],
            handler=self._handle_user_event,
            dead_letter_exchange=f"dlq.{settings.RABBITMQ_EXCHANGE}"
        )
        logger.info("- User events consumer (user.student.created, user.student.deleted)")
    
    async def _handle_lesson_event(self, event_message: Dict[str, Any]):
        """Route lesson events to appropriate handlers"""
        try:
            event_type = event_message.get('event_type')
            event_data = event_message.get('data', {})
            
            if event_type == "lesson_completed":
                await self.handle_lesson_completed(event_data)
            elif event_type == "lesson_cancelled":
                await self.handle_lesson_cancelled(event_data)
            elif event_type == "lesson_rescheduled":
                await self.handle_lesson_rescheduled(event_data)
            else:
                logger.warning(f"Unknown lesson event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling lesson event: {e}")
            raise
    
    async def _handle_user_event(self, event_message: Dict[str, Any]):
        """Route user events to appropriate handlers"""
        try:
            event_type = event_message.get('event_type')
            event_data = event_message.get('data', {})
            
            if event_type == "student_created":
                await self.handle_student_created(event_data)
            elif event_type == "student_deleted":
                await self.handle_student_deleted(event_data)
            else:
                logger.warning(f"Unknown user event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling user event: {e}")
            raise
    
    async def handle_lesson_completed(self, event: Dict[str, Any]):
        """
        Handle lesson completion event
        Deduct lesson from student balance
        """
        try:
            lesson_id = event.get('lesson_id')
            student_id = event.get('student_id')
            lesson_price = Decimal(str(event.get('lesson_price', settings.DEFAULT_PRICE_PER_LESSON)))
            lesson_topic = event.get('lesson_topic', 'Lesson')
            lesson_date = event.get('lesson_date')
            
            logger.info(f"Processing lesson completed event: lesson_id={lesson_id}, student_id={student_id}")
            
            # Deduct lesson from balance
            await self.balance_service.deduct_lessons(
                student_id=student_id,
                lessons_count=1,
                amount=lesson_price,
                description=f"Lesson completed: {lesson_topic}",
                lesson_id=lesson_id
            )
            
            # Publish balance deducted event
            await self.event_publisher.publish_balance_deducted({
                "student_id": student_id,
                "lesson_id": lesson_id,
                "lessons_deducted": 1,
                "amount_spent": float(lesson_price),
                "reason": "lesson_completed",
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": event.get('correlation_id')
            })
            
            logger.info(f"Successfully processed lesson completed event for student {student_id}")
            
        except Exception as e:
            logger.error(f"Error handling lesson completed event: {e}")
            # TODO: Send to dead letter queue
    
    async def handle_lesson_cancelled(self, event: Dict[str, Any]):
        """
        Handle lesson cancellation event
        May need to refund balance depending on cancellation type
        """
        try:
            lesson_id = event.get('lesson_id')
            student_id = event.get('student_id')
            cancellation_type = event.get('cancellation_type', 'unknown')  # 'excused', 'unexcused', 'rescheduled'
            lesson_price = Decimal(str(event.get('lesson_price', settings.DEFAULT_PRICE_PER_LESSON)))
            lesson_topic = event.get('lesson_topic', 'Lesson')
            
            logger.info(f"Processing lesson cancelled event: lesson_id={lesson_id}, student_id={student_id}, type={cancellation_type}")
            
            # Only refund for excused absences and reschedules
            if cancellation_type in ['excused', 'rescheduled']:
                # Add lesson back to balance
                await self.balance_service.add_lessons(
                    student_id=student_id,
                    lessons_count=1,
                    amount=Decimal('0.00'),  # No new money, just returning balance
                    description=f"Lesson refund: {lesson_topic} ({cancellation_type})",
                    reference_id=f"lesson_{lesson_id}_refund"
                )
                
                # Publish balance refunded event
                await self.event_publisher.publish_balance_refunded({
                    "student_id": student_id,
                    "lesson_id": lesson_id,
                    "lessons_refunded": 1,
                    "reason": cancellation_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": event.get('correlation_id')
                })
                
                logger.info(f"Refunded balance for student {student_id} due to {cancellation_type} cancellation")
            else:
                logger.info(f"No refund for {cancellation_type} cancellation")
            
        except Exception as e:
            logger.error(f"Error handling lesson cancelled event: {e}")
            # TODO: Send to dead letter queue
    
    async def handle_student_created(self, event: Dict[str, Any]):
        """
        Handle student creation event
        Create initial balance record
        """
        try:
            student_id = event.get('student_id')
            logger.info(f"Processing student created event: student_id={student_id}")
            
            # Create balance record
            await self.balance_service.get_balance(student_id)  # This creates if not exists
            
            logger.info(f"Created balance record for student {student_id}")
            
        except Exception as e:
            logger.error(f"Error handling student created event: {e}")
    
    async def handle_lesson_rescheduled(self, event: Dict[str, Any]):
        """
        Handle lesson rescheduled event
        Usually no payment action needed, just log
        """
        try:
            lesson_id = event.get('lesson_id')
            student_id = event.get('student_id')
            old_date = event.get('old_date')
            new_date = event.get('new_date')
            
            logger.info(f"Lesson rescheduled: lesson_id={lesson_id}, student_id={student_id}")
            logger.info(f"From {old_date} to {new_date}")
            
            # Typically no payment action needed for reschedules
            # But we can track it for analytics
            
        except Exception as e:
            logger.error(f"Error handling lesson rescheduled event: {e}")
    
    async def handle_student_deleted(self, event: Dict[str, Any]):
        """
        Handle student deletion event
        May need to handle remaining balance
        """
        try:
            student_id = event.get('student_id')
            deletion_reason = event.get('reason', 'unknown')
            
            logger.info(f"Student deleted: student_id={student_id}, reason={deletion_reason}")
            
            # Get current balance
            balance = await self.balance_service.get_balance(student_id)
            if balance and balance.current_balance > 0:
                logger.warning(f"Student {student_id} deleted with remaining balance: {balance.current_balance} lessons")
                # Could trigger refund process or transfer to parent account
            
        except Exception as e:
            logger.error(f"Error handling student deleted event: {e}")
    
    async def handle_payment_created(self, payment_id: int, student_id: int, lessons_paid: int, amount: Decimal):
        """
        Handle internal payment creation
        Publish event to notify other services
        """
        try:
            await self.event_publisher.publish_payment_processed({
                "payment_id": payment_id,
                "student_id": student_id,
                "lessons_paid": lessons_paid,
                "amount": float(amount),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            await self.event_publisher.publish_balance_updated({
                "student_id": student_id,
                "balance_change": lessons_paid,
                "change_type": "payment",
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error publishing payment events: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check event handler health"""
        return {
            "is_running": self.is_running,
            "rabbitmq_connected": await self.rabbitmq_client.health_check() if self.rabbitmq_client else False,
            "consumers_active": len(self.rabbitmq_client.consumers) if self.rabbitmq_client else 0
        }


class MockEventHandler(PaymentEventHandler):
    """Mock event handler for testing and development"""
    
    async def start(self):
        """Start mock event handler"""
        self.is_running = True
        logger.info("Mock Payment Event Handler started")
    
    async def stop(self):
        """Stop mock event handler"""
        self.is_running = False
        logger.info("Mock Payment Event Handler stopped")
    
    async def simulate_lesson_completed(self, student_id: int, lesson_id: int, lesson_topic: str = "Math"):
        """Simulate lesson completed event for testing"""
        event = {
            "lesson_id": lesson_id,
            "student_id": student_id,
            "lesson_price": float(settings.DEFAULT_PRICE_PER_LESSON),
            "lesson_topic": lesson_topic,
            "lesson_date": datetime.utcnow().isoformat()
        }
        await self.handle_lesson_completed(event)
    
    async def simulate_lesson_cancelled(self, student_id: int, lesson_id: int, cancellation_type: str = "excused"):
        """Simulate lesson cancelled event for testing"""
        event = {
            "lesson_id": lesson_id,
            "student_id": student_id,
            "cancellation_type": cancellation_type,
            "lesson_price": float(settings.DEFAULT_PRICE_PER_LESSON),
            "lesson_topic": "Math"
        }
        await self.handle_lesson_cancelled(event)
    
    async def simulate_student_created(self, student_id: int):
        """Simulate student created event for testing"""
        event = {
            "student_id": student_id,
            "student_name": f"Test Student {student_id}",
            "created_at": datetime.utcnow().isoformat()
        }
        await self.handle_student_created(event)