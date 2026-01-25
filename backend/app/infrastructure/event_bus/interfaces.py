"""Event bus interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Type

from app.shared_kernel.domain_events import DomainEvent

EventHandler = Callable[[Any], Awaitable[None]]


class EventBus(ABC):
    """Abstract event bus."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> str:
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        raise NotImplementedError
