"""Shared kernel primitives (events, value objects, errors)."""

from .domain_events import (
    DomainEvent,
    ChapterGenerationStartedEvent,
    ChapterGeneratedEvent,
    ChapterApprovedEvent,
    CoherenceValidatedEvent,
    ContradictionDetectedEvent,
    FactsExtractedEvent,
    MemoryUpdatedEvent,
)
from .exceptions import (
    DomainException,
    ValidationError,
    EntityNotFoundError,
    CoherenceError,
    ExternalServiceError,
    CircuitOpenError,
    ConcurrencyError,
)
from .value_objects import (
    ProjectId,
    ChapterId,
    UserId,
    WordCount,
    CoherenceScore,
    ChapterContent,
)
from .result import Result

__all__ = [
    "DomainEvent",
    "ChapterGenerationStartedEvent",
    "ChapterGeneratedEvent",
    "ChapterApprovedEvent",
    "CoherenceValidatedEvent",
    "ContradictionDetectedEvent",
    "FactsExtractedEvent",
    "MemoryUpdatedEvent",
    "DomainException",
    "ValidationError",
    "EntityNotFoundError",
    "CoherenceError",
    "ExternalServiceError",
    "CircuitOpenError",
    "ConcurrencyError",
    "ProjectId",
    "ChapterId",
    "UserId",
    "WordCount",
    "CoherenceScore",
    "ChapterContent",
    "Result",
]
