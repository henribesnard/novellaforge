"""Services for NovellaForge concept and planning workflows."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import json
import math

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, Genre
from app.services.llm_client import DeepSeekClient
from app.core.config import settings


class NovellaForgeService:
    """Generate concept and planning assets for serial novels."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm_client = DeepSeekClient()

    def _genre_label(self, genre: str) -> str:
        key = (genre or "fiction").strip().lower()
        labels = {
            "werewolf": "loup-garou",
            "billionaire": "milliardaire",
            "mafia": "mafia",
            "fantasy": "fantasy",
            "vengeance": "vengeance",
            "romance": "romance",
            "thriller": "thriller",
            "fiction": "fiction",
            "scifi": "science-fiction",
            "mystery": "mystere",
            "horror": "horreur",
            "historical": "historique",
            "other": "autre",
        }
        return labels.get(key, key.replace("_", " "))

    def _concept_fallback(self, genre: str) -> Dict[str, Any]:
        genre_label = self._genre_label(genre)
        return {
            "title": f"Projet {genre_label} sans titre",
            "premise": f"Une histoire {genre_label} portee par des enjeux emotionnels forts.",
            "tone": "emotionnel, intense, addictif",
            "tropes": ["destins lies", "secrets enfouis", "tension croissante"],
            "emotional_orientation": "passion, tension, vengeance",
        }

    def _build_concept_prompt(
        self,
        genre: str,
        notes: Optional[str] = None,
        avoid_titles: Optional[List[str]] = None,
        variation_seed: Optional[str] = None,
    ) -> str:
        genre_label = self._genre_label(genre)
        prompt = (
            "Tu es un assistant de conception de romans feuilleton. "
            "Reponds en francais uniquement. Toutes les valeurs doivent etre en francais. "
            "Retourne un JSON strict avec les cles: title, premise, tone, tropes (liste), emotional_orientation.\n"
            f"Genre: {genre_label} (code: {genre})\n"
            "Le concept doit etre adapte au pay-to-read et inclure un fort potentiel de cliffhanger. "
            "Propose un titre inedit qui n'a jamais ete utilise."
        )
        if avoid_titles:
            prompt += "\nTitres a eviter (ne pas reutiliser): " + "; ".join(avoid_titles[:8])
        if variation_seed:
            prompt += f"\nIndice de variation: {variation_seed}"
        if notes:
            prompt += f"\nNotes utilisateur: {notes}"
        return prompt

    def _synopsis_fallback(self, concept: Dict[str, Any]) -> str:
        premise = (concept or {}).get("premise") or "Une histoire forte en emotions"
        tone = (concept or {}).get("tone") or "emotionnel"
        return f"{premise}. Le ton reste {tone}, avec une progression feuilletonnante et des cliffhangers."

    async def _get_project(self, project_id: UUID, user_id: UUID) -> Project:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id, Project.owner_id == user_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied",
        )
        return project

    async def generate_concept_preview(
        self,
        genre: str,
        notes: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        avoid_titles = await self._get_recent_titles(user_id, genre) if user_id else []
        avoid_set = {title.casefold() for title in avoid_titles if isinstance(title, str)}
        fallback = self._concept_fallback(genre)

        for _ in range(3):
            prompt = self._build_concept_prompt(
                genre,
                notes,
                avoid_titles=avoid_titles,
                variation_seed=str(uuid4()),
            )
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=700,
                response_format={"type": "json_object"},
            )
            concept = self._parse_json(response, fallback=fallback)
            if not isinstance(concept, dict):
                concept = fallback
            for key, value in fallback.items():
                if concept.get(key) in (None, "", []):
                    concept[key] = value
            tropes = concept.get("tropes")
            if isinstance(tropes, str):
                concept["tropes"] = [item.strip() for item in tropes.split(",") if item.strip()]
            elif not isinstance(tropes, list):
                concept["tropes"] = fallback["tropes"]
            for key in ("title", "premise", "tone", "emotional_orientation"):
                if not isinstance(concept.get(key), str):
                    concept[key] = str(concept.get(key) or fallback[key])

            title = (concept.get("title") or "").strip()
            if not title:
                return concept
            normalized = title.casefold()
            if normalized in avoid_set:
                avoid_titles.append(title)
                avoid_set.add(normalized)
                continue
            return concept

        return concept

    async def _get_recent_titles(self, user_id: Optional[UUID], genre: str, limit: int = 8) -> List[str]:
        if not user_id:
            return []
        try:
            genre_enum = Genre(genre)
        except ValueError:
            genre_enum = None
        query = select(Project.title).where(Project.owner_id == user_id)
        if genre_enum:
            query = query.where(Project.genre == genre_enum)
        else:
            query = query.where(Project.genre == genre)
        query = query.order_by(Project.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall() if row and row[0]]

    async def generate_synopsis(
        self,
        project_id: UUID,
        user_id: UUID,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        project = await self._get_project(project_id, user_id)
        metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
        concept_entry = metadata.get("concept") if isinstance(metadata.get("concept"), dict) else None
        if not concept_entry or concept_entry.get("status") != "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Concept non accepte",
            )
        concept = concept_entry.get("data") or {}

        prompt = (
            "Tu es un assistant de conception de romans feuilleton. "
            "Reponds en francais uniquement. "
            "Retourne un JSON strict avec la cle synopsis.\n"
            f"Premisse: {concept.get('premise', '')}\n"
            f"Ton: {concept.get('tone', '')}\n"
            f"Tropes: {', '.join(concept.get('tropes', []))}\n"
            f"Orientation emotionnelle: {concept.get('emotional_orientation', '')}\n"
            "Le synopsis doit etre concis, clair et adapte au pay-to-read."
        )
        if notes:
            prompt += f"\nNotes utilisateur: {notes}"

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        payload = self._parse_json(response, fallback={"synopsis": self._synopsis_fallback(concept)})
        synopsis = payload.get("synopsis") or self._synopsis_fallback(concept)
        if not isinstance(synopsis, str):
            synopsis = str(synopsis)

        synopsis_entry = {
            "status": "draft",
            "text": synopsis,
            "updated_at": datetime.utcnow().isoformat(),
        }
        metadata["synopsis"] = synopsis_entry
        project.project_metadata = metadata
        await self.db.commit()
        await self.db.refresh(project)
        return synopsis_entry

    async def generate_concept(
        self,
        project_id: UUID,
        user_id: UUID,
        force: bool = False,
    ) -> Dict[str, Any]:
        project = await self._get_project(project_id, user_id)
        metadata = project.project_metadata or {}
        concept_entry = metadata.get("concept") if isinstance(metadata, dict) else None

        if concept_entry and not force and concept_entry.get("status") == "accepted":
            return concept_entry

        genre = project.genre.value if project.genre else "fiction"
        concept = await self.generate_concept_preview(genre, user_id=user_id)

        concept_entry = {
            "status": "draft",
            "data": concept,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["concept"] = concept_entry
        project.project_metadata = metadata
        if not project.description and concept.get("premise"):
            project.description = concept["premise"]
        if concept.get("title"):
            project.title = concept["title"]
        await self.db.commit()
        await self.db.refresh(project)
        return concept_entry

    async def accept_concept(
        self,
        project_id: UUID,
        user_id: UUID,
        concept: Dict[str, Any],
    ) -> Dict[str, Any]:
        project = await self._get_project(project_id, user_id)
        metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
        concept_entry = {
            "status": "accepted",
            "data": concept,
            "updated_at": datetime.utcnow().isoformat(),
        }
        metadata["concept"] = concept_entry
        project.project_metadata = metadata
        if concept.get("premise"):
            project.description = concept["premise"]
        if concept.get("title"):
            project.title = concept["title"]
        await self.db.commit()
        await self.db.refresh(project)
        return concept_entry

    async def generate_plan(
        self,
        project_id: UUID,
        user_id: UUID,
        chapter_count: Optional[int] = None,
        arc_count: Optional[int] = None,
        regenerate: bool = False,
    ) -> Dict[str, Any]:
        project = await self._get_project(project_id, user_id)
        metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
        plan_entry = metadata.get("plan")
        if plan_entry and not regenerate:
            return plan_entry

        concept_entry = metadata.get("concept") if isinstance(metadata.get("concept"), dict) else None
        if not concept_entry or concept_entry.get("status") != "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Concept non accepte",
            )
        concept = concept_entry.get("data") or {}
        genre = project.genre.value if project.genre else "fiction"
        genre_label = self._genre_label(genre)
        target_words = project.target_word_count or 200000
        chapter_min = self._get_chapter_min(metadata)
        chapter_max = self._get_chapter_max(metadata)
        average_chapter = int((chapter_min + chapter_max) / 2)
        default_chapter_count = max(30, math.ceil(target_words / average_chapter))
        chapter_count = chapter_count or default_chapter_count
        arc_count = arc_count or max(3, min(10, math.ceil(chapter_count / 15)))

        prompt = (
            "Tu es un assistant de planification de romans feuilleton. "
            "Reponds en francais uniquement. Toutes les valeurs doivent etre en francais. "
            "Retourne un JSON strict avec les cles: global_summary, arcs, chapters.\n"
            "Chaque arc: id, title, summary, target_emotion, chapter_start, chapter_end.\n"
            "Chaque chapitre: index, title, summary, emotional_stake, arc_id, cliffhanger_type.\n"
            f"Genre: {genre_label} (code: {genre})\n"
            f"Premisse: {concept.get('premise', '')}\n"
            f"Ton: {concept.get('tone', '')}\n"
            f"Tropes: {', '.join(concept.get('tropes', []))}\n"
            f"Nombre de chapitres: {chapter_count}\n"
            f"Nombre d'arcs: {arc_count}\n"
            "Chaque chapitre doit se terminer par un cliffhanger fort."
        )
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1800,
            response_format={"type": "json_object"},
        )
        plan = self._parse_json(response, fallback=self._fallback_plan(chapter_count, arc_count))
        plan = self._normalize_plan(plan, chapter_count, arc_count)

        plan_entry = {
            "data": plan,
            "status": "draft",
            "updated_at": datetime.utcnow().isoformat(),
        }
        metadata["plan"] = plan_entry
        project.project_metadata = metadata
        await self.db.commit()
        await self.db.refresh(project)
        return plan_entry

    def _parse_json(self, text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass
        return fallback

    def _fallback_plan(self, chapter_count: int, arc_count: int) -> Dict[str, Any]:
        arcs = []
        chapters = []
        chapters_per_arc = max(1, math.ceil(chapter_count / arc_count))
        for arc_index in range(arc_count):
            start = arc_index * chapters_per_arc + 1
            end = min(chapter_count, (arc_index + 1) * chapters_per_arc)
            arc_id = f"arc-{arc_index + 1}"
            arcs.append(
                {
                    "id": arc_id,
                    "title": f"Arc {arc_index + 1}",
                    "summary": "Montee dramatique principale de cet arc.",
                    "target_emotion": "tension",
                    "chapter_start": start,
                    "chapter_end": end,
                }
            )
            for chapter_index in range(start, end + 1):
                chapters.append(
                    {
                        "index": chapter_index,
                        "title": f"Chapitre {chapter_index}",
                        "summary": "Resume prevu du chapitre.",
                        "emotional_stake": "tension",
                        "arc_id": arc_id,
                        "cliffhanger_type": "revelation",
                        "status": "planned",
                    }
                )
        return {
            "global_summary": "Plan global du roman feuilleton.",
            "arcs": arcs,
            "chapters": chapters,
        }

    def _normalize_plan(
        self,
        plan: Dict[str, Any],
        chapter_count: int,
        arc_count: int,
    ) -> Dict[str, Any]:
        arcs = plan.get("arcs") if isinstance(plan.get("arcs"), list) else []
        chapters = plan.get("chapters") if isinstance(plan.get("chapters"), list) else []
        if not arcs or not chapters:
            return self._fallback_plan(chapter_count, arc_count)

        normalized_chapters: List[Dict[str, Any]] = []
        for idx in range(1, chapter_count + 1):
            source = next(
                (item for item in chapters if int(item.get("index", 0)) == idx),
                None,
            )
            arc_id = source.get("arc_id") if source else None
            normalized_chapters.append(
                {
                    "index": idx,
                    "title": (source or {}).get("title") or f"Chapitre {idx}",
                    "summary": (source or {}).get("summary") or "Resume prevu du chapitre.",
                    "emotional_stake": (source or {}).get("emotional_stake") or "tension",
                    "arc_id": arc_id,
                    "cliffhanger_type": (source or {}).get("cliffhanger_type") or "revelation",
                    "status": (source or {}).get("status") or "planned",
                }
            )

        normalized_arcs: List[Dict[str, Any]] = []
        for arc_index in range(arc_count):
            arc_id = arcs[arc_index].get("id") if arc_index < len(arcs) else f"arc-{arc_index + 1}"
            normalized_arcs.append(
                {
                    "id": arc_id or f"arc-{arc_index + 1}",
                    "title": arcs[arc_index].get("title") if arc_index < len(arcs) else f"Arc {arc_index + 1}",
                    "summary": arcs[arc_index].get("summary") if arc_index < len(arcs) else "Resume de l'arc.",
                    "target_emotion": arcs[arc_index].get("target_emotion") if arc_index < len(arcs) else "tension",
                    "chapter_start": arcs[arc_index].get("chapter_start") if arc_index < len(arcs) else 1,
                    "chapter_end": arcs[arc_index].get("chapter_end") if arc_index < len(arcs) else chapter_count,
                }
            )

        return {
            "global_summary": plan.get("global_summary") or "Plan global du roman feuilleton.",
            "arcs": normalized_arcs,
            "chapters": normalized_chapters,
        }

    def _get_chapter_min(self, metadata: Dict[str, Any]) -> int:
        default_min = settings.CHAPTER_MIN_WORDS
        default_max = settings.CHAPTER_MAX_WORDS
        raw_min = int(((metadata.get("chapter_word_range") or {}).get("min") or default_min))
        raw_max = int(((metadata.get("chapter_word_range") or {}).get("max") or default_max))
        use_defaults = raw_min < 1 or raw_max < 1 or raw_min > default_max or raw_max > default_max
        if raw_max < raw_min:
            use_defaults = True
        if use_defaults:
            return default_min
        min_words = max(default_min, raw_min)
        max_words = min(default_max, raw_max)
        if min_words > max_words:
            return default_min
        return min_words

    def _get_chapter_max(self, metadata: Dict[str, Any]) -> int:
        default_min = settings.CHAPTER_MIN_WORDS
        default_max = settings.CHAPTER_MAX_WORDS
        raw_min = int(((metadata.get("chapter_word_range") or {}).get("min") or default_min))
        raw_max = int(((metadata.get("chapter_word_range") or {}).get("max") or default_max))
        use_defaults = raw_min < 1 or raw_max < 1 or raw_min > default_max or raw_max > default_max
        if raw_max < raw_min:
            use_defaults = True
        if use_defaults:
            return default_max
        min_words = max(default_min, raw_min)
        max_words = min(default_max, raw_max)
        if min_words > max_words:
            return default_max
        return max_words
