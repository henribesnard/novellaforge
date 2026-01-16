"""Writing pipeline orchestrated with LangGraph for NovellaForge."""
from __future__ import annotations

from typing import Dict, Any, List, Optional, TypedDict
from uuid import UUID
import json
import math

from langgraph.graph import StateGraph, END
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentType
from app.models.project import Project
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.context_service import ProjectContextService
from app.services.document_service import DocumentService
from app.services.llm_client import DeepSeekClient
from app.services.rag_service import RagService
from app.services.memory_service import MemoryService


class ChapterPlan(TypedDict):
    chapter_number: int
    scene_beats: List[str]
    target_emotion: str
    required_plot_points: List[str]
    cliffhanger_type: str
    estimated_word_count: int


class NovelState(TypedDict, total=False):
    project_id: UUID
    user_id: UUID
    chapter_id: Optional[UUID]
    chapter_index: Optional[int]
    chapter_title: str
    chapter_summary: str
    chapter_emotional_stake: str
    chapter_instruction: Optional[str]
    target_word_count: Optional[int]
    min_word_count: int
    max_word_count: int
    use_rag: bool
    reindex_documents: bool
    create_document: bool
    auto_approve: bool
    project_context: Dict[str, Any]
    retrieved_chunks: List[str]
    style_chunks: List[str]
    memory_context: str
    current_plan: Optional[ChapterPlan]
    chapter_text: str
    critique_score: float
    critique_feedback: List[str]
    critique_payload: Dict[str, Any]
    revision_count: int
    continuity_alerts: List[str]
    debug_reasoning: List[str]


