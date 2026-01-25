"""Writing repositories (placeholder)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.domains.writing.domain.entities import Chapter


class ChapterRepository:
    async def get_by_id(self, chapter_id: UUID) -> Optional[Chapter]:
        raise NotImplementedError

    async def save(self, chapter: Chapter) -> None:
        raise NotImplementedError
