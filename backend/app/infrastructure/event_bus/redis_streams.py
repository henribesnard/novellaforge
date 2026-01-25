"""Redis Streams implementation of the event bus."""
from __future__ import annotations

import json
from typing import Dict, List, Type

import redis.asyncio as redis

from app.shared_kernel.domain_events import DomainEvent
from .interfaces import EventBus, EventHandler
from .handlers import EventHandlerRegistry


class RedisStreamsEventBus(EventBus):
    def __init__(self, redis_url: str, stream_prefix: str = "novellaforge:events") -> None:
        self._redis = redis.from_url(redis_url)
        self._stream_prefix = stream_prefix
        self._registry = EventHandlerRegistry()

    async def publish(self, event: DomainEvent) -> str:
        stream_name = f"{self._stream_prefix}:{type(event).__name__}"
        payload = event.to_dict()
        event_data = {
            "event_type": type(event).__name__,
            "payload": json.dumps(payload, default=str),
        }
        return await self._redis.xadd(stream_name, event_data)

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        self._registry.register(event_type.__name__, handler)

    def get_handlers(self, event_type_name: str) -> List[EventHandler]:
        return self._registry.get_handlers(event_type_name)
