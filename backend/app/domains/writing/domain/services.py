"""Writing domain services."""
from __future__ import annotations

from uuid import UUID

from .entities import Chapter


class ChapterFactory:
    """Factory for creating chapter aggregates."""

    def create(self, project_id: UUID, index: int, title: str, content: str) -> Chapter:
        return Chapter.create(project_id=project_id, index=index, title=title, content=content)
