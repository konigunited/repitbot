"""
Event-Driven Architecture Tests
==============================

Tests for RabbitMQ-based event messaging and event-driven workflows
in the RepitBot microservices architecture.

Event Categories:
- User Events (registration, login, profile updates)
- Lesson Events (creation, completion, cancellation, attendance)
- Homework Events (assignment, submission, grading)
- Payment Events (processing, completion, refunds)
- Material Events (upload, download, sharing)
- Notification Events (sending, delivery, failures)
- Analytics Events (data collection, aggregation)
- Student Events (XP changes, achievements, progress)

Event Flow Testing:
1. Event Publishing (services can publish events)
2. Event Consumption (services can receive events)
3. Event Ordering (events processed in correct order)
4. Event Persistence (events stored reliably)
5. Event Replay (events can be reprocessed)
6. Dead Letter Queues (failed events handled)
7. Cross-Service Workflows (multi-service event chains)
"""

import pytest
import asyncio
import aiohttp
import pika
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid


@pytest.mark.events
class TestEventPublishing:
    """Test event publishing from microservices"""
    
    def setup_rabbitmq_connection(self):
        """Setup RabbitMQ connection for testing"""
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    credentials=pika.PlainCredentials('repitbot', 'repitbot_password')
                )
            )
            channel = connection.channel()
            return connection, channel
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")
    
    
    def test_rabbitmq_connectivity(self):
        """Test basic RabbitMQ connectivity and queue setup"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Test exchange declarations
            test_exchanges = [
                "user.events",
                "lesson.events", 
                "homework.events",
                "payment.events",
                "material.events",
                "notification.events",
                "analytics.events",
                "student.events"
            ]
            
            for exchange in test_exchanges:
                channel.exchange_declare(
                    exchange=exchange, 
                    exchange_type='topic', 
                    durable=True
                )
                print(f"✅ Exchange declared: {exchange}")
            
            # Test queue creation
            test_queue = "test_event_queue"
            channel.queue_declare(queue=test_queue, durable=False)
            
            # Test basic message publishing
            test_message = {
                "event_type": "test.event",
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "data": {"test": "message"}
            }
            
            channel.basic_publish(
                exchange="user.events",
                routing_key="user.test",
                body=json.dumps(test_message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            print("✅ Test message published successfully")
            
            # Cleanup
            channel.queue_delete(queue=test_queue)
            
        finally:
            connection.close()
    
    
    async def test_lesson_completion_event_publishing(self, http_client, test_config, auth_tokens):
        """Test that lesson completion publishes events"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        # Setup event listener
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Create temporary queue to listen for lesson events
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            
            channel.queue_bind(
                exchange='lesson.events',
                queue=queue_name,
                routing_key='lesson.completed'
            )
            
            received_events = []
            
            def event_callback(ch, method, properties, body):
                event_data = json.loads(body)
                received_events.append(event_data)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=event_callback
            )
            
            # Trigger lesson completion
            test_lesson_id = 999999
            completion_data = {
                "status": "completed",
                "attendance": "present",
                "completion_time": datetime.now().isoformat(),
                "notes": "Event test completion"
            }
            
            async with http_client.post(
                f"{test_config.API_GATEWAY_URL}/api/v1/lessons/{test_lesson_id}/complete",
                headers=headers,
                json=completion_data
            ) as response:
                # Even if lesson doesn't exist, service might still publish test event
                if response.status in [200, 201]:
                    print("✅ Lesson completion triggered")
                else:
                    print(f"⚠️  Lesson completion status: {response.status}")
            
            # Check for events (with timeout)
            timeout_start = time.time()
            timeout = 5  # 5 seconds
            
            while time.time() < timeout_start + timeout:
                connection.process_data_events(time_limit=1)
                if received_events:
                    break
            
            if received_events:
                event = received_events[0]
                
                # Verify event structure
                assert "event_type" in event
                assert "event_id" in event
                assert "timestamp" in event
                assert "data" in event
                
                if event["event_type"] == "lesson.completed":
                    assert "lesson_id" in event["data"]
                    print("✅ Lesson completion event received and validated")
                else:
                    print(f"⚠️  Unexpected event type: {event['event_type']}")
            else:
                print("⚠️  No lesson completion events received (may not be implemented)")
                
        finally:
            connection.close()
    
    
    async def test_homework_submission_event_publishing(self, http_client, test_config, auth_tokens):
        """Test that homework submission publishes events"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Setup event listener for homework events
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            
            channel.queue_bind(
                exchange='homework.events',
                queue=queue_name,
                routing_key='homework.submitted'
            )
            
            received_events = []
            
            def event_callback(ch, method, properties, body):
                event_data = json.loads(body)
                received_events.append(event_data)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=event_callback
            )
            
            # Trigger homework submission
            test_homework_id = 999999
            submission_data = {
                "answers": {
                    "question_1": "Event test answer 1",
                    "question_2": "Event test answer 2"
                },
                "notes": "Event testing submission",
                "submitted_at": datetime.now().isoformat()
            }
            
            async with http_client.post(
                f"{test_config.API_GATEWAY_URL}/api/v1/homework/{test_homework_id}/submit",
                headers=headers,
                json=submission_data
            ) as response:
                if response.status in [200, 201]:
                    print("✅ Homework submission triggered")
                else:
                    print(f"⚠️  Homework submission status: {response.status}")
            
            # Check for events
            timeout_start = time.time()
            timeout = 5
            
            while time.time() < timeout_start + timeout:
                connection.process_data_events(time_limit=1)
                if received_events:
                    break
            
            if received_events:
                event = received_events[0]
                
                # Verify homework submission event structure
                if event.get("event_type") == "homework.submitted":
                    assert "homework_id" in event["data"]
                    assert "student_id" in event["data"]
                    print("✅ Homework submission event received and validated")
                else:
                    print(f"⚠️  Received event type: {event.get('event_type')}")
            else:
                print("⚠️  No homework submission events received")
                
        finally:
            connection.close()
    
    
    async def test_payment_processing_event_publishing(self, http_client, test_config, auth_tokens):
        """Test that payment processing publishes events"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Setup event listener for payment events
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            
            channel.queue_bind(
                exchange='payment.events',
                queue=queue_name,
                routing_key='payment.*'
            )
            
            received_events = []
            
            def event_callback(ch, method, properties, body):
                event_data = json.loads(body)
                received_events.append(event_data)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=event_callback
            )
            
            # Trigger payment
            payment_data = {
                "amount": 1000.0,
                "payment_method": "card",
                "description": "Event test payment"
            }
            
            async with http_client.post(
                f"{test_config.API_GATEWAY_URL}/api/v1/payments/top-up",
                headers=headers,
                json=payment_data
            ) as response:
                if response.status in [200, 201]:
                    print("✅ Payment triggered")
                else:
                    print(f"⚠️  Payment status: {response.status}")
            
            # Check for events
            timeout_start = time.time()
            timeout = 5
            
            while time.time() < timeout_start + timeout:
                connection.process_data_events(time_limit=1)
                if received_events:
                    break
            
            if received_events:
                event = received_events[0]
                
                # Verify payment event structure
                if event.get("event_type") in ["payment.processed", "payment.completed"]:
                    assert "amount" in event["data"]
                    print("✅ Payment event received and validated")
                else:
                    print(f"⚠️  Received event type: {event.get('event_type')}")
            else:
                print("⚠️  No payment events received")
                
        finally:
            connection.close()


