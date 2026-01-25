import asyncio
import pytest

from app.infrastructure.resilience import CircuitBreaker, async_retry, with_timeout
from app.shared_kernel.exceptions import CircuitOpenError


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    breaker = CircuitBreaker(name="test", failure_threshold=2)

    async def fail():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await breaker.execute(fail)
    with pytest.raises(ValueError):
        await breaker.execute(fail)

    with pytest.raises(CircuitOpenError):
        await breaker.execute(fail)


@pytest.mark.asyncio
async def test_async_retry_eventually_succeeds():
    calls = {"count": 0}

    async def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("fail")
        return "ok"

    result = await async_retry(flaky, retries=3, backoff=0.01, jitter=0.0)
    assert result == "ok"


@pytest.mark.asyncio
async def test_with_timeout_raises():
    async def slow():
        await asyncio.sleep(0.05)
        return "done"

    with pytest.raises(asyncio.TimeoutError):
        await with_timeout(slow(), timeout=0.01)
