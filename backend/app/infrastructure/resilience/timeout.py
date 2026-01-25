"""Timeout helper for async calls."""
from __future__ import annotations

import asyncio
from typing import Awaitable, Any


async def with_timeout(coro: Awaitable[Any], timeout: float) -> Any:
    return await asyncio.wait_for(coro, timeout=timeout)