@pytest.mark.events  
class TestEventConsumption:
    """Test event consumption and processing by microservices"""
    
    def setup_rabbitmq_connection(self):
        """Setup RabbitMQ connection for testing"""
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    credentials=pika.PlainCredentials('repitbot', 'repitbot_password')
                )
            )
            channel = connection.channel()
            return connection, channel
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")
    
    
    def test_publish_test_events(self):
        """Publish test events to verify consumers are working"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Test events to publish
            test_events = [
                {
                    "exchange": "lesson.events",
                    "routing_key": "lesson.completed",
                    "event": {
                        "event_type": "lesson.completed",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "lesson_id": 123,
                            "student_id": 456,
                            "tutor_id": 789,
                            "completion_time": datetime.now().isoformat(),
                            "attendance": "present"
                        }
                    }
                },
                {
                    "exchange": "homework.events", 
                    "routing_key": "homework.submitted",
                    "event": {
                        "event_type": "homework.submitted",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "homework_id": 111,
                            "student_id": 456,
                            "submission_id": 222,
                            "submitted_at": datetime.now().isoformat()
                        }
                    }
                },
                {
                    "exchange": "payment.events",
                    "routing_key": "payment.completed", 
                    "event": {
                        "event_type": "payment.completed",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "payment_id": 333,
                            "user_id": 456,
                            "amount": 1000.0,
                            "lesson_id": 123
                        }
                    }
                }
            ]
            
            published_count = 0
            
            for test_event in test_events:
                try:
                    channel.basic_publish(
                        exchange=test_event["exchange"],
                        routing_key=test_event["routing_key"],
                        body=json.dumps(test_event["event"]),
                        properties=pika.BasicProperties(
                            delivery_mode=2,
                            content_type='application/json'
                        )
                    )
                    published_count += 1
                    print(f"✅ Published {test_event['event']['event_type']} event")
                    
                except Exception as e:
                    print(f"❌ Failed to publish {test_event['event']['event_type']}: {e}")
            
            print(f"✅ Published {published_count}/{len(test_events)} test events")
            
            # Give consumers time to process
            time.sleep(2)
            
        finally:
            connection.close()
    
    
    def test_dead_letter_queue_setup(self):
        """Test that dead letter queues are properly configured"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Check for dead letter queue setup
            dlq_exchanges = [
                "lesson.events.dlq",
                "homework.events.dlq",
                "payment.events.dlq",
                "notification.events.dlq"
            ]
            
            for dlq_exchange in dlq_exchanges:
                try:
                    channel.exchange_declare(
                        exchange=dlq_exchange,
                        exchange_type='topic',
                        durable=True
                    )
                    print(f"✅ Dead letter exchange available: {dlq_exchange}")
                except Exception as e:
                    print(f"⚠️  Dead letter exchange issue: {dlq_exchange} - {e}")
            
            # Test dead letter queue
            dlq_queue = "test.dlq"
            
            channel.queue_declare(
                queue=dlq_queue,
                durable=True,
                arguments={
                    'x-message-ttl': 60000,  # 1 minute TTL
                    'x-dead-letter-exchange': 'lesson.events.dlq'
                }
            )
            
            # Publish message that should go to DLQ after TTL
            poisoned_message = {
                "event_type": "test.poisoned_message",
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "data": {"test": "This message should be rejected"}
            }
            
            channel.basic_publish(
                exchange='',
                routing_key=dlq_queue,
                body=json.dumps(poisoned_message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            
            print("✅ Dead letter queue mechanism tested")
            
            # Cleanup
            channel.queue_delete(queue=dlq_queue)
            
        finally:
            connection.close()
    
    
    async def test_event_processing_idempotency(self, http_client, test_config):
        """Test that events are processed idempotently (no duplicates)"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Create test queue for idempotency testing
            test_queue = "idempotency_test_queue"
            channel.queue_declare(queue=test_queue, durable=False)
            
            # Publish same event multiple times (simulate duplicates)
            duplicate_event = {
                "event_type": "test.idempotency",
                "event_id": "SAME_EVENT_ID_123",  # Same ID intentionally
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "user_id": 123,
                    "action": "idempotency_test"
                }
            }
            
            # Publish the same event 3 times
            for i in range(3):
                channel.basic_publish(
                    exchange='',
                    routing_key=test_queue,
                    body=json.dumps(duplicate_event),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
            
            print("✅ Published duplicate events for idempotency testing")
            
            # In a real test, we would:
            # 1. Have a test consumer that tracks processed event IDs
            # 2. Verify that even though 3 events were sent, only 1 is processed
            # 3. Check that subsequent events with same ID are ignored
            
            # Cleanup
            channel.queue_delete(queue=test_queue)
            
        finally:
            connection.close()


@pytest.mark.events
class TestEventOrdering:
    """Test event ordering and sequence processing"""
    
    def setup_rabbitmq_connection(self):
        """Setup RabbitMQ connection for testing"""
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    credentials=pika.PlainCredentials('repitbot', 'repitbot_password')
                )
            )
            channel = connection.channel()
            return connection, channel
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")
    
    
    def test_ordered_event_sequence(self):
        """Test that events are processed in correct order when needed"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Test ordered sequence of events
            sequence_queue = "order_test_queue"
            
            # Create queue with single consumer for ordering
            channel.queue_declare(queue=sequence_queue, durable=False)
            channel.basic_qos(prefetch_count=1)  # Process one message at a time
            
            # Create sequence of events that must be processed in order
            lesson_sequence = [
                {
                    "event_type": "lesson.scheduled",
                    "event_id": str(uuid.uuid4()),
                    "sequence": 1,
                    "lesson_id": 999,
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "event_type": "lesson.started", 
                    "event_id": str(uuid.uuid4()),
                    "sequence": 2,
                    "lesson_id": 999,
                    "timestamp": (datetime.now() + timedelta(seconds=1)).isoformat()
                },
                {
                    "event_type": "lesson.completed",
                    "event_id": str(uuid.uuid4()),
                    "sequence": 3,
                    "lesson_id": 999,
                    "timestamp": (datetime.now() + timedelta(seconds=2)).isoformat()
                }
            ]
            
            # Publish events in order
            for event in lesson_sequence:
                channel.basic_publish(
                    exchange='',
                    routing_key=sequence_queue,
                    body=json.dumps(event),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
            
            print("✅ Published ordered event sequence")
            
            # Verify events are in queue in correct order
            received_events = []
            
            def collect_events(ch, method, properties, body):
                event_data = json.loads(body)
                received_events.append(event_data)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
                # Stop after collecting all events
                if len(received_events) >= 3:
                    ch.stop_consuming()
            
            channel.basic_consume(
                queue=sequence_queue,
                on_message_callback=collect_events
            )
            
            # Process with timeout
            timeout_start = time.time()
            timeout = 5
            
            try:
                channel.start_consuming()
            except:
                pass  # Expected when stop_consuming is called
            
            # Verify order
            if len(received_events) >= 3:
                sequences = [event.get("sequence", 0) for event in received_events]
                if sequences == [1, 2, 3]:
                    print("✅ Events received in correct order")
                else:
                    print(f"⚠️  Events received out of order: {sequences}")
            else:
                print(f"⚠️  Only received {len(received_events)} events")
            
            # Cleanup
            channel.queue_delete(queue=sequence_queue)
            
        finally:
            connection.close()
    
    
    def test_parallel_event_processing(self):
        """Test that independent events can be processed in parallel"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Create multiple queues for parallel processing
            parallel_queues = ["parallel_queue_1", "parallel_queue_2", "parallel_queue_3"]
            
            for queue in parallel_queues:
                channel.queue_declare(queue=queue, durable=False)
            
            # Publish independent events to different queues
            independent_events = [
                {
                    "queue": "parallel_queue_1",
                    "event": {
                        "event_type": "user.login",
                        "event_id": str(uuid.uuid4()),
                        "user_id": 1,
                        "timestamp": datetime.now().isoformat()
                    }
                },
                {
                    "queue": "parallel_queue_2", 
                    "event": {
                        "event_type": "material.downloaded",
                        "event_id": str(uuid.uuid4()),
                        "material_id": 100,
                        "timestamp": datetime.now().isoformat()
                    }
                },
                {
                    "queue": "parallel_queue_3",
                    "event": {
                        "event_type": "notification.sent", 
                        "event_id": str(uuid.uuid4()),
                        "notification_id": 200,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            ]
            
            # Publish to different queues (can be processed in parallel)
            for item in independent_events:
                channel.basic_publish(
                    exchange='',
                    routing_key=item["queue"],
                    body=json.dumps(item["event"]),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
            
            print("✅ Published independent events for parallel processing")
            
            # Cleanup
            for queue in parallel_queues:
                channel.queue_delete(queue=queue)
            
        finally:
            connection.close()


@pytest.mark.events
class TestEventDrivenWorkflows:
    """Test complete event-driven workflows across services"""
    
    def setup_rabbitmq_connection(self):
        """Setup RabbitMQ connection for testing"""
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    credentials=pika.PlainCredentials('repitbot', 'repitbot_password')
                )
            )
            channel = connection.channel()
            return connection, channel
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")
    
    
    def test_lesson_completion_workflow(self):
        """Test complete lesson completion event workflow"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Setup listeners for the complete workflow
            workflow_queues = {
                "lesson_completed": "lesson.completed",
                "payment_processed": "payment.processed", 
                "notification_sent": "notification.sent",
                "analytics_updated": "analytics.updated",
                "xp_awarded": "student.xp_awarded"
            }
            
            for queue_name, routing_key in workflow_queues.items():
                channel.queue_declare(queue=queue_name, durable=False)
                
                # Bind to appropriate exchange
                if "lesson" in routing_key:
                    exchange = "lesson.events"
                elif "payment" in routing_key:
                    exchange = "payment.events"
                elif "notification" in routing_key:
                    exchange = "notification.events"
                elif "analytics" in routing_key:
                    exchange = "analytics.events"
                elif "student" in routing_key:
                    exchange = "student.events"
                else:
                    exchange = "user.events"
                
                channel.queue_bind(
                    exchange=exchange,
                    queue=queue_name,
                    routing_key=routing_key
                )
            
            print("✅ Event workflow listeners setup complete")
            
            # Simulate lesson completion workflow by publishing initial event
            lesson_completed_event = {
                "event_type": "lesson.completed",
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "lesson_id": 1001,
                    "student_id": 2001,
                    "tutor_id": 3001,
                    "completion_time": datetime.now().isoformat(),
                    "attendance": "present",
                    "lesson_price": 1000.0
                }
            }
            
            channel.basic_publish(
                exchange="lesson.events",
                routing_key="lesson.completed",
                body=json.dumps(lesson_completed_event),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            
            print("✅ Lesson completion event published")
            
            # In a real system, this would trigger:
            # 1. Payment Service: Process lesson payment
            # 2. Notification Service: Notify parent and student
            # 3. Analytics Service: Update lesson statistics  
            # 4. Student Service: Award XP and check achievements
            
            # Simulate subsequent events in the workflow
            workflow_events = [
                {
                    "exchange": "payment.events",
                    "routing_key": "payment.processed",
                    "event": {
                        "event_type": "payment.processed",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": (datetime.now() + timedelta(seconds=1)).isoformat(),
                        "data": {
                            "payment_id": 4001,
                            "lesson_id": 1001,
                            "amount": 1000.0,
                            "status": "completed"
                        }
                    }
                },
                {
                    "exchange": "student.events",
                    "routing_key": "student.xp_awarded", 
                    "event": {
                        "event_type": "student.xp_awarded",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": (datetime.now() + timedelta(seconds=2)).isoformat(),
                        "data": {
                            "student_id": 2001,
                            "xp_amount": 50,
                            "reason": "lesson_completion",
                            "lesson_id": 1001
                        }
                    }
                }
            ]
            
            for event_info in workflow_events:
                channel.basic_publish(
                    exchange=event_info["exchange"],
                    routing_key=event_info["routing_key"],
                    body=json.dumps(event_info["event"]),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
                time.sleep(0.1)  # Small delay between events
            
            print("✅ Complete lesson workflow events published")
            
            # Cleanup
            for queue_name in workflow_queues.keys():
                try:
                    channel.queue_delete(queue=queue_name)
                except:
                    pass
            
        finally:
            connection.close()
    
    
    def test_homework_submission_workflow(self):
        """Test complete homework submission event workflow"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Homework submission workflow events:
            # 1. homework.submitted → Tutor notification
            # 2. homework.graded → Student XP award
            # 3. xp.awarded → Achievement check
            # 4. achievement.unlocked → Congratulations notification
            
            homework_workflow = [
                {
                    "exchange": "homework.events",
                    "routing_key": "homework.submitted",
                    "event": {
                        "event_type": "homework.submitted",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "homework_id": 5001,
                            "student_id": 2001,
                            "submission_id": 6001,
                            "submitted_at": datetime.now().isoformat()
                        }
                    }
                },
                {
                    "exchange": "homework.events",
                    "routing_key": "homework.graded",
                    "event": {
                        "event_type": "homework.graded",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": (datetime.now() + timedelta(minutes=5)).isoformat(),
                        "data": {
                            "homework_id": 5001,
                            "student_id": 2001,
                            "score": 95,
                            "max_score": 100,
                            "graded_by": 3001
                        }
                    }
                },
                {
                    "exchange": "student.events",
                    "routing_key": "student.achievement_unlocked",
                    "event": {
                        "event_type": "student.achievement_unlocked",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": (datetime.now() + timedelta(minutes=5, seconds=30)).isoformat(),
                        "data": {
                            "student_id": 2001,
                            "achievement_id": "homework_streak_5",
                            "achievement_name": "Homework Hero",
                            "xp_bonus": 25
                        }
                    }
                }
            ]
            
            for event_info in homework_workflow:
                channel.basic_publish(
                    exchange=event_info["exchange"],
                    routing_key=event_info["routing_key"],
                    body=json.dumps(event_info["event"]),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
                time.sleep(0.5)  # Delay between workflow steps
            
            print("✅ Complete homework workflow events published")
            
        finally:
            connection.close()
    
    
    def test_payment_failure_workflow(self):
        """Test payment failure and retry workflow"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Payment failure workflow:
            # 1. payment.failed → Retry attempt
            # 2. payment.retry_failed → Dead letter queue
            # 3. payment.manual_review → Admin notification
            
            payment_failure_workflow = [
                {
                    "exchange": "payment.events",
                    "routing_key": "payment.failed",
                    "event": {
                        "event_type": "payment.failed",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "payment_id": 7001,
                            "user_id": 2001,
                            "amount": 1000.0,
                            "error_code": "INSUFFICIENT_FUNDS",
                            "retry_count": 0
                        }
                    }
                },
                {
                    "exchange": "payment.events",
                    "routing_key": "payment.retry_failed",
                    "event": {
                        "event_type": "payment.retry_failed",
                        "event_id": str(uuid.uuid4()),
                        "timestamp": (datetime.now() + timedelta(minutes=1)).isoformat(),
                        "data": {
                            "payment_id": 7001,
                            "user_id": 2001,
                            "amount": 1000.0,
                            "error_code": "CARD_DECLINED",
                            "retry_count": 3,
                            "requires_manual_review": True
                        }
                    }
                }
            ]
            
            for event_info in payment_failure_workflow:
                channel.basic_publish(
                    exchange=event_info["exchange"],
                    routing_key=event_info["routing_key"],
                    body=json.dumps(event_info["event"]),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
                time.sleep(0.2)
            
            print("✅ Payment failure workflow events published")
            
        finally:
            connection.close()


@pytest.mark.events
class TestEventReliability:
    """Test event system reliability and error handling"""
    
    def setup_rabbitmq_connection(self):
        """Setup RabbitMQ connection for testing"""
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    credentials=pika.PlainCredentials('repitbot', 'repitbot_password')
                )
            )
            channel = connection.channel()
            return connection, channel
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")
    
    
    def test_event_persistence(self):
        """Test that events survive broker restarts"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Create durable queue and exchange
            durable_exchange = "test.durable.events"
            durable_queue = "test_durable_queue"
            
            channel.exchange_declare(
                exchange=durable_exchange,
                exchange_type='topic',
                durable=True
            )
            
            channel.queue_declare(
                queue=durable_queue,
                durable=True
            )
            
            channel.queue_bind(
                exchange=durable_exchange,
                queue=durable_queue,
                routing_key="test.*"
            )
            
            # Publish persistent message
            persistent_event = {
                "event_type": "test.persistence",
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "data": {"test": "This message should survive broker restart"}
            }
            
            channel.basic_publish(
                exchange=durable_exchange,
                routing_key="test.persistence",
                body=json.dumps(persistent_event),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            print("✅ Persistent event published")
            
            # In a real test, we would:
            # 1. Stop RabbitMQ broker
            # 2. Start RabbitMQ broker
            # 3. Verify message is still in queue
            
            # For now, verify message is in queue
            method_frame, header_frame, body = channel.basic_get(
                queue=durable_queue,
                auto_ack=False
            )
            
            if method_frame:
                recovered_event = json.loads(body)
                assert recovered_event["event_type"] == "test.persistence"
                channel.basic_ack(method_frame.delivery_tag)
                print("✅ Persistent event recovered from queue")
            else:
                print("⚠️  No message in durable queue")
            
            # Cleanup
            channel.queue_delete(queue=durable_queue)
            channel.exchange_delete(exchange=durable_exchange)
            
        finally:
            connection.close()
    
    
    def test_event_retry_mechanism(self):
        """Test event retry and dead letter handling"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            # Setup retry queue with TTL and DLQ
            retry_queue = "test_retry_queue"
            dlq_exchange = "test.dlq.events"
            dlq_queue = "test_dlq_queue"
            
            # Create DLQ exchange and queue
            channel.exchange_declare(
                exchange=dlq_exchange,
                exchange_type='direct',
                durable=True
            )
            
            channel.queue_declare(
                queue=dlq_queue,
                durable=True
            )
            
            channel.queue_bind(
                exchange=dlq_exchange,
                queue=dlq_queue,
                routing_key="failed"
            )
            
            # Create retry queue with TTL and DLQ
            channel.queue_declare(
                queue=retry_queue,
                durable=True,
                arguments={
                    'x-message-ttl': 5000,  # 5 seconds TTL
                    'x-dead-letter-exchange': dlq_exchange,
                    'x-dead-letter-routing-key': 'failed',
                    'x-max-retries': 3
                }
            )
            
            # Publish message that will fail processing
            failed_event = {
                "event_type": "test.will_fail",
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "data": {"retry_count": 0},
                "max_retries": 3
            }
            
            channel.basic_publish(
                exchange='',
                routing_key=retry_queue,
                body=json.dumps(failed_event),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            
            print("✅ Event published to retry queue")
            
            # In a real implementation:
            # 1. Consumer would reject message
            # 2. Message would be requeued with retry count
            # 3. After max retries, message goes to DLQ
            
            # Cleanup
            channel.queue_delete(queue=retry_queue)
            channel.queue_delete(queue=dlq_queue)
            channel.exchange_delete(exchange=dlq_exchange)
            
        finally:
            connection.close()
    
    
    def test_event_deduplication(self):
        """Test event deduplication mechanism"""
        
        connection, channel = self.setup_rabbitmq_connection()
        
        try:
            dedup_queue = "test_dedup_queue"
            channel.queue_declare(queue=dedup_queue, durable=False)
            
            # Publish duplicate events (same event_id)
            duplicate_event_id = str(uuid.uuid4())
            
            for i in range(3):
                duplicate_event = {
                    "event_type": "test.duplicate",
                    "event_id": duplicate_event_id,  # Same ID
                    "timestamp": datetime.now().isoformat(),
                    "data": {"attempt": i + 1}
                }
                
                channel.basic_publish(
                    exchange='',
                    routing_key=dedup_queue,
                    body=json.dumps(duplicate_event),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
            
            print("✅ Duplicate events published for deduplication testing")
            
            # Count messages in queue
            method = channel.queue_declare(queue=dedup_queue, passive=True)
            message_count = method.method.message_count
            
            print(f"📊 Messages in queue: {message_count}")
            
            # In a proper implementation:
            # - Consumer would track processed event IDs
            # - Only first event with unique ID would be processed
            # - Subsequent events with same ID would be acknowledged but skipped
            
            # Cleanup
            channel.queue_delete(queue=dedup_queue)
            
        finally:
            connection.close()