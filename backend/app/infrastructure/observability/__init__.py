"""Observability utilities (metrics, logging, tracing)."""

from .metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    CHAPTER_GENERATION_TOTAL,
    CHAPTER_GENERATION_DURATION,
    CIRCUIT_BREAKER_STATE,
    PROMETHEUS_AVAILABLE,
    render_metrics,
    METRICS_CONTENT_TYPE,
)
from .structured_logging import configure_structlog
from .tracing import setup_tracing, get_tracer
from .middleware import ObservabilityMiddleware

__all__ = [
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "CHAPTER_GENERATION_TOTAL",
    "CHAPTER_GENERATION_DURATION",
    "CIRCUIT_BREAKER_STATE",
    "PROMETHEUS_AVAILABLE",
    "render_metrics",
    "METRICS_CONTENT_TYPE",
    "configure_structlog",
    "setup_tracing",
    "get_tracer",
    "ObservabilityMiddleware",
]
