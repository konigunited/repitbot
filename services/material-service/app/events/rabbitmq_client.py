# -*- coding: utf-8 -*-
"""
RabbitMQ Client for Material Service
Handles connection, publishing, and consuming events
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import aio_pika
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel
from aio_pika import connect_robust, ExchangeType, Message

from ..core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """RabbitMQ client for event-driven communication"""
    
    def __init__(self):
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel: Optional[AbstractRobustChannel] = None
        self.exchange = None
        self.is_connected = False
        self.consumers = {}
        
    async def connect(self) -> bool:
        """Establish connection to RabbitMQ"""
        try:
            logger.info(f"Connecting to RabbitMQ: {settings.RABBITMQ_URL}")
            
            # Establish connection
            self.connection = await connect_robust(
                settings.RABBITMQ_URL,
                loop=asyncio.get_event_loop()
            )
            
            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=settings.EVENT_PROCESSING_BATCH_SIZE)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                ExchangeType.TOPIC,
                durable=True
            )
            
            self.is_connected = True
            logger.info("Successfully connected to RabbitMQ")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            self.is_connected = False
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    async def publish_event(self, routing_key: str, event_data: Dict[str, Any]) -> bool:
        """Publish event to exchange"""
        if not self.is_connected or not self.exchange:
            logger.error("Not connected to RabbitMQ")
            return False
        
        try:
            # Prepare event message
            event_message = {
                "event_type": routing_key.split('.')[-1],
                "data": event_data,
                "service": "material-service",
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": event_data.get('correlation_id'),
                "version": "1.0"
            }
            
            # Create message
            message = Message(
                json.dumps(event_message).encode(),
                content_type="application/json",
                delivery_mode=2,  # Persistent
                timestamp=datetime.utcnow()
            )
            
            # Publish to exchange
            await self.exchange.publish(
                message,
                routing_key=routing_key
            )
            
            logger.info(f"Published event: {routing_key}")
            logger.debug(f"Event data: {json.dumps(event_message, indent=2)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {routing_key}: {e}")
            return False
    
    async def create_consumer(
        self,
        queue_name: str,
        routing_keys: list,
        handler: Callable,
        dead_letter_exchange: str = None
    ):
        """Create consumer for specific routing keys"""
        if not self.is_connected or not self.channel:
            logger.error("Not connected to RabbitMQ")
            return
        
        try:
            # Declare queue arguments
            queue_args = {}
            if dead_letter_exchange:
                queue_args = {
                    "x-dead-letter-exchange": dead_letter_exchange,
                    "x-dead-letter-routing-key": f"dlq.{queue_name}"
                }
            
            # Declare queue
            queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                arguments=queue_args
            )
            
            # Bind queue to routing keys
            for routing_key in routing_keys:
                await queue.bind(self.exchange, routing_key)
                logger.info(f"Bound queue {queue_name} to {routing_key}")
            
            # Create consumer
            async def message_handler(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        # Parse message
                        event_data = json.loads(message.body.decode())
                        logger.info(f"Received event: {event_data.get('event_type')} on {queue_name}")
                        
                        # Handle event
                        await handler(event_data)
                        
                    except Exception as e:
                        logger.error(f"Error processing message in {queue_name}: {e}")
                        raise
            
            # Start consuming
            consumer_tag = await queue.consume(message_handler)
            self.consumers[queue_name] = consumer_tag
            
            logger.info(f"Started consumer for queue: {queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to create consumer for {queue_name}: {e}")
    
    async def stop_consumer(self, queue_name: str):
        """Stop specific consumer"""
        if queue_name in self.consumers:
            try:
                await self.consumers[queue_name].cancel()
                del self.consumers[queue_name]
                logger.info(f"Stopped consumer for queue: {queue_name}")
            except Exception as e:
                logger.error(f"Error stopping consumer {queue_name}: {e}")
    
    async def setup_dead_letter_queue(self, original_queue_name: str):
        """Setup dead letter queue for failed messages"""
        if not self.is_connected or not self.channel:
            return
        
        try:
            dlq_exchange_name = f"dlq.{settings.RABBITMQ_EXCHANGE}"
            dlq_queue_name = f"dlq.{original_queue_name}"
            
            # Declare DLQ exchange
            dlq_exchange = await self.channel.declare_exchange(
                dlq_exchange_name,
                ExchangeType.DIRECT,
                durable=True
            )
            
            # Declare DLQ queue
            dlq_queue = await self.channel.declare_queue(
                dlq_queue_name,
                durable=True
            )
            
            # Bind DLQ
            await dlq_queue.bind(dlq_exchange, f"dlq.{original_queue_name}")
            
            logger.info(f"Setup dead letter queue: {dlq_queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup DLQ for {original_queue_name}: {e}")
    
    async def health_check(self) -> bool:
        """Check RabbitMQ connection health"""
        try:
            if not self.connection or self.connection.is_closed:
                return False
            
            # Try to declare a temporary exchange to test connection
            temp_exchange = await self.channel.declare_exchange(
                "health_check_temp",
                ExchangeType.DIRECT,
                auto_delete=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return False


class MaterialEventPublisher:
    """Helper class for publishing specific material events"""
    
    def __init__(self, rabbitmq_client: RabbitMQClient):
        self.client = rabbitmq_client
    
    async def publish_material_created(self, material_data: Dict[str, Any]):
        """Publish material created event"""
        await self.client.publish_event(
            "material.created",
            material_data
        )
    
    async def publish_material_updated(self, material_data: Dict[str, Any]):
        """Publish material updated event"""
        await self.client.publish_event(
            "material.updated",
            material_data
        )
    
    async def publish_material_deleted(self, material_data: Dict[str, Any]):
        """Publish material deleted event"""
        await self.client.publish_event(
            "material.deleted",
            material_data
        )
    
    async def publish_file_uploaded(self, file_data: Dict[str, Any]):
        """Publish file uploaded event"""
        await self.client.publish_event(
            "material.file.uploaded",
            file_data
        )
    
    async def publish_file_downloaded(self, download_data: Dict[str, Any]):
        """Publish file downloaded event"""
        await self.client.publish_event(
            "material.file.downloaded",
            download_data
        )
    
    async def publish_material_accessed(self, access_data: Dict[str, Any]):
        """Publish material accessed event"""
        await self.client.publish_event(
            "material.accessed",
            access_data
        )


class MockRabbitMQClient(RabbitMQClient):
    """Mock RabbitMQ client for testing and development"""
    
    async def connect(self) -> bool:
        """Mock connection"""
        self.is_connected = True
        logger.info("Mock RabbitMQ client connected")
        return True
    
    async def disconnect(self):
        """Mock disconnection"""
        self.is_connected = False
        logger.info("Mock RabbitMQ client disconnected")
    
    async def publish_event(self, routing_key: str, event_data: Dict[str, Any]) -> bool:
        """Mock event publishing"""
        logger.info(f"Mock published event: {routing_key}")
        logger.debug(f"Event data: {json.dumps(event_data, indent=2)}")
        return True
    
    async def create_consumer(self, queue_name: str, routing_keys: list, handler: Callable, dead_letter_exchange: str = None):
        """Mock consumer creation"""
        logger.info(f"Mock consumer created for {queue_name} with keys: {routing_keys}")
    
    async def health_check(self) -> bool:
        """Mock health check"""
        return self.is_connected