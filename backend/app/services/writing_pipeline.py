"""Writing pipeline orchestrated with LangGraph for NovellaForge."""
from __future__ import annotations

from typing import Dict, Any, List, Optional, TypedDict
from uuid import UUID, uuid4
from datetime import datetime
from collections import OrderedDict
import asyncio
import hashlib
import json
import logging
import time

from langgraph.graph import StateGraph, END
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentType
from app.models.project import Project
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.context_service import ProjectContextService, SmartContextTruncator
from app.services.document_service import DocumentService
from app.services.llm_client import DeepSeekClient
from app.services.rag_service import RagService
from app.services.memory_service import MemoryService
from app.services.cache_service import CacheService
from app.services.agents.consistency_analyst import ConsistencyAnalyst


logger = logging.getLogger(__name__)


_MEMORY_CONTEXT_CACHE: "OrderedDict[str, str]" = OrderedDict()
_MEMORY_CONTEXT_CACHE_MAX = 128


class ChapterPlan(TypedDict):
    chapter_number: int
    scene_beats: List[str]
    target_emotion: str
    required_plot_points: List[str]
    optional_subplots: List[str]
    arc_constraints: List[str]
    forbidden_actions: List[str]
    success_criteria: str
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
    max_revisions: int
    beat_texts: List[str]
    continuity_alerts: List[str]
    continuity_validation: Dict[str, Any]
    graph_issues: List[Dict[str, Any]]
    debug_reasoning: List[str]


