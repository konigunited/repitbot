"""
Event Publisher for Analytics Service
Publishes analytics-related events to RabbitMQ
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import aio_pika
from aio_pika import connect, Message
import os

logger = logging.getLogger(__name__)

class AnalyticsEventPublisher:
    """Event publisher for analytics service"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        """Connect to RabbitMQ"""
        try:
            rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
            self.connection = await connect(rabbitmq_url)
            self.channel = await self.connection.channel()
            
            # Declare analytics exchange
            self.exchange = await self.channel.declare_exchange(
                "analytics.notifications", 
                aio_pika.ExchangeType.TOPIC, 
                durable=True
            )
            
            logger.info("Connected to RabbitMQ for analytics event publishing")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    async def publish_event(
        self, 
        event_type: str, 
        event_data: Dict[str, Any],
        routing_key: Optional[str] = None
    ):
        """Publish analytics event"""
        try:
            if not self.exchange:
                await self.connect()
            
            # Add metadata
            event_data.update({
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "service": "analytics-service"
            })
            
            # Create message
            message = Message(
                json.dumps(event_data).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            
            # Use routing key or default
            routing_key = routing_key or f"analytics.{event_type}"
            
            # Publish message
            await self.exchange.publish(message, routing_key=routing_key)
            
            logger.info(f"Published analytics event: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {str(e)}")
            raise

    async def publish_report_generated(
        self,
        report_id: str,
        report_type: str,
        user_id: int,
        format: str,
        file_path: str
    ):
        """Publish report generation completion event"""
        await self.publish_event(
            "report.generated",
            {
                "report_id": report_id,
                "report_type": report_type,
                "user_id": user_id,
                "format": format,
                "file_path": file_path,
                "generated_at": datetime.now().isoformat()
            },
            "analytics.report.generated"
        )

    async def publish_chart_generated(
        self,
        chart_type: str,
        user_id: int,
        chart_data: Dict[str, Any],
        parameters: Dict[str, Any]
    ):
        """Publish chart generation event"""
        await self.publish_event(
            "chart.generated",
            {
                "chart_type": chart_type,
                "user_id": user_id,
                "chart_data": chart_data,
                "parameters": parameters,
                "generated_at": datetime.now().isoformat()
            },
            "analytics.chart.generated"
        )

    async def publish_analytics_threshold_alert(
        self,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        severity: str,
        affected_entities: list
    ):
        """Publish analytics threshold alert"""
        await self.publish_event(
            "threshold.alert",
            {
                "metric_name": metric_name,
                "current_value": current_value,
                "threshold_value": threshold_value,
                "severity": severity,
                "affected_entities": affected_entities,
                "alert_time": datetime.now().isoformat()
            },
            f"analytics.alert.{severity}"
        )

    async def publish_dashboard_accessed(
        self,
        user_id: int,
        dashboard_type: str,
        filters: Dict[str, Any],
        access_time: datetime
    ):
        """Publish dashboard access event"""
        await self.publish_event(
            "dashboard.accessed",
            {
                "user_id": user_id,
                "dashboard_type": dashboard_type,
                "filters": filters,
                "access_time": access_time.isoformat()
            },
            "analytics.dashboard.accessed"
        )

    async def close(self):
        """Close connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Analytics event publisher connection closed")

# Global publisher instance
analytics_publisher = AnalyticsEventPublisher()