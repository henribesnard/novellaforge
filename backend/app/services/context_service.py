"""Project context builder for writing and agents."""
from typing import Dict, Any, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.document import Document
from app.models.character import Character


class ProjectContextService:
    """Build a structured context pack from project data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build_project_context(
        self,
        project_id: UUID,
        user_id: UUID,
        document_preview_chars: int = 800,
    ) -> Dict[str, Any]:
        """Collect project, characters, documents, and constraints."""
        project_result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user_id,
            )
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied",
            )

        documents_result = await self.db.execute(
            select(Document).where(Document.project_id == project_id).order_by(Document.order_index.asc())
        )
        documents = documents_result.scalars().all()

        characters_result = await self.db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        characters = characters_result.scalars().all()

        project_metadata = project.project_metadata or {}
        concept = None
        plan = None
        continuity: Dict[str, Any] = {}
        recent_chapter_summaries: List[str] = []
        story_bible: Dict[str, Any] = {}
        if isinstance(project_metadata, dict):
            concept_entry = project_metadata.get("concept")
            plan_entry = project_metadata.get("plan")
            if isinstance(concept_entry, dict):
                concept = concept_entry.get("data") or (
                    concept_entry
                    if any(key in concept_entry for key in ("premise", "tone", "tropes", "emotional_orientation"))
                    else None
                )
            if isinstance(plan_entry, dict):
                plan = plan_entry.get("data") if isinstance(plan_entry.get("data"), dict) else (
                    plan_entry
                    if any(key in plan_entry for key in ("chapters", "arcs", "global_summary"))
                    else None
                )
            continuity = project_metadata.get("continuity") or {}
            recent_chapter_summaries = project_metadata.get("recent_chapter_summaries") or []
            story_bible = project_metadata.get("story_bible") or {}
            if not isinstance(story_bible, dict):
                story_bible = {}
        constraints = project_metadata.get("constraints") if isinstance(project_metadata, dict) else None
        instructions_raw = project_metadata.get("instructions") if isinstance(project_metadata, dict) else None
        instructions = []
        if isinstance(instructions_raw, list):
            for item in instructions_raw:
                if not isinstance(item, dict):
                    continue
                title = item.get("title")
                detail = item.get("detail")
                if not title or not detail:
                    continue
                instructions.append(
                    {
                        "id": str(item.get("id")) if item.get("id") else None,
                        "title": str(title),
                        "detail": str(detail),
                        "created_at": item.get("created_at"),
                    }
                )

        return {
            "project": {
                "id": str(project.id),
                "title": project.title,
                "description": project.description,
                "genre": project.genre.value if project.genre else None,
                "status": project.status.value,
                "structure_template": project.structure_template,
                "target_word_count": project.target_word_count,
                "current_word_count": project.current_word_count,
                "concept": concept,
                "plan": plan,
                "continuity": continuity,
                "recent_chapter_summaries": recent_chapter_summaries,
                "metadata": project_metadata,
            },
            "constraints": constraints or {},
            "instructions": instructions,
            "story_bible": story_bible,
            "documents": [
                {
                    "id": str(doc.id),
                    "title": doc.title,
                    "document_type": doc.document_type.value if doc.document_type else None,
                    "order_index": doc.order_index,
                    "word_count": doc.word_count,
                    "metadata": doc.document_metadata or {},
                    "content_preview": (doc.content or "")[:document_preview_chars],
                }
                for doc in documents
            ],
            "characters": [
                {
                    "id": str(char.id),
                    "name": char.name,
                    "role": char.character_metadata.get("role") if char.character_metadata else None,
                    "description": char.description,
                    "personality": char.personality,
                    "backstory": char.backstory,
                    "metadata": char.character_metadata or {},
                }
                for char in characters
            ],
        }
