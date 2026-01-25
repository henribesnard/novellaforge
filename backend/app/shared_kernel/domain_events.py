"""Domain event primitives for the shared kernel."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from abc import ABC


@dataclass(frozen=True)
class DomainEvent(ABC):
    """Base class for all domain events."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.__class__.__name__,
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "causation_id": str(self.causation_id) if self.causation_id else None,
            "payload": self._payload_dict(),
        }

    def _payload_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        for item in fields(self):
            if item.name in {"event_id", "occurred_at", "correlation_id", "causation_id"}:
                continue
            value = getattr(self, item.name)
            payload[item.name] = self._serialize_value(value)
        return payload

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return value


# Writing domain events
@dataclass(frozen=True)
class ChapterGenerationStartedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_index: int = 0
    user_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class ChapterGeneratedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_id: UUID = field(default_factory=uuid4)
    chapter_index: int = 0
    word_count: int = 0
    content_hash: str = ""


@dataclass(frozen=True)
class ChapterApprovedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_id: UUID = field(default_factory=uuid4)
    chapter_index: int = 0
    summary: str = ""


# Coherence domain events
@dataclass(frozen=True)
class CoherenceValidatedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_id: UUID = field(default_factory=uuid4)
    score: float = 0.0
    issues_count: int = 0
    blocking_issues: bool = False


@dataclass(frozen=True)
class ContradictionDetectedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_id: UUID = field(default_factory=uuid4)
    contradiction_type: str = ""
    severity: str = "warning"
    description: str = ""


# Memory domain events
@dataclass(frozen=True)
class FactsExtractedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_index: int = 0
    characters_count: int = 0
    locations_count: int = 0
    events_count: int = 0


@dataclass(frozen=True)
class MemoryUpdatedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    memory_type: str = ""
    entities_updated: int = 0
