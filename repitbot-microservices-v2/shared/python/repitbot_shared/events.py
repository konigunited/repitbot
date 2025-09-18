"""Async event bus built on top of RabbitMQ using aio-pika."""
from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional

import aio_pika


class EventType(str, Enum):
    """High-level application events shared between microservices."""

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    LESSON_SCHEDULED = "lesson.scheduled"
    HOMEWORK_ASSIGNED = "homework.assigned"
    PAYMENT_RECORDED = "payment.recorded"
    NOTIFICATION_REQUESTED = "notification.requested"


@dataclass
class Event:
    """Serializable payload transported through the event bus."""

    type: EventType
    payload: Dict[str, Any]
    source: str
    timestamp: datetime = datetime.utcnow()
    correlation_id: Optional[str] = None

    def to_json(self) -> str:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["type"] = self.type.value
        return json.dumps(data)

    @classmethod
    def from_json(cls, raw: str) -> "Event":
        data = json.loads(raw)
        data["type"] = EventType(data["type"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class EventBus:
    """RabbitMQ-based pub/sub helper for services."""

    def __init__(self, url: str, exchange_name: str = "repitbot.events") -> None:
        self.url = url
        self.exchange_name = exchange_name
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None
        self._consumers: Dict[EventType, list[Callable[[Event], Awaitable[None]]]] = {}
        self._consumer_tasks: list[asyncio.Task] = []
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self._connection:
                return
            self._connection = await aio_pika.connect_robust(self.url)
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                self.exchange_name,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            # Recreate bindings for already registered subscribers
            for event_type in list(self._consumers.keys()):
                await self._ensure_consumer(event_type)

    async def close(self) -> None:
        async with self._lock:
            for task in self._consumer_tasks:
                task.cancel()
            for task in self._consumer_tasks:
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            self._consumer_tasks.clear()
            if self._connection:
                await self._connection.close()
            self._connection = None
            self._channel = None
            self._exchange = None

    async def publish(self, event: Event) -> None:
        if not self._exchange:
            await self.connect()
        assert self._exchange is not None
        message = aio_pika.Message(
            body=event.to_json().encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={"source": event.source},
        )
        await self._exchange.publish(message, routing_key=event.type.value)

    async def subscribe(self, event_type: EventType, handler: Callable[[Event], Awaitable[None]]) -> None:
        self._consumers.setdefault(event_type, []).append(handler)
        if self._exchange:
            await self._ensure_consumer(event_type)

    async def _ensure_consumer(self, event_type: EventType) -> None:
        assert self._channel is not None
        queue_name = f"repitbot.{event_type.value}"
        queue = await self._channel.declare_queue(queue_name, durable=True)
        assert self._exchange is not None
        await queue.bind(self._exchange, routing_key=event_type.value)

        async def _consume() -> None:
            async with queue.iterator() as iterator:
                async for message in iterator:
                    async with message.process():
                        event = Event.from_json(message.body.decode("utf-8"))
                        for consumer in self._consumers.get(event_type, []):
                            try:
                                await consumer(event)
                            except Exception:
                                # Swallow consumer exceptions to keep the flow running
                                continue

        task = asyncio.create_task(_consume())
        self._consumer_tasks.append(task)
