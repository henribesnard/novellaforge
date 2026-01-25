"""Mediator for command/query dispatch."""
from __future__ import annotations

from typing import Union, Any

from .command_bus import CommandBus, Command
from .query_bus import QueryBus, Query


class Mediator:
    def __init__(self, command_bus: CommandBus, query_bus: QueryBus) -> None:
        self._command_bus = command_bus
        self._query_bus = query_bus

    async def send(self, request: Union[Command, Query]) -> Any:
        if isinstance(request, Command):
            return await self._command_bus.dispatch(request)
        if isinstance(request, Query):
            return await self._query_bus.dispatch(request)
        raise ValueError(f"Unknown request type: {type(request)}")
