"""Observability middleware for FastAPI."""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .metrics import REQUEST_COUNT, REQUEST_LATENCY
from .tracing import get_tracer


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        tracer = get_tracer("novellaforge.http")
        if tracer:
            with tracer.start_as_current_span(
                f"{request.method} {request.url.path}"
            ) as span:
                response = await call_next(request)
                span.set_attribute("http.status_code", response.status_code)
        else:
            response = await call_next(request)
        duration = time.perf_counter() - start
        REQUEST_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(duration)
        return response
