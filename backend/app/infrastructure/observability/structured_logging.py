"""Structlog configuration helpers."""
from __future__ import annotations

import logging

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:  # pragma: no cover
    structlog = None  # type: ignore
    STRUCTLOG_AVAILABLE = False


def configure_structlog() -> None:
    if not STRUCTLOG_AVAILABLE:
        return
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.getLogger(__name__).info("structlog configured")
