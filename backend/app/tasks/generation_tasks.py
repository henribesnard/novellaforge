"""
Celery tasks for distributed chapter generation.

These tasks allow parallel beat generation across multiple workers,
significantly reducing chapter generation time.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from celery import group, chord
from celery.exceptions import SoftTimeLimitExceeded

from app.core.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code in sync Celery tasks."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(
    bind=True,
    name="generate_beat",
    max_retries=2,
    soft_time_limit=120,
    time_limit=150,
    queue="beats_high",
)
def generate_beat_task(
    self,
    beat_index: int,
    beat_outline: str,
    base_prompt: str,
    beat_target: int,
    current_words: int,
    remaining_target: int,
    max_words: int,
    total_beats: int,
    continuation_hint: str = "",
    previous_block: str = "",
) -> Dict[str, Any]:
    """
    Generate a single beat of a chapter.

    This task is designed to run on dedicated workers for parallel execution.
    Each beat is generated independently and assembled later.
    """
    try:
        from app.services.llm_client import DeepSeekClient

        llm_client = DeepSeekClient()

        # Build beat prompt
        prompt = f"{base_prompt}\n"
        if previous_block:
            prompt += f"Scenes precedentes (resume court):\n{previous_block}\n"
        prompt += (
            f"Scene {beat_index + 1}/{total_beats}: {beat_outline}\n"
            f"Nombre de mots actuel: {current_words}\n"
            f"Objectif global restant: environ {remaining_target} mots.\n"
            f"Ecris environ {beat_target} mots pour cette scene.\n"
            f"Ne depasse pas {max_words} mots au total. Termine par une phrase complete.\n"
            f"{continuation_hint}\n"
            "Retourne uniquement la suite du chapitre."
        )

        async def _generate():
            return await llm_client.chat(
                messages=[
                    {"role": "system", "content": "Tu es un auteur de fiction feuilleton."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=_max_tokens_for_words(beat_target),
            )

        content = _run_async(_generate())
        content = (content or "").strip()
        word_count = len(content.split())

        logger.info(f"Beat {beat_index + 1} generated: {word_count} words")

        return {
            "beat_index": beat_index,
            "content": content,
            "word_count": word_count,
            "success": True,
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"Beat {beat_index + 1} generation timed out")
        return {
            "beat_index": beat_index,
            "content": "",
            "word_count": 0,
            "success": False,
            "error": "Timeout",
        }
    except Exception as e:
        logger.exception(f"Beat {beat_index + 1} generation failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=5 * (self.request.retries + 1))
        return {
            "beat_index": beat_index,
            "content": "",
            "word_count": 0,
            "success": False,
            "error": str(e),
        }


@celery_app.task(
    name="assemble_beats",
    queue="beats_high",
)
def assemble_beats_task(beat_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assemble completed beats into a full chapter.

    This is the callback task in a chord that runs after all beats complete.
    """
    # Sort by beat index
    sorted_results = sorted(beat_results, key=lambda x: x.get("beat_index", 0))

    # Check for failures
    failed_beats = [r for r in sorted_results if not r.get("success", False)]
    if failed_beats:
        logger.warning(f"{len(failed_beats)} beats failed")

    # Assemble content
    contents = [r.get("content", "") for r in sorted_results if r.get("content")]
    full_content = "\n\n".join(contents)
    total_words = len(full_content.split())

    return {
        "chapter_text": full_content,
        "word_count": total_words,
        "beat_count": len(sorted_results),
        "failed_beats": len(failed_beats),
        "beat_texts": [r.get("content", "") for r in sorted_results],
    }


def _max_tokens_for_words(word_target: int) -> int:
    """Calculate max tokens based on word target."""
    token_target = int(word_target * settings.WRITE_TOKENS_PER_WORD)
    token_target = max(120, token_target)
    token_cap = min(settings.WRITE_MAX_TOKENS, settings.CHAT_MAX_TOKENS)
    return min(token_cap, token_target)


async def generate_beats_distributed(
    beats: List[str],
    base_prompt: str,
    target_word_count: int,
    min_beat_words: int = 120,
) -> Dict[str, Any]:
    """
    Generate all beats in parallel using Celery workers.

    Args:
        beats: List of beat outlines
        base_prompt: The base prompt with context
        target_word_count: Total target word count
        min_beat_words: Minimum words per beat

    Returns:
        Dict with chapter_text, word_count, beat_texts
    """
    if not beats:
        return {"chapter_text": "", "word_count": 0, "beat_texts": []}

    per_beat_target = max(min_beat_words, int(target_word_count / len(beats) * 0.85))

    # Create task signatures for each beat
    beat_tasks = []
    for idx, beat in enumerate(beats):
        current_words = int(per_beat_target * idx)
        remaining_target = max(target_word_count - current_words, 0)
        beat_target = max(min_beat_words, min(per_beat_target, remaining_target or per_beat_target))

        beat_tasks.append(
            generate_beat_task.s(
                beat_index=idx,
                beat_outline=beat,
                base_prompt=base_prompt,
                beat_target=beat_target,
                current_words=current_words,
                remaining_target=remaining_target,
                max_words=target_word_count + 200,
                total_beats=len(beats),
                continuation_hint="Assume les scenes precedentes deja ecrites. Commence directement cette scene.",
            )
        )

    # Use chord to run beats in parallel and then assemble
    workflow = chord(beat_tasks)(assemble_beats_task.s())

    # Wait for result with timeout
    try:
        result = workflow.get(timeout=180)  # 3 minute timeout
        return result
    except Exception as e:
        logger.exception(f"Distributed beat generation failed: {e}")
        # Fallback: return empty
        return {"chapter_text": "", "word_count": 0, "beat_texts": [], "error": str(e)}


