"""Shared kernel exception hierarchy."""
from typing import Optional, Dict, Any


class DomainException(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ValidationError(DomainException):
    """Raised when domain validation fails."""


class EntityNotFoundError(DomainException):
    """Raised when a domain entity is not found."""


class CoherenceError(DomainException):
    """Raised when narrative coherence fails."""


class ExternalServiceError(DomainException):
    """Raised when an external service fails."""


class CircuitOpenError(ExternalServiceError):
    """Raised when a circuit breaker is open."""


class ConcurrencyError(DomainException):
    """Raised on concurrency conflicts."""
