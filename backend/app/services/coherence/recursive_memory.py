"""Recursive Memory - Pyramid summary structure for long novels."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentType
from app.services.llm_client import DeepSeekClient

logger = logging.getLogger(__name__)


class RecursiveMemory:
    """
    Manages a pyramid structure of summaries:

    Level 3: Global Synopsis (~1000 words)
        └── Level 2: Arc Summaries (~500 words each)
            └── Level 1: Chapter Summaries (detailed, last 5 chapters)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm_client = DeepSeekClient()

        # Configuration
        self.recent_chapters_count = settings.RECURSIVE_MEMORY_RECENT_CHAPTERS
        self.arc_summary_words = settings.RECURSIVE_MEMORY_ARC_SUMMARY_WORDS
        self.global_synopsis_words = settings.RECURSIVE_MEMORY_GLOBAL_SYNOPSIS_WORDS

    async def build_context(
        self,
        project_id: UUID,
        chapter_index: int,
        project_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build hierarchical context for chapter generation.

        Args:
            project_id: The project UUID.
            chapter_index: Current chapter being written.
            project_metadata: Project metadata (optional, will fetch if not provided).

        Returns:
            Formatted context string combining all levels.
        """
        # Level 3: Global synopsis
        global_synopsis = await self._get_global_synopsis(project_id, project_metadata)

        # Level 2: Current arc summary
        arc_summary = await self._get_current_arc_summary(
            project_id, chapter_index, project_metadata
        )

        # Level 1: Recent chapter summaries (detailed)
        recent_summaries = await self._get_recent_chapter_summaries(
            project_id, chapter_index
        )

        # Merge levels with clear structure
        context_parts = []

        if global_synopsis:
            context_parts.append(f"=== SYNOPSIS GLOBAL ===\n{global_synopsis}")

        if arc_summary:
            context_parts.append(f"=== ARC NARRATIF ACTUEL ===\n{arc_summary}")

        if recent_summaries:
            summaries_text = "\n\n".join([
                f"[Chapitre {s['index']}] {s['summary']}"
                for s in recent_summaries
            ])
            context_parts.append(f"=== CHAPITRES RÉCENTS ===\n{summaries_text}")

        return "\n\n".join(context_parts)

    async def update_after_chapter(
        self,
        project_id: UUID,
        chapter_index: int,
        chapter_text: str,
        chapter_summary: str,
    ) -> Dict[str, Any]:
        """
        Update memory structures after a chapter is approved.

        Args:
            project_id: The project UUID.
            chapter_index: The approved chapter index.
            chapter_text: Full chapter text.
            chapter_summary: Summary of the chapter.

        Returns:
            Dict with update status and any regenerated summaries.
        """
        updates = {
            "chapter_summary_stored": True,
            "arc_summary_updated": False,
            "global_synopsis_updated": False,
        }

        # Store chapter summary
        await self._store_chapter_summary(project_id, chapter_index, chapter_summary)

        # Check if arc summary needs update (every 5 chapters or end of arc)
        if await self._should_update_arc_summary(project_id, chapter_index):
            await self._update_arc_summary(project_id, chapter_index)
            updates["arc_summary_updated"] = True

        # Check if global synopsis needs update (every 10 chapters)
        if chapter_index % 10 == 0:
            await self._update_global_synopsis(project_id)
            updates["global_synopsis_updated"] = True

        return updates

    async def _get_global_synopsis(
        self,
        project_id: UUID,
        project_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get or generate global synopsis."""
        if project_metadata is None:
            project_metadata = await self._fetch_project_metadata(project_id)

        recursive_memory = project_metadata.get("recursive_memory", {})
        return recursive_memory.get("global_synopsis", "")

    async def _get_current_arc_summary(
        self,
        project_id: UUID,
        chapter_index: int,
        project_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get summary of the current narrative arc."""
        if project_metadata is None:
            project_metadata = await self._fetch_project_metadata(project_id)

        # Find current arc based on plan
        plan = project_metadata.get("plan", {})
        if isinstance(plan, dict):
            plan_data = plan.get("data", plan)
        else:
            plan_data = {}

        arcs = plan_data.get("arcs", [])
        current_arc = None

        for arc in arcs:
            start = arc.get("chapter_start", 0)
            end = arc.get("chapter_end", 999)
            if start <= chapter_index <= end:
                current_arc = arc
                break

        if not current_arc:
            return ""

        # Get arc summary from recursive memory
        recursive_memory = project_metadata.get("recursive_memory", {})
        arc_summaries = recursive_memory.get("arc_summaries", {})
        arc_id = current_arc.get("id", "")

        return arc_summaries.get(arc_id, current_arc.get("summary", ""))

    async def _get_recent_chapter_summaries(
        self,
        project_id: UUID,
        chapter_index: int,
    ) -> List[Dict[str, Any]]:
        """Get detailed summaries of recent chapters."""
        summaries = []

        # Query documents for recent chapters
        start_index = max(1, chapter_index - self.recent_chapters_count)

        result = await self.db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == DocumentType.CHAPTER,
                Document.order_index >= start_index,
                Document.order_index < chapter_index,
            ).order_by(Document.order_index.asc())
        )
        documents = result.scalars().all()

        for doc in documents:
            metadata = doc.document_metadata or {}
            summary = metadata.get("summary", "")

            # If no summary, generate one
            if not summary and doc.content:
                summary = await self._generate_chapter_summary(doc.content)
                # Store for future use
                await self._store_chapter_summary(project_id, doc.order_index, summary)

            if summary:
                summaries.append({
                    "index": doc.order_index,
                    "title": doc.title,
                    "summary": summary,
                })

        return summaries

    async def _store_chapter_summary(
        self,
        project_id: UUID,
        chapter_index: int,
        summary: str,
    ) -> None:
        """Store chapter summary in document metadata."""
        result = await self.db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == DocumentType.CHAPTER,
                Document.order_index == chapter_index,
            )
        )
        doc = result.scalar_one_or_none()

        if doc:
            metadata = doc.document_metadata or {}
            metadata["summary"] = summary
            doc.document_metadata = metadata
            await self.db.commit()

    async def _should_update_arc_summary(
        self,
        project_id: UUID,
        chapter_index: int,
    ) -> bool:
        """Determine if arc summary should be updated."""
        # Update every 5 chapters or at arc boundaries
        if chapter_index % 5 == 0:
            return True

        # Check if this is an arc boundary
        project_metadata = await self._fetch_project_metadata(project_id)
        plan = project_metadata.get("plan", {})
        if isinstance(plan, dict):
            plan_data = plan.get("data", plan)
        else:
            plan_data = {}

        arcs = plan_data.get("arcs", [])
        for arc in arcs:
            if arc.get("chapter_end") == chapter_index:
                return True

        return False

    async def _update_arc_summary(
        self,
        project_id: UUID,
        chapter_index: int,
    ) -> None:
        """Regenerate current arc summary."""
        project_metadata = await self._fetch_project_metadata(project_id)

        # Find current arc
        plan = project_metadata.get("plan", {})
        if isinstance(plan, dict):
            plan_data = plan.get("data", plan)
        else:
            plan_data = {}

        arcs = plan_data.get("arcs", [])
        current_arc = None

        for arc in arcs:
            start = arc.get("chapter_start", 0)
            end = arc.get("chapter_end", 999)
            if start <= chapter_index <= end:
                current_arc = arc
                break

        if not current_arc:
            return

        # Get all chapter summaries in this arc
        arc_start = current_arc.get("chapter_start", 1)
        arc_end = min(current_arc.get("chapter_end", chapter_index), chapter_index)

        result = await self.db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == DocumentType.CHAPTER,
                Document.order_index >= arc_start,
                Document.order_index <= arc_end,
            ).order_by(Document.order_index.asc())
        )
        documents = result.scalars().all()

        chapter_summaries = []
        for doc in documents:
            metadata = doc.document_metadata or {}
            summary = metadata.get("summary", "")
            if summary:
                chapter_summaries.append(f"Ch.{doc.order_index}: {summary}")

        if not chapter_summaries:
            return

        # Generate arc summary
        arc_summary = await self._generate_arc_summary(
            arc_title=current_arc.get("title", "Arc"),
            arc_target_emotion=current_arc.get("target_emotion", ""),
            chapter_summaries=chapter_summaries,
        )

        # Store in project metadata
        await self._store_arc_summary(project_id, current_arc.get("id", ""), arc_summary)

    async def _update_global_synopsis(self, project_id: UUID) -> None:
        """Regenerate global synopsis from all arc summaries."""
        project_metadata = await self._fetch_project_metadata(project_id)

        recursive_memory = project_metadata.get("recursive_memory", {})
        arc_summaries = recursive_memory.get("arc_summaries", {})

        if not arc_summaries:
            return

        # Get concept for context
        concept = project_metadata.get("concept", {})
        if isinstance(concept, dict):
            concept_data = concept.get("data", concept)
        else:
            concept_data = {}

        premise = concept_data.get("premise", "")

        # Generate global synopsis
        synopsis = await self._generate_global_synopsis(
            premise=premise,
            arc_summaries=list(arc_summaries.values()),
        )

        # Store
        await self._store_global_synopsis(project_id, synopsis)

    async def _generate_chapter_summary(self, chapter_text: str) -> str:
        """Generate a summary for a chapter."""
        prompt = f"""Résume ce chapitre en 2-3 phrases, en capturant :
- Les événements principaux
- Les évolutions des personnages
- Les éléments importants pour la suite

Chapitre :
{chapter_text[:3000]}

Résumé (2-3 phrases) :"""

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return response.strip()

    async def _generate_arc_summary(
        self,
        arc_title: str,
        arc_target_emotion: str,
        chapter_summaries: List[str],
    ) -> str:
        """Generate a summary for a narrative arc."""
        chapters_text = "\n".join(chapter_summaries)

        prompt = f"""Résume cet arc narratif en environ {self.arc_summary_words} mots.

Titre de l'arc : {arc_title}
Émotion cible : {arc_target_emotion}

Résumés des chapitres :
{chapters_text}

Résumé de l'arc (capture la progression narrative, les conflits, les résolutions partielles) :"""

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=800,
        )
        return response.strip()

    async def _generate_global_synopsis(
        self,
        premise: str,
        arc_summaries: List[str],
    ) -> str:
        """Generate global synopsis from arc summaries."""
        arcs_text = "\n\n".join([f"Arc {i+1}: {s}" for i, s in enumerate(arc_summaries)])

        prompt = f"""Génère un synopsis global du roman en environ {self.global_synopsis_words} mots.

Prémisse : {premise}

Résumés des arcs :
{arcs_text}

Synopsis global (couvre l'intrigue principale, les personnages clés, les thèmes) :"""

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1500,
        )
        return response.strip()

    async def _fetch_project_metadata(self, project_id: UUID) -> Dict[str, Any]:
        """Fetch project metadata from database."""
        from app.models.project import Project

        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            return project.project_metadata or {}
        return {}

    async def _store_arc_summary(
        self,
        project_id: UUID,
        arc_id: str,
        summary: str,
    ) -> None:
        """Store arc summary in project metadata."""
        from app.models.project import Project

        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            metadata = project.project_metadata or {}
            if "recursive_memory" not in metadata:
                metadata["recursive_memory"] = {}
            if "arc_summaries" not in metadata["recursive_memory"]:
                metadata["recursive_memory"]["arc_summaries"] = {}

            metadata["recursive_memory"]["arc_summaries"][arc_id] = summary
            project.project_metadata = metadata
            await self.db.commit()

    async def _store_global_synopsis(
        self,
        project_id: UUID,
        synopsis: str,
    ) -> None:
        """Store global synopsis in project metadata."""
        from app.models.project import Project

        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            metadata = project.project_metadata or {}
            if "recursive_memory" not in metadata:
                metadata["recursive_memory"] = {}

            metadata["recursive_memory"]["global_synopsis"] = synopsis
            metadata["recursive_memory"]["synopsis_updated_at"] = datetime.utcnow().isoformat()
            project.project_metadata = metadata
            await self.db.commit()
