"""Prometheus metrics definitions with safe fallbacks."""
from __future__ import annotations

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover
    PROMETHEUS_AVAILABLE = False

    class _NoOpMetric:  # pylint: disable=too-few-public-methods
        def labels(self, *args, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            return None
        def observe(self, *args, **kwargs):
            return None
        def set(self, *args, **kwargs):
            return None

    def Counter(*args, **kwargs):  # type: ignore
        return _NoOpMetric()

    def Histogram(*args, **kwargs):  # type: ignore
        return _NoOpMetric()

    def Gauge(*args, **kwargs):  # type: ignore
        return _NoOpMetric()

    def generate_latest():  # type: ignore
        return b""

    CONTENT_TYPE_LATEST = "text/plain"


REQUEST_COUNT = Counter(
    "novellaforge_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "novellaforge_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10],
)

CHAPTER_GENERATION_TOTAL = Counter(
    "novellaforge_chapter_generation_total",
    "Total chapter generations",
    ["project_id", "status"],
)

CHAPTER_GENERATION_DURATION = Histogram(
    "novellaforge_chapter_generation_duration_seconds",
    "Chapter generation duration",
    ["stage"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

CIRCUIT_BREAKER_STATE = Gauge(
    "novellaforge_circuit_breaker_state",
    "Circuit breaker state",
    ["name"],
)


def render_metrics() -> bytes:
    return generate_latest()


METRICS_CONTENT_TYPE = CONTENT_TYPE_LATEST