@celery_app.task(
    bind=True,
    name="generate_chapter_async",
    soft_time_limit=600,
    time_limit=660,
    queue="generation_medium",
)
def generate_chapter_async_task(
    self,
    project_id: str,
    user_id: str,
    chapter_index: Optional[int] = None,
    chapter_id: Optional[str] = None,
    instruction: Optional[str] = None,
    target_word_count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate a full chapter asynchronously.

    This is useful for batch generation or when the user doesn't need
    real-time feedback.
    """
    try:
        from app.db.session import get_sync_session
        from app.services.writing_pipeline import WritingPipeline

        async def _generate():
            async with get_sync_session() as db:
                pipeline = WritingPipeline(db)
                state = {
                    "project_id": UUID(project_id),
                    "user_id": UUID(user_id),
                    "chapter_index": chapter_index,
                    "chapter_id": UUID(chapter_id) if chapter_id else None,
                    "chapter_instruction": instruction,
                    "target_word_count": target_word_count,
                    "use_rag": True,
                    "reindex_documents": False,
                    "create_document": True,
                    "auto_approve": False,
                }
                return await pipeline.generate_chapter(state)

        result = _run_async(_generate())

        return {
            "success": True,
            "chapter_title": result.get("chapter_title", ""),
            "chapter_text": result.get("chapter_text", ""),
            "document_id": result.get("document_id"),
            "word_count": result.get("word_count", 0),
            "critique": result.get("critique"),
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"Chapter generation timed out for project {project_id}")
        return {"success": False, "error": "Generation timed out"}
    except Exception as e:
        logger.exception(f"Chapter generation failed for project {project_id}: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(
    name="pregenerate_plans_async",
    soft_time_limit=300,
    time_limit=360,
    queue="generation_medium",
)
def pregenerate_plans_async_task(
    project_id: str,
    user_id: str,
    count: int = 5,
) -> Dict[str, Any]:
    """
    Pregenerate plans for upcoming chapters.

    This runs in the background to have plans ready when the user
    requests chapter generation.
    """
    try:
        from app.db.session import get_sync_session
        from app.services.writing_pipeline import WritingPipeline
        from app.models.project import Project
        from sqlalchemy import select

        async def _pregenerate():
            async with get_sync_session() as db:
                # Get project
                result = await db.execute(
                    select(Project).where(Project.id == UUID(project_id))
                )
                project = result.scalar_one_or_none()
                if not project:
                    return {"success": False, "error": "Project not found", "plans_generated": 0}

                pipeline = WritingPipeline(db)
                metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}

                # Find current chapter
                plan_entry = metadata.get("plan", {})
                plan_data = plan_entry.get("data") if isinstance(plan_entry, dict) else plan_entry
                if not isinstance(plan_data, dict):
                    plan_data = {}

                chapters = plan_data.get("chapters", [])
                approved_count = sum(1 for ch in chapters if isinstance(ch, dict) and ch.get("status") == "approved")
                current_chapter = approved_count + 1

                pregenerated_plans = metadata.get("pregenerated_plans", {})
                if not isinstance(pregenerated_plans, dict):
                    pregenerated_plans = {}

                plans_generated = 0
                for i in range(count):
                    chapter_num = current_chapter + i

                    if str(chapter_num) in pregenerated_plans:
                        continue

                    context = await pipeline.context_service.build_project_context(
                        project_id=UUID(project_id),
                        user_id=UUID(user_id),
                    )

                    state = {
                        "project_id": UUID(project_id),
                        "user_id": UUID(user_id),
                        "chapter_index": chapter_num,
                        "project_context": context,
                    }

                    plan_result = await pipeline.plan_chapter(state)
                    plan = plan_result.get("current_plan")

                    if plan:
                        pregenerated_plans[str(chapter_num)] = plan
                        plans_generated += 1

                metadata["pregenerated_plans"] = pregenerated_plans
                project.project_metadata = metadata
                await db.commit()

                return {"success": True, "plans_generated": plans_generated}

        return _run_async(_pregenerate())

    except Exception as e:
        logger.exception(f"Plan pregeneration failed for project {project_id}: {e}")
        return {"success": False, "error": str(e), "plans_generated": 0}