class WritingPipeline:
    """GraphNovel-inspired pipeline for serial chapter generation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.context_service = ProjectContextService(db)
        self.rag_service = RagService()
        self.memory_service = MemoryService()
        self.cache_service = CacheService()
        self.llm_client = DeepSeekClient()
        self.consistency_analyst = ConsistencyAnalyst()
        self.graph = self._build_graph()

    def _log_duration(self, name: str, start: float) -> None:
        elapsed = time.perf_counter() - start
        print(f"[PERF] {name} took {elapsed:.2f}s")
        if logger.hasHandlers() and logger.isEnabledFor(logging.INFO):
            logger.info("[PERF] %s took %.2fs", name, elapsed)

    async def _timed_chat(self, name: str, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return await self.llm_client.chat(**kwargs)
        finally:
            self._log_duration(name, start)

    async def _timed_graph_validation(self, state: NovelState) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            return await self._validate_with_graph(state)
        finally:
            self._log_duration("validate_continuity.graph", start)

    def _build_graph(self):
        graph = StateGraph(NovelState)
        graph.add_node("collect_context", self.collect_context)
        graph.add_node("retrieve_context", self.retrieve_context)
        graph.add_node("plan_chapter", self.plan_chapter)
        graph.add_node("write_chapter", self.write_chapter)
        graph.add_node("validate_continuity", self.validate_continuity)
        graph.add_node("critic", self.critic)

        graph.set_entry_point("collect_context")
        graph.add_edge("collect_context", "retrieve_context")
        graph.add_edge("retrieve_context", "plan_chapter")
        graph.add_edge("plan_chapter", "write_chapter")
        graph.add_edge("write_chapter", "validate_continuity")
        graph.add_edge("validate_continuity", "critic")

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
        start = time.perf_counter()
        try:
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
                target_word_count = int(target_word_count)
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
        finally:
            self._log_duration("collect_context", start)

    async def retrieve_context(self, state: NovelState) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            metadata = state.get("project_context", {}).get("project", {}).get("metadata", {})
            chapter_index = state.get("chapter_index") or 1
            
            # Composite key for cache (integrity + relevance)
            cache_identity = {"metadata": metadata, "chapter_index": chapter_index}
            
            # 1. Try to get cached memory context
            memory_context = await self.cache_service.get_memory_context(cache_identity)
            if not memory_context:
                # Use Smart Truncation
                continuity = metadata.get("continuity", {})
                memory_context = SmartContextTruncator.truncate_memory_context(
                    continuity,
                    max_chars=settings.MEMORY_CONTEXT_MAX_CHARS,
                    current_chapter=chapter_index
                )
                # Async update cache
                await self.cache_service.set_memory_context(cache_identity, memory_context)

            if memory_context:
                logger.debug("Memory context preview: %s...", memory_context[:500])

            if not state.get("use_rag", True):
                return {"retrieved_chunks": [], "style_chunks": [], "memory_context": memory_context}

            if state.get("reindex_documents"):
                documents = await self._load_project_documents(state["project_id"])
                await self.rag_service.aindex_documents(state["project_id"], documents, clear_existing=True)

            query = f"{state.get('chapter_title', '')}\n{state.get('chapter_summary', '')}".strip()
            
            # 2. Try to get cached RAG results
            chunks = await self.cache_service.get_rag_results(query, str(state["project_id"]))
            if chunks is None:
                chunks = await self.rag_service.aretrieve(
                    project_id=state["project_id"],
                    query=query,
                    top_k=settings.RAG_TOP_K,
                )
                await self.cache_service.set_rag_results(query, str(state["project_id"]), chunks)

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
        finally:
            self._log_duration("retrieve_context", start)

    async def plan_chapter(self, state: NovelState) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            if state.get("current_plan"):
                return {}

            # Check for pregenerated plans
            chapter_index = state.get("chapter_index") or 1
            project_meta = state.get("project_context", {}).get("project", {}).get("metadata", {})
            pregenerated_plans = project_meta.get("pregenerated_plans", {})
            if isinstance(pregenerated_plans, dict) and str(chapter_index) in pregenerated_plans:
                pregenerated = pregenerated_plans[str(chapter_index)]
                if pregenerated:
                    logger.info(f"Using pregenerated plan for chapter {chapter_index}")
                    return {"current_plan": pregenerated, "debug_reasoning": ["pregenerated"]}

            project = state.get("project_context", {}).get("project", {})
            project_data: Dict[str, Any] = project if isinstance(project, dict) else {}
            concept_raw = project_data.get("concept")
            concept: Dict[str, Any] = concept_raw if isinstance(concept_raw, dict) else {}
            plan_raw = project_data.get("plan")
            plan: Dict[str, Any] = plan_raw if isinstance(plan_raw, dict) else {}
            summaries_raw = project_data.get("recent_chapter_summaries")
            summaries = summaries_raw if isinstance(summaries_raw, list) else []
            summary_block = "\n".join([f"- {item}" for item in summaries][-5:]) or "aucun"
            memory_context = self._truncate_text(state.get("memory_context", ""), settings.MEMORY_CONTEXT_MAX_CHARS)
            plan_entry = self._find_plan_entry(plan, chapter_index)
            if self._plan_entry_has_details(plan_entry):
                current_plan = self._normalize_plan(
                    plan_entry or {},
                    chapter_index,
                    state.get("target_word_count"),
                )
                return {"current_plan": current_plan, "debug_reasoning": []}
            plan_required_points = self._normalize_str_list(
                plan_entry.get("required_plot_points") if plan_entry else None
            )
            plan_optional_subplots = self._normalize_str_list(
                plan_entry.get("optional_subplots") if plan_entry else None
            )
            plan_arc_constraints = self._normalize_str_list(
                plan_entry.get("arc_constraints") if plan_entry else None
            )
            plan_forbidden_actions = self._normalize_str_list(
                plan_entry.get("forbidden_actions") if plan_entry else None
            )
            plan_success_criteria = str(plan_entry.get("success_criteria") or "") if plan_entry else ""

            prompt = (
                "Tu es un assistant de planification de romans feuilleton. "
                "Reponds en francais uniquement. "
                "Retourne un JSON strict avec les cles: chapter_number, scene_beats, "
                "target_emotion, required_plot_points, optional_subplots, arc_constraints, "
                "forbidden_actions, success_criteria, cliffhanger_type, estimated_word_count. "
                "Le cliffhanger doit etre fort et adapte au pay-to-read.\n"
                f"Genre: {project_data.get('genre')}\n"
                f"Premisse: {concept.get('premise', '')}\n"
                f"Ton: {concept.get('tone', '')}\n"
                f"Tropes: {', '.join(concept.get('tropes', []))}\n"
                f"Synopsis global: {plan.get('global_summary', '')}\n"
                f"Index du chapitre: {chapter_index}\n"
                f"Resume du chapitre: {state.get('chapter_summary', '')}\n"
                f"Enjeu emotionnel: {state.get('chapter_emotional_stake', '')}\n"
                f"Recents resumes:\n{summary_block}\n"
                f"Contexte memoire:\n{memory_context}\n"
                "Si des contraintes du plan global sont fournies, reutilise-les dans les champs correspondants.\n"
                "Retourne uniquement le JSON."
            )
            if plan_required_points:
                prompt += f"\nPoints d'intrigue requis (plan global): {', '.join(plan_required_points)}"
            if plan_optional_subplots:
                prompt += f"\nSous-intrigues suggerees (plan global): {', '.join(plan_optional_subplots)}"
            if plan_arc_constraints:
                prompt += f"\nContraintes d'arc (plan global): {', '.join(plan_arc_constraints)}"
            if plan_forbidden_actions:
                prompt += f"\nActions interdites (plan global): {', '.join(plan_forbidden_actions)}"
            if plan_success_criteria:
                prompt += f"\nCriteres de succes (plan global): {plan_success_criteria}"
            use_reasoning = self._should_use_reasoning(chapter_index, state.get("chapter_instruction"))
            model = settings.DEEPSEEK_REASONING_MODEL if use_reasoning else settings.DEEPSEEK_MODEL
            message = await self._timed_chat(
                "plan_chapter.llm",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=900,
                model=model,
                response_format={"type": "json_object"},
                return_full=True,
            )
            plan_data = self._safe_json(message.get("content", ""))
            current_plan = self._normalize_plan(plan_data, chapter_index, state.get("target_word_count"))
            if plan_required_points:
                current_plan["required_plot_points"] = plan_required_points
            if plan_optional_subplots:
                current_plan["optional_subplots"] = plan_optional_subplots
            if plan_arc_constraints:
                current_plan["arc_constraints"] = plan_arc_constraints
            if plan_forbidden_actions:
                current_plan["forbidden_actions"] = plan_forbidden_actions
            if plan_success_criteria:
                current_plan["success_criteria"] = plan_success_criteria
            reasoning = self._extract_reasoning(message)
            return {
                "current_plan": current_plan,
                "debug_reasoning": [reasoning] if reasoning else [],
            }
        finally:
            self._log_duration("plan_chapter", start)

    async def write_chapter(self, state: NovelState) -> Dict[str, Any]:
        start = time.perf_counter()
        plan_raw = state.get("current_plan")
        plan: Dict[str, Any] = dict(plan_raw) if isinstance(plan_raw, dict) else {}
        beats = plan.get("scene_beats") or []
        if not beats:
            beats = ["Mise en place", "Montee en tension", "Revelation cliffhanger"]

        project = state.get("project_context", {}).get("project", {})
        concept = project.get("concept") or {}
        chapter_title = state.get("chapter_title")
        min_words = settings.CHAPTER_MIN_WORDS
        max_words = settings.CHAPTER_MAX_WORDS
        target_word_count = (
            state.get("target_word_count")
            or plan.get("estimated_word_count")
            or int((min_words + max_words) / 2)
        )
        target_word_count = int(target_word_count)
        if target_word_count < min_words:
            target_word_count = min_words
        elif target_word_count > max_words:
            target_word_count = max_words
        min_beat_words = settings.WRITE_MIN_BEAT_WORDS
        # Distribute target conservatively across beats to stay near the expected length.
        per_beat_target = max(min_beat_words, int(target_word_count / len(beats) * 0.85))

        base_prompt = (
            "Ecris en francais le chapitre suivant d'un roman feuilleton. "
            "Si des informations ci-dessous sont en anglais, adapte-les en francais. "
            "Paragraphes courts pour lecture mobile. Termine par un cliffhanger fort et une phrase complete.\n"
            f"Objectif principal: environ {target_word_count} mots.\n"
            f"Objectif: {min_words}-{max_words} mots. Reste dans cette plage.\n"
            f"Titre du chapitre: {chapter_title}\n"
            f"Resume du chapitre: {state.get('chapter_summary', '')}\n"
            f"Enjeu emotionnel: {state.get('chapter_emotional_stake', '')}\n"
            f"Emotion cible: {plan.get('target_emotion', '')}\n"
            f"Type de cliffhanger: {plan.get('cliffhanger_type', '')}\n"
            f"Premisse: {concept.get('premise', '')}\n"
            f"Ton: {concept.get('tone', '')}\n"
            f"Tropes: {', '.join(concept.get('tropes', []))}\n"
        )

        plot_constraints = self._resolve_plot_constraints(state, plan)
        required_plot_points = plot_constraints.get("required_plot_points") or []
        forbidden_actions = plot_constraints.get("forbidden_actions") or []
        success_criteria = plot_constraints.get("success_criteria") or ""
        if required_plot_points:
            base_prompt += "Points d'intrigue requis:\n"
            base_prompt += "\n".join([f"- {point}" for point in required_plot_points]) + "\n"
        if forbidden_actions:
            base_prompt += "Actions interdites:\n"
            base_prompt += "\n".join([f"- {action}" for action in forbidden_actions]) + "\n"
        if success_criteria:
            base_prompt += f"Criteres de succes: {success_criteria}\n"

        story_bible = state.get("project_context", {}).get("story_bible", {})
        bible_block = self._build_bible_context_block(story_bible)
        bible_block = self._truncate_text(bible_block, settings.STORY_BIBLE_MAX_CHARS)
        if bible_block:
            logger.debug("Story bible preview: %s...", bible_block[:500])
            base_prompt += f"Story bible (regles critiques):\n{bible_block}\n"

        memory_context = self._truncate_text(state.get("memory_context", ""), settings.MEMORY_CONTEXT_MAX_CHARS)
        base_prompt += f"Contexte memoire:\n{memory_context}\n"

        style_block = "\n".join(state.get("style_chunks", [])[:3])
        style_block = self._truncate_text(style_block, settings.STYLE_CONTEXT_MAX_CHARS)
        if style_block:
            base_prompt += f"References de style:\n{style_block}\n"

        rag_block = "\n\n".join(state.get("retrieved_chunks", [])[:3])
        rag_block = self._truncate_text(rag_block, settings.RAG_CONTEXT_MAX_CHARS)
        if rag_block:
            base_prompt += f"Extraits pertinents:\n{rag_block}\n"

        revision_notes = state.get("critique_feedback") or []
        if not isinstance(revision_notes, list):
            revision_notes = [str(revision_notes)]
        plot_validation = state.get("continuity_validation") or {}
        plot_point_validation = plot_validation.get("plot_point_validation") or {}
        missing_points = plot_point_validation.get("missing_points") or []
        forbidden_violations = plot_point_validation.get("forbidden_violations") or []
        if missing_points:
            revision_notes.append(
                f"POINTS D'INTRIGUE MANQUANTS A AJOUTER: {', '.join(missing_points)}"
            )
        if forbidden_violations:
            revision_notes.append(
                f"ACTIONS INTERDITES A EVITER: {', '.join(forbidden_violations)}"
            )
        instruction = state.get("chapter_instruction")
        if revision_notes or instruction:
            notes = "\n".join([f"- {note}" for note in (revision_notes + ([instruction] if instruction else []))])
            base_prompt += f"Axes de revision:\n{notes}\n"

        beat_outline = self._build_beats_outline(beats)
        revision_count = int(state.get("revision_count") or 0)
        beat_texts = state.get("beat_texts") if isinstance(state.get("beat_texts"), list) else []

        if (
            settings.WRITE_PARTIAL_REVISION
            and revision_count > 0
            and beat_texts
            and len(beat_texts) == len(beats)
        ):
            previous_block = self._build_previous_beats_block(
                beat_texts[:-1], settings.WRITE_PREVIOUS_BEATS_MAX_CHARS
            )
            current_words = self._count_words("\n\n".join(beat_texts[:-1]))
            remaining_target = max(target_word_count - current_words, 0)
            beat_target = max(min_beat_words, remaining_target or per_beat_target)
            continuation_hint = (
                "Assume les scenes precedentes deja ecrites. Commence directement cette scene."
            )
            beat_prompt = self._build_beat_prompt(
                base_prompt=base_prompt,
                beat_outline=beat_outline,
                beat=beats[-1],
                beat_index=len(beats) - 1,
                total_beats=len(beats),
                beat_target=beat_target,
                current_words=current_words,
                remaining_target=remaining_target,
                max_words=max_words,
                continuation_hint=continuation_hint,
                previous_block=previous_block,
            )
            part = await self._timed_chat(
                f"write_chapter.beat_{len(beats)}",
                messages=[
                    {"role": "system", "content": "Tu es un auteur de fiction feuilleton."},
                    {"role": "user", "content": beat_prompt},
                ],
                temperature=0.7,
                max_tokens=self._max_tokens_for_words(beat_target),
            )
            part = (part or "").strip()
            updated = list(beat_texts)
            if part:
                updated[-1] = part
            content = "\n\n".join([text for text in updated if text])
            result = {"chapter_text": content, "beat_texts": updated}
            self._log_duration("write_chapter", start)
            return result

        # Distributed beats via Celery (true parallelism across workers)
        if settings.WRITE_DISTRIBUTED_BEATS and len(beats) > 1:
            try:
                from app.tasks.generation_tasks import generate_beats_distributed
                distributed_result = await generate_beats_distributed(
                    beats=beats,
                    base_prompt=base_prompt + f"\n{beat_outline}\n",
                    target_word_count=target_word_count,
                    min_beat_words=min_beat_words,
                )
                if distributed_result.get("chapter_text"):
                    result = {
                        "chapter_text": distributed_result["chapter_text"],
                        "beat_texts": distributed_result.get("beat_texts", []),
                    }
                    self._log_duration("write_chapter.distributed", start)
                    return result
                # Fall through to parallel if distributed failed
                logger.warning("Distributed beat generation failed, falling back to parallel")
            except Exception as e:
                logger.warning(f"Distributed beats unavailable: {e}, falling back to parallel")

        if settings.WRITE_PARALLEL_BEATS and len(beats) > 1:
            tasks = []
            for idx, beat in enumerate(beats):
                current_words = int(per_beat_target * idx)
                remaining_target = max(target_word_count - current_words, 0)
                beat_target = max(min_beat_words, min(per_beat_target, remaining_target or per_beat_target))
                continuation_hint = (
                    "Assume les scenes precedentes deja ecrites. Commence directement cette scene."
                )
                beat_prompt = self._build_beat_prompt(
                    base_prompt=base_prompt,
                    beat_outline=beat_outline,
                    beat=beat,
                    beat_index=idx,
                    total_beats=len(beats),
                    beat_target=beat_target,
                    current_words=current_words,
                    remaining_target=remaining_target,
                    max_words=max_words,
                    continuation_hint=continuation_hint,
                )
                tasks.append(
                    self._timed_chat(
                        f"write_chapter.beat_{idx + 1}",
                        messages=[
                            {"role": "system", "content": "Tu es un auteur de fiction feuilleton."},
                            {"role": "user", "content": beat_prompt},
                        ],
                        temperature=0.7,
                        max_tokens=self._max_tokens_for_words(beat_target),
                    )
                )
            parts = await asyncio.gather(*tasks)
            beat_texts = [(part or "").strip() for part in parts]
            content = "\n\n".join([text for text in beat_texts if text])
            result = {"chapter_text": content, "beat_texts": beat_texts}
            self._log_duration("write_chapter", start)
            return result

        content = ""
        current_words = 0
        beat_texts = []
        for idx, beat in enumerate(beats):
            beats_left = len(beats) - idx
            remaining_target = max(target_word_count - current_words, 0)
            if remaining_target == 0:
                beat_target = max(min_beat_words, int(per_beat_target * 0.5))
            else:
                dynamic_target = max(min_beat_words, int(remaining_target / beats_left))
                beat_target = max(min_beat_words, min(per_beat_target, dynamic_target))
            continuation_hint = self._build_continuation_hint(content)
            beat_prompt = self._build_beat_prompt(
                base_prompt=base_prompt,
                beat_outline=beat_outline,
                beat=beat,
                beat_index=idx,
                total_beats=len(beats),
                beat_target=beat_target,
                current_words=current_words,
                remaining_target=remaining_target,
                max_words=max_words,
                continuation_hint=continuation_hint,
            )
            part = await self._timed_chat(
                f"write_chapter.beat_{idx + 1}",
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
            beat_texts.append(part)
            content = f"{content}\n\n{part}" if content else part
            current_words = self._count_words(content)
            if current_words >= int(target_word_count * settings.WRITE_EARLY_STOP_RATIO):
                break

        result = {
            "chapter_text": content,
            "beat_texts": beat_texts,
        }
        self._log_duration("write_chapter", start)
        return result

    async def validate_continuity(self, state: NovelState) -> Dict[str, Any]:
        """Validate continuity using ConsistencyAnalyst."""
        start = time.perf_counter()
        chapter_text = state.get("chapter_text", "")
        if not chapter_text:
            result = {
                "continuity_validation": {
                    "severe_issues": [{"type": "missing_content", "detail": "No chapter text to validate."}],
                    "minor_issues": [],
                    "coherence_score": 0.0,
                    "blocking": False,
                }
            }
            self._log_duration("validate_continuity", start)
            return result

        chapter_text = self._truncate_text(chapter_text, settings.VALIDATION_MAX_CHARS)
        memory_context = self._truncate_text(state.get("memory_context", ""), settings.MEMORY_CONTEXT_MAX_CHARS)

        project_context = state.get("project_context") or {}
        project_meta = project_context.get("project", {}).get("metadata", {})
        story_bible = project_context.get("story_bible")
        if not isinstance(story_bible, dict) or not story_bible:
            story_bible = project_meta.get("story_bible") if isinstance(project_meta, dict) else {}
        if not isinstance(story_bible, dict):
            story_bible = {}

        previous_chapters = await self._get_previous_chapter_texts(
            state.get("project_id"),
            state.get("chapter_index"),
            limit=5,
        )

        analyst_task = self.consistency_analyst.execute(
            task_data={
                "action": "analyze_chapter",
                "chapter_text": chapter_text,
                "memory_context": memory_context,
                "story_bible": story_bible,
                "previous_chapters": previous_chapters,
            },
            context=project_context,
        )
        graph_task = self._timed_graph_validation(state)
        analyst_result, graph_payload = await asyncio.gather(analyst_task, graph_task)

        analysis = analyst_result.get("analysis") or {}
        validation = self._transform_analyst_result(analysis, state)

        resolved_descriptions = self._get_resolved_contradictions(state)
        if resolved_descriptions:
            validation["severe_issues"] = [
                issue for issue in validation.get("severe_issues", [])
                if issue.get("detail") not in resolved_descriptions
            ]
            validation["minor_issues"] = [
                issue for issue in validation.get("minor_issues", [])
                if issue.get("detail") not in resolved_descriptions
            ]
            if validation.get("blocking") and not validation["severe_issues"] and not validation["minor_issues"]:
                validation["blocking"] = False

        plan_entry_raw = state.get("current_plan")
        plan_entry: Dict[str, Any] = dict(plan_entry_raw) if isinstance(plan_entry_raw, dict) else {}
        plot_constraints = self._resolve_plot_constraints(state, plan_entry)
        required_plot_points = plot_constraints.get("required_plot_points") or []
        forbidden_actions = plot_constraints.get("forbidden_actions") or []

        plot_validation = {
            "covered_points": [],
            "missing_points": [],
            "forbidden_violations": [],
            "coverage_score": 0.0,
            "explanation": "",
        }
        plot_issues: List[Any] = []
        if required_plot_points or forbidden_actions:
            plot_validation = await self._validate_plot_points(
                chapter_text,
                required_plot_points,
                forbidden_actions,
            )
            plot_issues = plot_validation.get("issues") or []
        validation["plot_point_validation"] = {
            "covered_points": plot_validation.get("covered_points") or [],
            "missing_points": plot_validation.get("missing_points") or [],
            "forbidden_violations": plot_validation.get("forbidden_violations") or [],
            "coverage_score": float(plot_validation.get("coverage_score") or 0.0),
            "explanation": plot_validation.get("explanation") or "",
        }
        if plot_issues:
            valid_issues = [issue for issue in plot_issues if isinstance(issue, dict)]
            if valid_issues:
                validation["severe_issues"] = [*validation.get("severe_issues", []), *valid_issues]
                validation["blocking"] = True
                logger.debug("Plot point validation issues detected: %s", valid_issues)

        graph_issues = graph_payload.get("graph_issues") or []
        validation["graph_issues"] = graph_issues
        if graph_issues:
            for issue in graph_issues:
                if not isinstance(issue, dict):
                    continue
                severity = str(issue.get("severity") or "").lower()
                detail = issue.get("detail") or ""
                issue_type = issue.get("type") or "graph_issue"
                payload = {
                    "type": issue_type,
                    "detail": detail,
                    "severity": "blocking" if severity == "critical" else (severity or "warning"),
                    "source": issue.get("source") or "neo4j_graph",
                }
                if severity in ("critical", "high"):
                    validation["severe_issues"] = [*validation.get("severe_issues", []), payload]
                    if severity == "critical":
                        validation["blocking"] = True
                else:
                    validation["minor_issues"] = [*validation.get("minor_issues", []), payload]

        if resolved_descriptions:
            validation["graph_issues"] = [
                issue for issue in validation.get("graph_issues", [])
                if issue.get("detail") not in resolved_descriptions
            ]
            validation["severe_issues"] = [
                issue for issue in validation.get("severe_issues", [])
                if issue.get("detail") not in resolved_descriptions
            ]
            validation["minor_issues"] = [
                issue for issue in validation.get("minor_issues", [])
                if issue.get("detail") not in resolved_descriptions
            ]
            if validation.get("blocking") and not validation.get("severe_issues"):
                missing_points = validation.get("plot_point_validation", {}).get("missing_points") or []
                forbidden = validation.get("plot_point_validation", {}).get("forbidden_violations") or []
                if not missing_points and not forbidden:
                    validation["blocking"] = False

        if validation.get("severe_issues"):
            project_id = state.get("project_id")
            if project_id:
                for issue in validation["severe_issues"]:
                    if not isinstance(issue, dict):
                        continue
                    if not self._should_track_issue(issue):
                        continue
                    await self._track_contradiction(project_id, issue, state.get("chapter_index"))

        alerts = self._build_continuity_alerts(validation)
        result = {"continuity_validation": validation, "continuity_alerts": alerts}
        self._log_duration("validate_continuity", start)
        return result

    def _transform_analyst_result(
        self, analysis: Dict[str, Any], state: NovelState
    ) -> Dict[str, Any]:
        """Transform ConsistencyAnalyst output to pipeline format."""
        severe_issues = []
        minor_issues = []

        for contradiction in analysis.get("contradictions", []):
            severity = str(contradiction.get("severity") or "medium").lower()
            issue = {
                "type": contradiction.get("type", "contradiction"),
                "detail": contradiction.get("description", ""),
                "severity": "blocking" if severity == "critical" else severity,
                "source": "consistency_analyst",
                "suggested_fix": contradiction.get("suggested_fix", ""),
            }
            if severity in ("critical", "high"):
                severe_issues.append(issue)
            else:
                minor_issues.append(issue)

        for timeline_issue in analysis.get("timeline_issues", []):
            severity = str(timeline_issue.get("severity") or "medium").lower()
            issue = {
                "type": "timeline",
                "detail": timeline_issue.get("issue", ""),
                "severity": "blocking" if severity == "critical" else severity,
                "source": "consistency_analyst",
                "suggested_fix": timeline_issue.get("suggested_fix", ""),
            }
            if severity in ("critical", "high"):
                severe_issues.append(issue)
            else:
                minor_issues.append(issue)

        for char_issue in analysis.get("character_inconsistencies", []):
            severity = str(char_issue.get("severity") or "medium").lower()
            issue = {
                "type": "character",
                "detail": f"{char_issue.get('character', 'Unknown')}: {char_issue.get('issue', '')}",
                "severity": "blocking" if severity == "critical" else severity,
                "source": "consistency_analyst",
                "suggested_fix": char_issue.get("suggested_fix", ""),
                "previous_state": char_issue.get("previous_state", ""),
                "current_state": char_issue.get("current_state", ""),
            }
            if severity in ("critical", "high"):
                severe_issues.append(issue)
            else:
                minor_issues.append(issue)

        for rule_violation in analysis.get("world_rule_violations", []):
            severity = str(rule_violation.get("severity") or "medium").lower()
            issue = {
                "type": "world_rule",
                "detail": (
                    f"Regle violee: {rule_violation.get('rule', '')} - "
                    f"{rule_violation.get('violation', '')}"
                ),
                "severity": "blocking" if severity == "critical" else severity,
                "source": "consistency_analyst",
                "suggested_fix": rule_violation.get("suggested_fix", ""),
            }
            if severity in ("critical", "high"):
                severe_issues.append(issue)
            else:
                minor_issues.append(issue)

        blocking = any(issue.get("severity") == "blocking" for issue in severe_issues)

        return {
            "severe_issues": severe_issues,
            "minor_issues": minor_issues,
            "coherence_score": float(analysis.get("overall_coherence_score") or 7.0),
            "blocking": blocking,
            "blocking_issues": analysis.get("blocking_issues", []),
            "summary": analysis.get("summary", ""),
        }

    async def _get_previous_chapter_texts(
        self, project_id: Optional[UUID], chapter_index: Optional[int], limit: int = 5
    ) -> List[str]:
        """Retrieve previous chapter texts for context."""
        if not project_id or not chapter_index or chapter_index <= 1:
            return []

        doc_service = DocumentService(self.db)
        chapters = []
        for idx in range(max(1, chapter_index - limit), chapter_index):
            doc = await doc_service.get_chapter_by_index(project_id, idx)
            if doc and doc.content:
                content = doc.content[:2000] if len(doc.content) > 2000 else doc.content
                chapters.append(f"[Chapitre {idx}]\n{content}")
        return chapters

    async def critic(self, state: NovelState) -> Dict[str, Any]:
        start = time.perf_counter()
        text = state.get("chapter_text", "")
        if not text:
            result = {
                "critique_score": 0.0,
                "critique_feedback": ["No content generated."],
                "critique_payload": {},
                "revision_count": state.get("revision_count", 0) + 1,
            }
            self._log_duration("critic", start)
            return result

        memory_context = self._truncate_text(state.get("memory_context", ""), settings.MEMORY_CONTEXT_MAX_CHARS)
        rag_block = "\n\n".join(state.get("retrieved_chunks", [])[:3])
        rag_block = self._truncate_text(rag_block, settings.RAG_CONTEXT_MAX_CHARS)
        text = text[-settings.CRITIC_MAX_CHARS:]
        prompt = (
            "Evalue le chapitre pour le rythme, le cliffhanger et la coherence. "
            "Retourne un JSON avec les cles: score (0-10), issues (liste), suggestions (liste), "
            "cliffhanger_ok (bool), pacing_ok (bool), continuity_risks (liste).\n"
            f"Contexte memoire:\n{memory_context}\n"
            f"Extraits pertinents:\n{rag_block}\n"
            f"Texte du chapitre:\n{text}"
        )
        response = await self._timed_chat(
            "critic.llm",
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
        existing_alerts = state.get("continuity_alerts") or []
        if isinstance(existing_alerts, list):
            continuity_alerts = [*existing_alerts, *continuity_alerts]
        feedback = [*issues, *suggestions]
        revision_count = state.get("revision_count", 0)
        result = {
            "critique_score": score,
            "critique_feedback": feedback,
            "critique_payload": payload,
            "revision_count": revision_count + 1,
            "continuity_alerts": continuity_alerts,
        }
        self._log_duration("critic", start)
        return result

    def _quality_gate(self, state: NovelState) -> str:
        score = state.get("critique_score", 0.0)
        revision_count = int(state.get("revision_count") or 0)
        max_revisions = int(state.get("max_revisions") or settings.MAX_REVISIONS)
        if revision_count >= max_revisions:
            return "done"
        validation = state.get("continuity_validation") or {}
        is_blocking = bool(validation.get("blocking"))
        coherence_score = float(validation.get("coherence_score") or 0.0)
        if is_blocking:
            return "revise"
        if coherence_score < settings.QUALITY_GATE_COHERENCE_THRESHOLD:
            return "revise"
        plot_validation = validation.get("plot_point_validation") or {}
        missing_points = plot_validation.get("missing_points") or []
        forbidden_violations = plot_validation.get("forbidden_violations") or []
        if missing_points or forbidden_violations:
            return "revise"
        if score >= settings.QUALITY_GATE_SCORE_THRESHOLD:
            return "done"
        return "revise"

    async def generate_chapter(self, state: NovelState) -> Dict[str, Any]:
        start = time.perf_counter()
        state = dict(state)
        state.setdefault("max_revisions", settings.MAX_REVISIONS)
        result = await self.graph.ainvoke(state)
        chapter_text = result.get("chapter_text", "")
        word_count = self._count_words(chapter_text)

        document_id = None
        if state.get("create_document", True):
            document_id = await self._persist_draft(state, result, chapter_text, word_count)

        if state.get("auto_approve") and document_id:
            await self.approve_chapter(document_id, state["user_id"])

        response = {
            "chapter_title": result.get("chapter_title", ""),
            "plan": result.get("current_plan"),
            "chapter_text": chapter_text,
            "document_id": document_id,
            "word_count": word_count,
            "critique": result.get("critique_payload"),
            "continuity_alerts": result.get("continuity_alerts", []),
            "continuity_validation": result.get("continuity_validation"),
            "retrieved_chunks": result.get("retrieved_chunks", []),
        }
        self._log_duration("generate_chapter", start)
        return response

    async def approve_chapter(self, document_id: str, user_id: UUID) -> Dict[str, Any]:
        start = time.perf_counter()
        document_service = DocumentService(self.db)
        document = await document_service.get_by_id(UUID(str(document_id)), user_id)
        if not document:
            self._log_duration("approve_chapter", start)
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

        plan_entry_raw = project_metadata.get("plan")
        plan_entry: Dict[str, Any] = plan_entry_raw if isinstance(plan_entry_raw, dict) else {}
        plan_data = plan_entry.get("data")
        chapter_index = None
        raw_chapter_index = metadata.get("chapter_index")
        if raw_chapter_index is not None:
            try:
                chapter_index = int(raw_chapter_index)
            except (TypeError, ValueError):
                chapter_index = None
        if isinstance(plan_data, dict) and chapter_index is not None:
            chapters = plan_data.get("chapters")
            if isinstance(chapters, list):
                for chapter in chapters:
                    if not isinstance(chapter, dict):
                        continue
                    try:
                        chapter_idx = int(chapter.get("index", 0))
                    except (TypeError, ValueError):
                        continue
                    if chapter_idx == chapter_index:
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
            DocumentUpdate(content=chapter_text, metadata=metadata, title=None, order_index=None),
            user_id,
        )

        self.memory_service.update_neo4j(
            facts,
            project_id=str(document.project_id),
            chapter_index=chapter_index,
        )
        self.memory_service.store_style_memory(
            str(document.project_id),
            str(document.id),
            chapter_text,
            summary,
        )

        rag_updated = False
        rag_error = None
        try:
            await self.rag_service.aupdate_document(
                document.project_id,
                document,
            )
            rag_updated = True
        except Exception as exc:
            rag_error = str(exc)
            logger.exception("RAG update failed for chapter %s", document.id)

        result = {
            "document_id": str(document.id),
            "status": "approved",
            "summary": summary,
            "rag_updated": rag_updated,
            "rag_update_error": rag_error,
        }
        self._log_duration("approve_chapter", start)
        return result

    async def _persist_draft(
        self,
        state: NovelState,
        result: Dict[str, Any],
        chapter_text: str,
        word_count: int,
    ) -> Optional[str]:
        document_service = DocumentService(self.db)
        chapter_id = state.get("chapter_id")
        user_id = state.get("user_id")
        if user_id is None:
            raise ValueError("user_id is required to persist a draft")
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
        validation = result.get("continuity_validation")
        plan_payload = result.get("current_plan")
        plan_data = plan_payload if isinstance(plan_payload, dict) else {}
        required_points = self._normalize_str_list(plan_data.get("required_plot_points"))
        plot_validation = {}
        if isinstance(validation, dict):
            plot_validation = validation.get("plot_point_validation") or {}
        metadata["plot_point_coverage"] = {
            "required": required_points,
            "covered": plot_validation.get("covered_points") or [],
            "missing": plot_validation.get("missing_points") or [],
            "forbidden_violations": plot_validation.get("forbidden_violations") or [],
            "coverage_score": float(plot_validation.get("coverage_score") or 0.0),
            "explanation": plot_validation.get("explanation") or "",
        }
        if validation:
            metadata["continuity_validation_history"] = [validation]

        if chapter_id:
            if validation:
                existing = await document_service.get_by_id(chapter_id, user_id)
                if existing and isinstance(existing.document_metadata, dict):
                    history = existing.document_metadata.get("continuity_validation_history") or []
                    if isinstance(history, list):
                        metadata["continuity_validation_history"] = [*history, validation]
            updated = await document_service.update(
                chapter_id,
                DocumentUpdate(
                    content=chapter_text,
                    metadata=metadata,
                    title=chapter_title,
                    order_index=None,
                ),
                user_id,
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
        document = await document_service.create(document_data, user_id=user_id)
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
        # Approximate safety margin: tokens per word, capped by write/chat max.
        token_target = int(word_target * settings.WRITE_TOKENS_PER_WORD)
        token_target = max(120, token_target)
        token_cap = min(settings.WRITE_MAX_TOKENS, settings.CHAT_MAX_TOKENS)
        return min(token_cap, token_target)

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
        condensed = await self._timed_chat(
            "write_chapter.condense",
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
            condensed_retry = await self._timed_chat(
                "write_chapter.condense_retry",
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

    def _normalize_str_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _normalize_plan(self, plan: Dict[str, Any], chapter_index: int, target_words: Optional[int]) -> ChapterPlan:
        return {
            "chapter_number": int(plan.get("chapter_number") or chapter_index),
            "scene_beats": plan.get("scene_beats") or ["Mise en place", "Montee en tension", "Cliffhanger"],
            "target_emotion": plan.get("target_emotion") or "tension",
            "required_plot_points": self._normalize_str_list(plan.get("required_plot_points")),
            "optional_subplots": self._normalize_str_list(plan.get("optional_subplots")),
            "arc_constraints": self._normalize_str_list(plan.get("arc_constraints")),
            "forbidden_actions": self._normalize_str_list(plan.get("forbidden_actions")),
            "success_criteria": str(plan.get("success_criteria") or ""),
            "cliffhanger_type": plan.get("cliffhanger_type") or "revelation",
            "estimated_word_count": int(
                plan.get("estimated_word_count")
                or target_words
                or int((settings.CHAPTER_MIN_WORDS + settings.CHAPTER_MAX_WORDS) / 2)
            ),
        }

    def _find_plan_entry(self, plan: Dict[str, Any], chapter_index: Optional[int]) -> Optional[Dict[str, Any]]:
        if not isinstance(plan, dict) or not chapter_index:
            return None
        chapters = plan.get("chapters")
        if not isinstance(chapters, list):
            return None
        for item in chapters:
            if not isinstance(item, dict):
                continue
            try:
                if int(item.get("index", 0)) == int(chapter_index):
                    return item
            except (TypeError, ValueError):
                continue
        return None

    def _resolve_plot_constraints(self, state: NovelState, plan_entry: Dict[str, Any]) -> Dict[str, Any]:
        required_plot_points = self._normalize_str_list(plan_entry.get("required_plot_points"))
        optional_subplots = self._normalize_str_list(plan_entry.get("optional_subplots"))
        arc_constraints = self._normalize_str_list(plan_entry.get("arc_constraints"))
        forbidden_actions = self._normalize_str_list(plan_entry.get("forbidden_actions"))
        success_criteria = str(plan_entry.get("success_criteria") or "")

        chapter_index = state.get("chapter_index") or plan_entry.get("chapter_number")
        project_plan = state.get("project_context", {}).get("project", {}).get("plan")
        plan_from_project = self._find_plan_entry(project_plan, chapter_index)
        if plan_from_project:
            if not required_plot_points:
                required_plot_points = self._normalize_str_list(plan_from_project.get("required_plot_points"))
            if not optional_subplots:
                optional_subplots = self._normalize_str_list(plan_from_project.get("optional_subplots"))
            if not arc_constraints:
                arc_constraints = self._normalize_str_list(plan_from_project.get("arc_constraints"))
            if not forbidden_actions:
                forbidden_actions = self._normalize_str_list(plan_from_project.get("forbidden_actions"))
            if not success_criteria:
                success_criteria = str(plan_from_project.get("success_criteria") or "")

        return {
            "required_plot_points": required_plot_points,
            "optional_subplots": optional_subplots,
            "arc_constraints": arc_constraints,
            "forbidden_actions": forbidden_actions,
            "success_criteria": success_criteria,
        }

    def _extract_reasoning(self, message: Dict[str, Any]) -> str:
        reasoning = message.get("reasoning_content") or ""
        content = message.get("content") or ""
        if not reasoning and "<think>" in content:
            start = content.find("<think>") + len("<think>")
            end = content.find("</think>")
            reasoning = content[start:end].strip() if end > start else ""
        return reasoning.strip()

    def _normalize_validation_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        severe_raw = payload.get("severe_issues")
        severe: List[Any] = severe_raw if isinstance(severe_raw, list) else []
        minor_raw = payload.get("minor_issues")
        minor: List[Any] = minor_raw if isinstance(minor_raw, list) else []
        return {
            "severe_issues": [item for item in severe if isinstance(item, dict)],
            "minor_issues": [item for item in minor if isinstance(item, dict)],
            "coherence_score": float(payload.get("coherence_score") or 0.0),
            "blocking": bool(payload.get("blocking")),
        }

    def _extract_plot_validation(self, payload: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
        plot_payload = payload.get("plot_point_validation")
        has_plot_fields = False
        if isinstance(plot_payload, dict):
            has_plot_fields = True
            covered = plot_payload.get("covered_points")
            missing = plot_payload.get("missing_points")
            forbidden = plot_payload.get("forbidden_violations")
            coverage_score = plot_payload.get("coverage_score")
            explanation = plot_payload.get("explanation")
        else:
            covered = payload.get("covered_points")
            missing = payload.get("missing_points")
            forbidden = payload.get("forbidden_violations")
            coverage_score = payload.get("coverage_score")
            explanation = payload.get("explanation")
            has_plot_fields = any(
                key in payload
                for key in (
                    "covered_points",
                    "missing_points",
                    "forbidden_violations",
                    "coverage_score",
                    "explanation",
                )
            )
        return (
            {
                "covered_points": self._normalize_str_list(covered),
                "missing_points": self._normalize_str_list(missing),
                "forbidden_violations": self._normalize_str_list(forbidden),
                "coverage_score": float(coverage_score or 0.0),
                "explanation": str(explanation or ""),
            },
            has_plot_fields,
        )

    def _build_plot_issues(self, plot_validation: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        for point in plot_validation.get("missing_points") or []:
            issues.append(
                {
                    "type": "missing_plot_point",
                    "detail": f"Point d'intrigue requis manquant: {point}",
                    "severity": "blocking",
                }
            )
        for violation in plot_validation.get("forbidden_violations") or []:
            issues.append(
                {
                    "type": "forbidden_action",
                    "detail": f"Action interdite presente: {violation}",
                    "severity": "blocking",
                }
            )
        return issues

    async def _validate_plot_points(
        self,
        chapter_text: str,
        required_points: List[str],
        forbidden_actions: List[str],
    ) -> Dict[str, Any]:
        """Validate plot point coverage and forbidden actions."""
        if not chapter_text:
            return {
                "covered_points": [],
                "missing_points": [],
                "forbidden_violations": [],
                "coverage_score": 0.0,
                "explanation": "No chapter text to validate.",
                "issues": [],
            }
        if not required_points and not forbidden_actions:
            return {
                "covered_points": [],
                "missing_points": [],
                "forbidden_violations": [],
                "coverage_score": 0.0,
                "explanation": "",
                "issues": [],
            }

        required_block = "\n".join([f"- {point}" for point in required_points]) or "aucun"
        forbidden_block = "\n".join([f"- {action}" for action in forbidden_actions]) or "aucun"
        prompt = (
            "Analyse ce chapitre pour verifier la couverture des points d'intrigue.\n\n"
            f"CHAPITRE:\n{chapter_text}\n\n"
            "POINTS D'INTRIGUE REQUIS (DOIVENT tous etre presents):\n"
            f"{required_block}\n\n"
            "ACTIONS INTERDITES (NE DOIVENT PAS apparaitre):\n"
            f"{forbidden_block}\n\n"
            "Retourne un JSON strict avec:\n"
            "{\n"
            '  "covered_points": ["..."],\n'
            '  "missing_points": ["..."],\n'
            '  "forbidden_violations": ["..."],\n'
            '  "coverage_score": 0-10,\n'
            '  "explanation": "..." \n'
            "}\n"
        )
        response = await self._timed_chat(
            "validate_continuity.plot_points",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        payload = self._safe_json(response)
        covered_points = self._normalize_str_list(payload.get("covered_points"))
        missing_points = self._normalize_str_list(payload.get("missing_points"))
        forbidden_violations = self._normalize_str_list(payload.get("forbidden_violations"))
        coverage_score = float(payload.get("coverage_score") or 0.0)
        explanation = str(payload.get("explanation") or "")

        issues: List[Dict[str, Any]] = []
        for point in missing_points:
            issues.append(
                {
                    "type": "missing_plot_point",
                    "detail": f"Point d'intrigue requis manquant: {point}",
                    "severity": "blocking",
                }
            )
        for violation in forbidden_violations:
            issues.append(
                {
                    "type": "forbidden_action",
                    "detail": f"Action interdite presente: {violation}",
                    "severity": "blocking",
                }
            )

        return {
            "covered_points": covered_points,
            "missing_points": missing_points,
            "forbidden_violations": forbidden_violations,
            "coverage_score": coverage_score,
            "explanation": explanation,
            "issues": issues,
        }

    async def _validate_with_graph(self, state: NovelState) -> Dict[str, Any]:
        """Validate continuity against Neo4j graph signals."""
        memory_service = getattr(self, "memory_service", None)
        if not memory_service or not getattr(memory_service, "neo4j_driver", None):
            return {"graph_issues": []}
        chapter_text = state.get("chapter_text", "")
        if not chapter_text:
            return {"graph_issues": []}
        project_id = state.get("project_id")
        project_id_value = str(project_id) if project_id else None
        chapter_index = state.get("chapter_index")
        project_context = state.get("project_context") or {}

        mentioned_chars = self._extract_mentioned_characters(chapter_text, project_context)
        issues: List[Dict[str, Any]] = []
        for char_name in mentioned_chars:
            try:
                contradictions = memory_service.detect_character_contradictions(
                    char_name,
                    project_id=project_id_value,
                )
            except Exception:
                logger.exception("Graph validation failed for character %s", char_name)
                continue
            for contradiction in contradictions:
                issues.append(
                    {
                        "type": "graph_contradiction",
                        "severity": "critical",
                        "detail": (
                            f"{char_name}: {contradiction.get('contradiction')} entre "
                            f"ch.{contradiction.get('from_chapter')} et ch.{contradiction.get('to_chapter')}"
                        ),
                        "source": "neo4j_graph",
                    }
                )

        try:
            orphaned = memory_service.find_orphaned_plot_threads(
                chapter_index,
                project_id=project_id_value,
            )
        except Exception:
            logger.exception("Graph validation failed for plot thread checks")
            orphaned = []
        for thread in orphaned:
            issues.append(
                {
                    "type": "abandoned_plot_thread",
                    "severity": "medium",
                    "detail": (
                        f"Fil narratif '{thread.get('event')}' non resolu depuis "
                        f"ch.{thread.get('last_mentioned')}"
                    ),
                    "source": "neo4j_graph",
                }
            )
        return {"graph_issues": issues}

    def _extract_mentioned_characters(
        self, chapter_text: str, project_context: Dict[str, Any]
    ) -> List[str]:
        """Extract character names mentioned in the chapter text."""
        if not chapter_text:
            return []
        text_lower = chapter_text.casefold()
        characters = project_context.get("characters")
        if not isinstance(characters, list):
            characters = []
        mentioned = []
        for item in characters:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name or not isinstance(name, str):
                continue
            if name.casefold() in text_lower:
                mentioned.append(name)
        return list(dict.fromkeys(mentioned))

    def _get_resolved_contradictions(self, state: NovelState) -> set[str]:
        metadata = state.get("project_context", {}).get("project", {}).get("metadata", {})
        if not isinstance(metadata, dict):
            return set()
        contradictions = metadata.get("tracked_contradictions")
        if not isinstance(contradictions, list):
            return set()
        resolved = set()
        for item in contradictions:
            if not isinstance(item, dict):
                continue
            status = item.get("status")
            if status not in ("resolved", "intentional"):
                continue
            description = item.get("description")
            if description:
                resolved.add(description)
        return resolved

    def _normalize_contradiction_severity(self, value: Any) -> str:
        severity = str(value or "").lower()
        if severity in ("critical", "blocking"):
            return "critical"
        if severity in ("high", "medium", "low"):
            return severity
        return "medium"

    def _should_track_issue(self, issue: Dict[str, Any]) -> bool:
        issue_type = str(issue.get("type") or "")
        if issue_type in {"missing_plot_point", "forbidden_action"}:
            return False
        detail = issue.get("detail")
        return bool(detail)

    async def _track_contradiction(
        self,
        project_id: UUID,
        issue: Dict[str, Any],
        chapter_index: Optional[int],
    ) -> None:
        """Track a contradiction in project metadata if not already resolved."""
        if not getattr(self, "db", None):
            return
        project = await self.db.get(Project, project_id)
        if not project:
            return
        metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
        contradictions = metadata.setdefault("tracked_contradictions", [])
        if not isinstance(contradictions, list):
            contradictions = []
            metadata["tracked_contradictions"] = contradictions

        description = issue.get("detail") or ""
        if not description:
            return
        existing = next(
            (
                item
                for item in contradictions
                if isinstance(item, dict)
                and item.get("description") == description
                and item.get("status") not in ("resolved", "intentional")
            ),
            None,
        )
        chapter_value = None
        if isinstance(chapter_index, int):
            chapter_value = chapter_index
        if existing:
            chapters = existing.get("affected_chapters")
            if isinstance(chapters, list) and chapter_value is not None:
                if chapter_value not in chapters:
                    chapters.append(chapter_value)
                    existing["affected_chapters"] = chapters
                    project.project_metadata = metadata
                    await self.db.commit()
            return

        contradictions.append(
            {
                "id": str(uuid4()),
                "type": issue.get("type") or "unknown",
                "severity": self._normalize_contradiction_severity(issue.get("severity")),
                "description": description,
                "detected_in_chapter": chapter_value,
                "detected_at": datetime.utcnow().isoformat(),
                "status": "pending",
                "resolution": None,
                "affected_chapters": [chapter_value] if chapter_value is not None else [],
                "auto_detected": True,
            }
        )
        project.project_metadata = metadata
        await self.db.commit()

    def _build_continuity_alerts(self, validation: Dict[str, Any]) -> List[str]:
        alerts: List[str] = []
        issues: List[Any] = []
        severe = validation.get("severe_issues")
        minor = validation.get("minor_issues")
        if isinstance(severe, list):
            issues.extend(severe)
        if isinstance(minor, list):
            issues.extend(minor)
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            detail = issue.get("detail") or ""
            issue_type = issue.get("type")
            if issue_type and detail:
                alerts.append(f"{issue_type}: {detail}")
            elif detail:
                alerts.append(detail)
        return alerts

    def _hash_metadata(self, metadata: Dict[str, Any]) -> str:
        try:
            payload = json.dumps(metadata, sort_keys=True, separators=(",", ":"), default=str)
        except TypeError:
            payload = json.dumps(str(metadata))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _get_cached_memory_context(self, metadata: Dict[str, Any]) -> str:
        if not isinstance(metadata, dict):
            return self.memory_service.build_context_block({})
        if not metadata:
            return self.memory_service.build_context_block({})
        cache_key = self._hash_metadata(metadata)
        cached = _MEMORY_CONTEXT_CACHE.get(cache_key)
        if cached is not None:
            _MEMORY_CONTEXT_CACHE.move_to_end(cache_key)
            return cached
        context = self.memory_service.build_context_block(metadata)
        if context:
            _MEMORY_CONTEXT_CACHE[cache_key] = context
            if len(_MEMORY_CONTEXT_CACHE) > _MEMORY_CONTEXT_CACHE_MAX:
                _MEMORY_CONTEXT_CACHE.popitem(last=False)
        return context

    def _truncate_text(self, text: str, max_chars: int) -> str:
        if not text or max_chars <= 0:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip()

    def _build_beats_outline(self, beats: List[str]) -> str:
        if not beats:
            return ""
        lines = ["Outline scenes:"]
        for idx, beat in enumerate(beats, start=1):
            lines.append(f"{idx}. {beat}")
        return "\n".join(lines)

    def _build_previous_beats_block(self, beats: List[str], max_chars: int) -> str:
        if not beats or max_chars <= 0:
            return ""
        combined = "\n\n".join([beat for beat in beats if beat]).strip()
        if len(combined) > max_chars:
            combined = combined[-max_chars:]
        return combined.strip()

    def _build_beat_prompt(
        self,
        base_prompt: str,
        beat_outline: str,
        beat: str,
        beat_index: int,
        total_beats: int,
        beat_target: int,
        current_words: int,
        remaining_target: int,
        max_words: int,
        continuation_hint: str,
        previous_block: str = "",
    ) -> str:
        prompt = f"{base_prompt}\n"
        if beat_outline:
            prompt += f"{beat_outline}\n"
        if previous_block:
            prompt += f"Scenes precedentes (resume court):\n{previous_block}\n"
        prompt += (
            f"Scene {beat_index + 1}/{total_beats}: {beat}\n"
            f"Nombre de mots actuel: {current_words}\n"
            f"Objectif global restant: environ {remaining_target} mots.\n"
            f"Ecris environ {beat_target} mots pour cette scene.\n"
            f"Ne depasse pas {max_words} mots au total. Termine par une phrase complete.\n"
            f"{continuation_hint}\n"
            "Retourne uniquement la suite du chapitre."
        )
        return prompt

    def _plan_entry_has_details(self, plan_entry: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(plan_entry, dict):
            return False
        beats = plan_entry.get("scene_beats")
        if isinstance(beats, list) and beats:
            return True
        return False

    def _should_use_reasoning(self, chapter_index: int, instruction: Optional[str]) -> bool:
        if not settings.PLAN_REASONING_ENABLED:
            return False
        if chapter_index <= settings.PLAN_REASONING_FIRST_CHAPTERS:
            return True
        interval = settings.PLAN_REASONING_INTERVAL
        if interval and chapter_index % interval == 0:
            return True
        if instruction:
            keywords = [
                item.strip().lower()
                for item in settings.PLAN_REASONING_KEYWORDS.split(",")
                if item.strip()
            ]
            text = instruction.lower()
            if any(keyword in text for keyword in keywords):
                return True
        return False

    def _build_bible_context_block(self, bible: Dict[str, Any]) -> str:
        if not isinstance(bible, dict) or not bible:
            return ""
        parts: List[str] = []

        rules_raw = bible.get("world_rules")
        rules = rules_raw if isinstance(rules_raw, list) else []
        critical_rules = [
            rule for rule in rules
            if isinstance(rule, dict) and rule.get("importance") in ("critical", "high")
        ]
        if critical_rules:
            parts.append("REGLES DU MONDE (NE PAS VIOLER):")
            for rule in critical_rules[:5]:
                rule_text = rule.get("rule") or ""
                if not rule_text:
                    continue
                parts.append(f"- {rule_text}")
                exceptions = rule.get("exceptions")
                if isinstance(exceptions, list) and exceptions:
                    parts.append(f"  Exceptions: {', '.join([str(item) for item in exceptions])}")

        timeline_raw = bible.get("timeline")
        timeline = timeline_raw if isinstance(timeline_raw, list) else []
        if timeline:
            parts.append("\nTIMELINE ETABLIE:")
            sorted_events = sorted(
                [event for event in timeline if isinstance(event, dict)],
                key=lambda event: event.get("chapter_index") or 0,
            )
            for event in sorted_events[-10:]:
                event_text = event.get("event") or ""
                chapter_index = event.get("chapter_index")
                if not event_text or chapter_index is None:
                    continue
                ref = event.get("time_reference") or ""
                suffix = f" ({ref})" if ref else ""
                parts.append(f"- Ch.{chapter_index}: {event_text}{suffix}")

        facts_raw = bible.get("established_facts")
        facts = facts_raw if isinstance(facts_raw, list) else []
        cannot_contradict = [
            fact for fact in facts
            if isinstance(fact, dict) and fact.get("cannot_contradict")
        ]
        if cannot_contradict:
            parts.append("\nFAITS ETABLIS (INCONTESTABLES):")
            for fact in cannot_contradict[:10]:
                fact_text = fact.get("fact") or ""
                chapter_index = fact.get("established_chapter")
                if not fact_text:
                    continue
                suffix = f" (ch.{chapter_index})" if chapter_index else ""
                parts.append(f"- {fact_text}{suffix}")

        return "\n".join(parts).strip()
