"""Decorators for CQRS handlers."""
from __future__ import annotations

from typing import Callable, Type, TypeVar

T = TypeVar("T")


def command_handler(command_type: Type) -> Callable[[T], T]:
    def decorator(handler_cls: T) -> T:
        setattr(handler_cls, "_command_type", command_type)
        return handler_cls
    return decorator


def query_handler(query_type: Type) -> Callable[[T], T]:
    def decorator(handler_cls: T) -> T:
        setattr(handler_cls, "_query_type", query_type)
        return handler_cls
    return decorator