class WritingPipeline:
    """GraphNovel-inspired pipeline for serial chapter generation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.context_service = ProjectContextService(db)
        self.rag_service = RagService()
        self.memory_service = MemoryService()
        self.llm_client = DeepSeekClient()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(NovelState)
        graph.add_node("collect_context", self.collect_context)
        graph.add_node("retrieve_context", self.retrieve_context)
        graph.add_node("plan_chapter", self.plan_chapter)
        graph.add_node("write_chapter", self.write_chapter)
        graph.add_node("critic", self.critic)

        graph.set_entry_point("collect_context")
        graph.add_edge("collect_context", "retrieve_context")
        graph.add_edge("retrieve_context", "plan_chapter")
        graph.add_edge("plan_chapter", "write_chapter")
        graph.add_edge("write_chapter", "critic")

        graph.add_conditional_edges(
            "critic",
            self._quality_gate,
            {
                "revise": "write_chapter",
                "done": END,
            },
        )
        return graph.compile()

    async def collect_context(self, state: NovelState) -> Dict[str, Any]:
        context = await self.context_service.build_project_context(
            project_id=state["project_id"],
            user_id=state["user_id"],
        )
        metadata = context.get("project", {}).get("metadata", {})
        chapter_range = metadata.get("chapter_word_range") if isinstance(metadata, dict) else None
        default_min = settings.CHAPTER_MIN_WORDS
        default_max = settings.CHAPTER_MAX_WORDS
        raw_min = int((chapter_range or {}).get("min") or default_min)
        raw_max = int((chapter_range or {}).get("max") or default_max)
        use_defaults = raw_min < 1 or raw_max < 1 or raw_min > default_max or raw_max > default_max
        if raw_max < raw_min:
            use_defaults = True
        if use_defaults:
            min_words = default_min
            max_words = default_max
        else:
            min_words = max(default_min, raw_min)
            max_words = min(default_max, raw_max)
            if min_words > max_words:
                min_words = default_min
                max_words = default_max
        target_word_count = state.get("target_word_count")
        if target_word_count:
            target_word_count = max(min_words, min(int(target_word_count), max_words))
        else:
            target_word_count = int((min_words + max_words) / 2)

        chapter_context = await self._resolve_chapter_context(state, context)

        return {
            "project_context": context,
            "min_word_count": min_words,
            "max_word_count": max_words,
            "target_word_count": target_word_count,
            **chapter_context,
        }

    async def retrieve_context(self, state: NovelState) -> Dict[str, Any]:
        if not state.get("use_rag", True):
            return {"retrieved_chunks": [], "style_chunks": [], "memory_context": ""}

        if state.get("reindex_documents"):
            documents = await self._load_project_documents(state["project_id"])
            await self.rag_service.aindex_documents(state["project_id"], documents, clear_existing=True)

        query = f"{state.get('chapter_title', '')}\n{state.get('chapter_summary', '')}".strip()
        chunks = await self.rag_service.aretrieve(
            project_id=state["project_id"],
            query=query,
            top_k=settings.RAG_TOP_K,
        )
        memory_context = self.memory_service.build_context_block(
            state.get("project_context", {}).get("project", {}).get("metadata", {})
        )
        style_chunks = self.memory_service.retrieve_style_memory(
            str(state["project_id"]),
            query,
            top_k=3,
        )
        return {
            "retrieved_chunks": chunks,
            "style_chunks": style_chunks,
            "memory_context": memory_context,
        }

    async def plan_chapter(self, state: NovelState) -> Dict[str, Any]:
        if state.get("current_plan"):
            return {}

        project = state.get("project_context", {}).get("project", {})
        concept = project.get("concept") or {}
        plan = project.get("plan") or {}
        summaries = project.get("recent_chapter_summaries") or []
        summary_block = "\n".join([f"- {item}" for item in summaries][-5:]) or "aucun"
        chapter_index = state.get("chapter_index") or 1

        prompt = (
            "Tu es un assistant de planification de romans feuilleton. "
            "Reponds en francais uniquement. "
            "Retourne un JSON strict avec les cles: chapter_number, scene_beats, "
            "target_emotion, required_plot_points, cliffhanger_type, estimated_word_count. "
            "Le cliffhanger doit etre fort et adapte au pay-to-read.\n"
            f"Genre: {project.get('genre')}\n"
            f"Premisse: {concept.get('premise', '')}\n"
            f"Ton: {concept.get('tone', '')}\n"
            f"Tropes: {', '.join(concept.get('tropes', []))}\n"
            f"Synopsis global: {plan.get('global_summary', '')}\n"
            f"Index du chapitre: {chapter_index}\n"
            f"Resume du chapitre: {state.get('chapter_summary', '')}\n"
            f"Enjeu emotionnel: {state.get('chapter_emotional_stake', '')}\n"
            f"Recents resumes:\n{summary_block}\n"
            "Retourne uniquement le JSON."
        )
        message = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=900,
            model=settings.DEEPSEEK_REASONING_MODEL,
            response_format={"type": "json_object"},
            return_full=True,
        )
        plan_data = self._safe_json(message.get("content", ""))
        current_plan = self._normalize_plan(plan_data, chapter_index, state.get("target_word_count"))
        reasoning = self._extract_reasoning(message)
        return {
            "current_plan": current_plan,
            "debug_reasoning": [reasoning] if reasoning else [],
        }

    async def write_chapter(self, state: NovelState) -> Dict[str, Any]:
        plan = state.get("current_plan") or {}
        beats = plan.get("scene_beats") or []
        if not beats:
            beats = ["Mise en place", "Montee en tension", "Revelation cliffhanger"]

        project = state.get("project_context", {}).get("project", {})
        concept = project.get("concept") or {}
        chapter_title = state.get("chapter_title")
        min_words = state.get("min_word_count", settings.CHAPTER_MIN_WORDS)
        max_words = state.get("max_word_count", settings.CHAPTER_MAX_WORDS)
        target_word_count = state.get("target_word_count") or plan.get("estimated_word_count") or int((min_words + max_words) / 2)
        # Distribute target conservatively across beats to stay near the expected length.
        per_beat_target = max(180, int(target_word_count / len(beats) * 0.85))

        base_prompt = (
            "Ecris en francais le chapitre suivant d'un roman feuilleton. "
            "Si des informations ci-dessous sont en anglais, adapte-les en francais. "
            "Paragraphes courts pour lecture mobile. Termine par un cliffhanger fort et une phrase complete.\n"
            f"Objectif principal: environ {target_word_count} mots.\n"
            f"Objectif: {min_words}-{max_words} mots. Ne depasse pas {max_words} mots.\n"
            f"Titre du chapitre: {chapter_title}\n"
            f"Resume du chapitre: {state.get('chapter_summary', '')}\n"
            f"Enjeu emotionnel: {state.get('chapter_emotional_stake', '')}\n"
            f"Emotion cible: {plan.get('target_emotion', '')}\n"
            f"Type de cliffhanger: {plan.get('cliffhanger_type', '')}\n"
            f"Premisse: {concept.get('premise', '')}\n"
            f"Ton: {concept.get('tone', '')}\n"
            f"Tropes: {', '.join(concept.get('tropes', []))}\n"
            f"Contexte memoire:\n{state.get('memory_context', '')}\n"
        )

        style_block = "\n".join(state.get("style_chunks", [])[:3])
        if style_block:
            base_prompt += f"References de style:\n{style_block}\n"

        rag_block = "\n\n".join(state.get("retrieved_chunks", [])[:3])
        if rag_block:
            base_prompt += f"Extraits pertinents:\n{rag_block}\n"

        revision_notes = state.get("critique_feedback") or []
        instruction = state.get("chapter_instruction")
        if revision_notes or instruction:
            notes = "\n".join([f"- {note}" for note in (revision_notes + ([instruction] if instruction else []))])
            base_prompt += f"Axes de revision:\n{notes}\n"

        content = ""
        current_words = 0
        for idx, beat in enumerate(beats):
            beats_left = len(beats) - idx
            remaining = max_words - current_words
            if remaining <= 0:
                break
            dynamic_target = max(120, int(remaining / beats_left * 0.9))
            beat_target = min(per_beat_target, dynamic_target, remaining)
            continuation_hint = self._build_continuation_hint(content)
            beat_prompt = (
                f"{base_prompt}\n"
                f"Scene {idx + 1}/{len(beats)}: {beat}\n"
                f"Nombre de mots actuel: {current_words}\n"
                f"Reste environ {remaining} mots pour terminer le chapitre.\n"
                f"Ecris environ {beat_target} mots.\n"
                f"Ne depasse pas {max_words} mots au total. Termine par une phrase complete.\n"
                f"{continuation_hint}\n"
                "Retourne uniquement la suite du chapitre."
            )
            part = await self.llm_client.chat(
                messages=[
                    {"role": "system", "content": "Tu es un auteur de fiction feuilleton."},
                    {"role": "user", "content": beat_prompt},
                ],
                temperature=0.7,
                max_tokens=self._max_tokens_for_words(beat_target),
            )
            part = (part or "").strip()
            if not part:
                break
            content = f"{content}\n\n{part}" if content else part
            current_words = self._count_words(content)

        current_words = self._count_words(content)
        if current_words > max_words:
            content = await self._condense_to_word_limit(
                content,
                min_words=min_words,
                max_words=max_words,
                target_word_count=target_word_count,
            )
            current_words = self._count_words(content)

        return {
            "chapter_text": content,
        }

    async def critic(self, state: NovelState) -> Dict[str, Any]:
        text = state.get("chapter_text", "")
        if not text:
            return {
                "critique_score": 0.0,
                "critique_feedback": ["No content generated."],
                "critique_payload": {},
                "revision_count": state.get("revision_count", 0) + 1,
            }

        prompt = (
            "Evaluate the chapter for pacing, cliffhanger, and coherence. "
            "Return JSON with keys: score (0-10), issues (list), suggestions (list), "
            "cliffhanger_ok (bool), pacing_ok (bool), continuity_risks (list).\n"
            f"Word count target: {state.get('min_word_count')} - {state.get('max_word_count')}\n"
            f"Chapter text:\n{text[-6000:]}"
        )
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        payload = self._safe_json(response)
        score = float(payload.get("score") or 0.0)
        issues = payload.get("issues") or []
        suggestions = payload.get("suggestions") or []
        continuity_alerts = payload.get("continuity_risks") or []
        feedback = [*issues, *suggestions]
        revision_count = state.get("revision_count", 0)
        return {
            "critique_score": score,
            "critique_feedback": feedback,
            "critique_payload": payload,
            "revision_count": revision_count + 1,
            "continuity_alerts": continuity_alerts,
        }

    def _quality_gate(self, state: NovelState) -> str:
        score = state.get("critique_score", 0.0)
        word_count = self._count_words(state.get("chapter_text", ""))
        min_words = state.get("min_word_count", settings.CHAPTER_MIN_WORDS)
        max_words = state.get("max_word_count", settings.CHAPTER_MAX_WORDS)
        if score >= 8.0 and min_words <= word_count <= max_words:
            return "done"
        if state.get("revision_count", 0) >= 3:
            return "done"
        return "revise"

    async def generate_chapter(self, state: NovelState) -> Dict[str, Any]:
        result = await self.graph.ainvoke(state)
        chapter_text = result.get("chapter_text", "")
        word_count = self._count_words(chapter_text)

        document_id = None
        if state.get("create_document", True):
            document_id = await self._persist_draft(state, result, chapter_text, word_count)

        if state.get("auto_approve") and document_id:
            await self.approve_chapter(document_id, state["user_id"])

        return {
            "chapter_title": result.get("chapter_title", ""),
            "plan": result.get("current_plan"),
            "chapter_text": chapter_text,
            "document_id": document_id,
            "word_count": word_count,
            "critique": result.get("critique_payload"),
            "continuity_alerts": result.get("continuity_alerts", []),
            "retrieved_chunks": result.get("retrieved_chunks", []),
        }

    async def approve_chapter(self, document_id: str, user_id: UUID) -> Dict[str, Any]:
        document_service = DocumentService(self.db)
        document = await document_service.get_by_id(UUID(str(document_id)), user_id)
        if not document:
            return {}

        metadata = document.document_metadata if isinstance(document.document_metadata, dict) else {}
        chapter_text = document.content or ""
        facts = await self.memory_service.extract_facts(chapter_text)
        summary = facts.get("summary") or metadata.get("summary")

        project_context = await self.context_service.build_project_context(document.project_id, user_id)
        project_metadata = project_context.get("project", {}).get("metadata", {})
        project_metadata = self.memory_service.merge_facts(project_metadata, facts)

        recent = project_metadata.get("recent_chapter_summaries") or []
        if summary:
            recent.append(summary)
        project_metadata["recent_chapter_summaries"] = recent[-10:]

        plan_entry = project_metadata.get("plan") or {}
        plan_data = plan_entry.get("data") if isinstance(plan_entry, dict) else None
        if plan_data and metadata.get("chapter_index"):
            for chapter in plan_data.get("chapters", []):
                if int(chapter.get("index", 0)) == int(metadata.get("chapter_index")):
                    chapter["status"] = "approved"
                    break
            plan_entry["data"] = plan_data
            project_metadata["plan"] = plan_entry

        await self._update_project_metadata(document.project_id, project_metadata)
        metadata["status"] = "approved"
        if summary:
            metadata["summary"] = summary
        await document_service.update(
            document.id,
            DocumentUpdate(content=chapter_text, metadata=metadata),
            user_id,
        )

        self.memory_service.update_neo4j(facts)
        self.memory_service.store_style_memory(
            str(document.project_id),
            str(document.id),
            chapter_text,
            summary,
        )

        return {
            "document_id": str(document.id),
            "status": "approved",
            "summary": summary,
        }

    async def _persist_draft(
        self,
        state: NovelState,
        result: Dict[str, Any],
        chapter_text: str,
        word_count: int,
    ) -> Optional[str]:
        document_service = DocumentService(self.db)
        chapter_title = result.get("chapter_title") or state.get("chapter_title") or "Chapitre"
        chapter_index = state.get("chapter_index")
        metadata = {
            "status": "draft",
            "chapter_index": chapter_index,
            "summary": state.get("chapter_summary"),
            "emotional_stake": state.get("chapter_emotional_stake"),
            "cliffhanger_type": (result.get("current_plan") or {}).get("cliffhanger_type"),
            "chapter_plan": result.get("current_plan"),
        }

        if state.get("chapter_id"):
            updated = await document_service.update(
                state["chapter_id"],
                DocumentUpdate(content=chapter_text, metadata=metadata, title=chapter_title),
                state["user_id"],
            )
            return str(updated.id)

        order_index = await self._get_next_order_index(state["project_id"])
        document_data = DocumentCreate(
            title=chapter_title,
            content=chapter_text,
            document_type=DocumentType.CHAPTER,
            order_index=order_index,
            project_id=state["project_id"],
            metadata=metadata,
        )
        document = await document_service.create(document_data, user_id=state["user_id"])
        return str(document.id)

    async def _resolve_chapter_context(
        self,
        state: NovelState,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        chapter_id = state.get("chapter_id")
        plan = context.get("project", {}).get("plan") or {}
        if chapter_id:
            document = await self._get_document(chapter_id)
            if document.project_id != state["project_id"]:
                raise ValueError("Document does not belong to project")
            metadata = document.document_metadata if isinstance(document.document_metadata, dict) else {}
            return {
                "chapter_index": metadata.get("chapter_index") or document.order_index + 1,
                "chapter_title": document.title,
                "chapter_summary": metadata.get("summary") or "",
                "chapter_emotional_stake": metadata.get("emotional_stake") or "",
                "current_plan": metadata.get("chapter_plan"),
            }

        chapter_index = state.get("chapter_index")
        plan_chapters = plan.get("chapters") if isinstance(plan, dict) else None
        if not chapter_index and isinstance(plan_chapters, list):
            pending = [item for item in plan_chapters if item.get("status") != "approved"]
            chapter_index = pending[0].get("index") if pending else None

        if isinstance(plan_chapters, list) and chapter_index:
            chapter_entry = next(
                (item for item in plan_chapters if int(item.get("index", 0)) == int(chapter_index)),
                None,
            )
        else:
            chapter_entry = None

        if chapter_entry:
            return {
                "chapter_index": int(chapter_entry.get("index", chapter_index or 1)),
                "chapter_title": chapter_entry.get("title") or f"Chapitre {chapter_index}",
                "chapter_summary": chapter_entry.get("summary") or "",
                "chapter_emotional_stake": chapter_entry.get("emotional_stake") or "",
            }

        order_index = await self._get_next_order_index(state["project_id"])
        return {
            "chapter_index": order_index + 1,
            "chapter_title": f"Chapitre {order_index + 1}",
            "chapter_summary": state.get("chapter_instruction") or "",
            "chapter_emotional_stake": "tension",
        }

    async def _get_document(self, document_id: UUID) -> Document:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError("Document not found")
        return document

    async def _get_next_order_index(self, project_id: UUID) -> int:
        result = await self.db.execute(
            select(func.max(Document.order_index)).where(Document.project_id == project_id)
        )
        max_index = result.scalar()
        return (max_index + 1) if max_index is not None else 0

    async def _load_project_documents(self, project_id: UUID) -> List[Document]:
        result = await self.db.execute(
            select(Document).where(Document.project_id == project_id).order_by(Document.order_index.asc())
        )
        return list(result.scalars().all())

    async def _update_project_metadata(self, project_id: UUID, metadata: Dict[str, Any]) -> None:
        project = await self.db.get(Project, project_id)
        if not project:
            return
        project.project_metadata = metadata
        await self.db.commit()

    def _count_words(self, text: str) -> int:
        return len(text.split())

    def _max_tokens_for_words(self, word_target: int) -> int:
        # Approximate safety margin: ~3 tokens per word, capped by chat max.
        return min(settings.CHAT_MAX_TOKENS, max(120, int(word_target * 3)))

    async def _condense_to_word_limit(
        self,
        text: str,
        min_words: int,
        max_words: int,
        target_word_count: int,
    ) -> str:
        if not text:
            return text
        prompt = (
            "Reecris le chapitre ci-dessous en le condensant sans perdre l'intrigue, "
            "les personnages, les emotions et le cliffhanger. "
            "Le chapitre final doit etre complet et terminer par une phrase entiere. "
            f"Longueur cible: environ {target_word_count} mots. "
            f"Contrainte stricte: entre {min_words} et {max_words} mots.\n\n"
            "Chapitre a condenser:\n"
            f"{text}"
        )
        condensed = await self.llm_client.chat(
            messages=[
                {"role": "system", "content": "Tu es un auteur de fiction feuilleton."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=self._max_tokens_for_words(max_words),
        )
        condensed = (condensed or "").strip()
        if not condensed:
            return text
        if self._count_words(condensed) > max_words:
            tighter_max = max(min_words, max_words - 120)
            retry_prompt = (
                "Reecris le chapitre ci-dessous en restant strictement sous la limite. "
                "Le chapitre final doit etre complet, coherent, et terminer par une phrase entiere. "
                f"Contrainte stricte: entre {min_words} et {tighter_max} mots.\n\n"
                "Chapitre a condenser:\n"
                f"{condensed}"
            )
            condensed_retry = await self.llm_client.chat(
                messages=[
                    {"role": "system", "content": "Tu es un auteur de fiction feuilleton."},
                    {"role": "user", "content": retry_prompt},
                ],
                temperature=0.4,
                max_tokens=self._max_tokens_for_words(tighter_max),
            )
            condensed_retry = (condensed_retry or "").strip()
            if condensed_retry:
                return condensed_retry
        return condensed


    def _build_continuation_hint(self, text: str) -> str:
        if not text:
            return "Commence le chapitre depuis le debut."
        excerpt = text[-1200:]
        return (
            "Dernier extrait:\n"
            f"{excerpt}\n"
            "Continue depuis cet extrait sans repeter le debut."
        )

    def _safe_json(self, text: str) -> Dict[str, Any]:
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass
        return {}

    def _normalize_plan(self, plan: Dict[str, Any], chapter_index: int, target_words: Optional[int]) -> ChapterPlan:
        return {
            "chapter_number": int(plan.get("chapter_number") or chapter_index),
            "scene_beats": plan.get("scene_beats") or ["Mise en place", "Montee en tension", "Cliffhanger"],
            "target_emotion": plan.get("target_emotion") or "tension",
            "required_plot_points": plan.get("required_plot_points") or [],
            "cliffhanger_type": plan.get("cliffhanger_type") or "revelation",
            "estimated_word_count": int(
                plan.get("estimated_word_count")
                or target_words
                or int((settings.CHAPTER_MIN_WORDS + settings.CHAPTER_MAX_WORDS) / 2)
            ),
        }

    def _extract_reasoning(self, message: Dict[str, Any]) -> str:
        reasoning = message.get("reasoning_content") or ""
        content = message.get("content") or ""
        if not reasoning and "<think>" in content:
            start = content.find("<think>") + len("<think>")
            end = content.find("</think>")
            reasoning = content[start:end].strip() if end > start else ""
        return reasoning.strip()
