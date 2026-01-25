"""Query bus for CQRS."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Dict, Type, Any

TQuery = TypeVar("TQuery", bound="Query")
TResult = TypeVar("TResult")


class Query(ABC):
    """Marker base class for queries."""


class QueryHandler(ABC, Generic[TQuery, TResult]):
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        raise NotImplementedError


class QueryBus:
    def __init__(self) -> None:
        self._handlers: Dict[Type[Query], QueryHandler] = {}

    def register(self, query_type: Type[TQuery], handler: QueryHandler) -> None:
        self._handlers[query_type] = handler

    async def dispatch(self, query: Query) -> Any:
        query_type = type(query)
        if query_type not in self._handlers:
            raise ValueError(f"No handler registered for {query_type.__name__}")
        handler = self._handlers[query_type]
        return await handler.handle(query)
