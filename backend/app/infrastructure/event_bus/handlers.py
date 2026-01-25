"""Registry for event handlers."""
from __future__ import annotations

from typing import Dict, List, Iterable

from .interfaces import EventHandler


class EventHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}

    def register(self, event_type_name: str, handler: EventHandler) -> None:
        if event_type_name not in self._handlers:
            self._handlers[event_type_name] = []
        self._handlers[event_type_name].append(handler)

    def get_handlers(self, event_type_name: str) -> List[EventHandler]:
        return list(self._handlers.get(event_type_name, []))

    def event_types(self) -> Iterable[str]:
        return self._handlers.keys()
