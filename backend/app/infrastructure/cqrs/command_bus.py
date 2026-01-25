"""Command bus for CQRS."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Dict, Type, Any

TCommand = TypeVar("TCommand", bound="Command")
TResult = TypeVar("TResult")


class Command(ABC):
    """Marker base class for commands."""


class CommandHandler(ABC, Generic[TCommand, TResult]):
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        raise NotImplementedError


class CommandBus:
    def __init__(self) -> None:
        self._handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, command_type: Type[TCommand], handler: CommandHandler) -> None:
        self._handlers[command_type] = handler

    async def dispatch(self, command: Command) -> Any:
        command_type = type(command)
        if command_type not in self._handlers:
            raise ValueError(f"No handler registered for {command_type.__name__}")
        handler = self._handlers[command_type]
        return await handler.handle(command)
