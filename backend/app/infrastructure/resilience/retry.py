"""Retry helpers with exponential backoff."""
from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Callable, Tuple, Type


async def async_retry(
    func: Callable[..., Any],
    *args: Any,
    retries: int = 3,
    backoff: float = 0.5,
    jitter: float = 0.1,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    delay = backoff
    attempt = 0
    while True:
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return await asyncio.to_thread(func, *args, **kwargs)
        except exceptions:
            attempt += 1
            if attempt > retries:
                raise
            await asyncio.sleep(delay + random.random() * jitter)
            delay *= 2


def retry(
    func: Callable[..., Any],
    *args: Any,
    retries: int = 3,
    backoff: float = 0.5,
    jitter: float = 0.1,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    delay = backoff
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except exceptions:
            attempt += 1
            if attempt > retries:
                raise
            sleep_for = delay + random.random() * jitter
            time.sleep(sleep_for)
            delay *= 2
