"""OpenTelemetry tracing setup."""
from __future__ import annotations

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    trace = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    ConsoleSpanExporter = None  # type: ignore
    OTEL_AVAILABLE = False


def setup_tracing(service_name: str) -> None:
    if not OTEL_AVAILABLE:
        return
    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


def get_tracer(name: str):
    if not OTEL_AVAILABLE:
        return None
    return trace.get_tracer(name)
