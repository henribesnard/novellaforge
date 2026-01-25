"""Query model for chapter status."""
from dataclasses import dataclass
from uuid import UUID

from app.infrastructure.cqrs import Query


@dataclass(frozen=True)
class GetChapterStatusQuery(Query):
    chapter_id: UUID
