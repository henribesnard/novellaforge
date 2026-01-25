"""Redis Streams consumer helper."""
from __future__ import annotations

import json
from typing import Dict, Optional

import redis.asyncio as redis

from .handlers import EventHandlerRegistry


class RedisStreamConsumer:
    def __init__(
        self,
        redis_url: str,
        stream_prefix: str = "novellaforge:events",
    ) -> None:
        self._redis = redis.from_url(redis_url)
        self._stream_prefix = stream_prefix
        self._registry = EventHandlerRegistry()
        self._last_ids: Dict[str, str] = {}

    def register(self, event_type_name: str, handler) -> None:
        self._registry.register(event_type_name, handler)

    async def poll(self, timeout_ms: int = 1000, count: int = 25) -> int:
        streams = {
            f"{self._stream_prefix}:{event_type}": self._last_ids.get(event_type, "$")
            for event_type in self._registry.event_types()
        }
        if not streams:
            return 0
        results = await self._redis.xread(streams=streams, count=count, block=timeout_ms)
        processed = 0
        for stream_name, entries in results:
            event_type = str(stream_name).split(":")[-1]
            handlers = self._registry.get_handlers(event_type)
            for entry_id, data in entries:
                payload_raw = None
                if isinstance(data, dict):
                    payload_raw = data.get(b"payload") or data.get("payload")
                payload = {}
                if payload_raw:
                    try:
                        if isinstance(payload_raw, bytes):
                            payload = json.loads(payload_raw.decode("utf-8"))
                        else:
                            payload = json.loads(payload_raw)
                    except json.JSONDecodeError:
                        payload = {}
                for handler in handlers:
                    await handler(payload)
                self._last_ids[event_type] = entry_id
                processed += 1
        return processed
