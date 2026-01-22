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


class SmartContextTruncator:
    """Intelligent context truncation based on relevance."""

    @staticmethod
    def truncate_memory_context(
        memory: Dict[str, Any],
        max_chars: int = 4000,
        current_chapter: int = 0,
        mentioned_characters: List[str] = None
    ) -> str:
        """
        Prioritize:
        1. Mentioned characters
        2. Recent events (last 5 chapters)
        3. Active relations
        4. Unresolved threads
        """
        sections = []
        char_budget = max_chars

        # 1. Mentioned characters (high priority)
        if mentioned_characters:
            priority_chars = [
                c for c in memory.get('characters', [])
                if isinstance(c, dict) and c.get('name') in mentioned_characters
            ]
            char_section = SmartContextTruncator._format_characters(priority_chars)
            if char_section:
                sections.append(("PERSONNAGES PRESENTS", char_section))
                char_budget -= len(char_section)

        # 2. Recent events (last 5 chapters)
        recent_events = [
            e for e in memory.get('events', [])
            if isinstance(e, dict) and int(e.get('chapter_index', 0) or 0) >= current_chapter - 5
        ]
        events_section = SmartContextTruncator._format_events(recent_events)
        if events_section:
            sections.append(("EVENEMENTS RECENTS", events_section[:max(500, char_budget // 3)]))

        # 3. Active relations
        relations_section = SmartContextTruncator._format_relations(
            memory.get('relations', [])
        )
        if relations_section:
            sections.append(("RELATIONS", relations_section[:max(500, char_budget // 4)]))

        # 4. Unresolved threads
        unresolved = [
            e for e in memory.get('events', [])
            if isinstance(e, dict) and e.get('unresolved_threads')
        ]
        if unresolved:
            unresolved_section = SmartContextTruncator._format_unresolved(unresolved)
            if unresolved_section:
                sections.append(("FILS NARRATIFS OUVERTS", unresolved_section[:500]))

        # Fallback if specific sections are empty but simple truncate is not enough
        # (This logic rebuilds the string from prioritized sections)
        return SmartContextTruncator._build_output(sections, max_chars)

    @staticmethod
    def _format_characters(chars: List[Dict[str, Any]]) -> str:
        lines = []
        for c in chars:
            line = f"- {c.get('name', 'Inconnu')}: {c.get('current_state', 'inconnu')}"
            if c.get('motivations'):
                line += f" | Motivation: {c['motivations']}"
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _format_events(events: List[Dict[str, Any]]) -> str:
        return "\n".join([
            f"- Ch.{e.get('chapter_index', '?')}: {e.get('summary', e.get('name', ''))}"
            for e in events
        ])

    @staticmethod
    def _format_relations(relations: List[Dict[str, Any]]) -> str:
        return "\n".join([
            f"- {r.get('from', '?')} -> {r.get('to', '?')}: {r.get('type', '?')}"
            for r in relations
            if isinstance(r, dict)
        ])

    @staticmethod
    def _format_unresolved(events: List[Dict[str, Any]]) -> str:
        threads = []
        for e in events:
            raw_threads = e.get('unresolved_threads', [])
            t_list = raw_threads if isinstance(raw_threads, list) else [str(raw_threads)]
            for thread in t_list:
                threads.append(f"- {thread} (depuis ch.{e.get('chapter_index', '?')})")
        return "\n".join(threads)

    @staticmethod
    def _build_output(sections: List[tuple], max_chars: int) -> str:
        output = []
        remaining = max_chars

        for title, content in sections:
            if not content or remaining <= 0:
                continue
            section_text = f"### {title}\n{content}\n"
            if len(section_text) <= remaining:
                output.append(section_text)
                remaining -= len(section_text)
            else:
                truncated = section_text[:remaining-3] + "..."
                output.append(truncated)
                break

        return "\n".join(output)
