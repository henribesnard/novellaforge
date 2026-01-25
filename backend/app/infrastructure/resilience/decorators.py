"""Resilience decorators."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from .circuit_breaker import CircuitBreaker
from .retry import async_retry
from .timeout import with_timeout


def with_circuit_breaker(breaker: CircuitBreaker) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await breaker.execute(func, *args, **kwargs)
        return wrapper
    return decorator


def with_retry(retries: int = 3, backoff: float = 0.5, jitter: float = 0.1):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await async_retry(func, *args, retries=retries, backoff=backoff, jitter=jitter, **kwargs)
        return wrapper
    return decorator


def with_timeout_decorator(timeout: float):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await with_timeout(func(*args, **kwargs), timeout)
        return wrapper
    return decorator
