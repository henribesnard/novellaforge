"""Writing domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List
from uuid import UUID, uuid4
import hashlib

from app.shared_kernel.domain_events import (
    DomainEvent,
    ChapterGeneratedEvent,
    ChapterApprovedEvent,
)


class ChapterStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Chapter:
    """Aggregate root for a chapter."""

    id: UUID
    project_id: UUID
    index: int
    title: str
    content: str
    status: ChapterStatus
    word_count: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    _events: List[DomainEvent] = field(default_factory=list, repr=False)

    @classmethod
    def create(cls, project_id: UUID, index: int, title: str, content: str) -> "Chapter":
        now = datetime.now(timezone.utc)
        chapter = cls(
            id=uuid4(),
            project_id=project_id,
            index=index,
            title=title,
            content=content,
            status=ChapterStatus.DRAFT,
            word_count=len(content.split()),
            created_at=now,
            updated_at=now,
        )
        chapter._events.append(
            ChapterGeneratedEvent(
                project_id=project_id,
                chapter_id=chapter.id,
                chapter_index=index,
                word_count=chapter.word_count,
                content_hash=_hash_content(content),
            )
        )
        return chapter

    def approve(self, summary: str) -> None:
        if self.status == ChapterStatus.APPROVED:
            raise ValueError("Chapter already approved")
        self.status = ChapterStatus.APPROVED
        self.metadata["summary"] = summary
        self.updated_at = datetime.now(timezone.utc)
        self._events.append(
            ChapterApprovedEvent(
                project_id=self.project_id,
                chapter_id=self.id,
                chapter_index=self.index,
                summary=summary,
            )
        )

    def collect_events(self) -> List[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
