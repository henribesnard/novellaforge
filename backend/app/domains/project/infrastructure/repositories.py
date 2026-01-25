"""Project repositories (placeholder)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.domains.project.domain.entities import Project


class ProjectRepository:
    async def get_by_id(self, project_id: UUID) -> Optional[Project]:
        raise NotImplementedError

    async def save(self, project: Project) -> None:
        raise NotImplementedError
