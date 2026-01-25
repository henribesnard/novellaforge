"""In-memory event bus for tests and local usage."""
from __future__ import annotations

from typing import Type

from app.shared_kernel.domain_events import DomainEvent
from .interfaces import EventBus, EventHandler
from .handlers import EventHandlerRegistry


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._registry = EventHandlerRegistry()

    async def publish(self, event: DomainEvent) -> str:
        event_type = type(event).__name__
        handlers = self._registry.get_handlers(event_type)
        for handler in handlers:
            await handler(event)
        return event_type

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        self._registry.register(event_type.__name__, handler)
