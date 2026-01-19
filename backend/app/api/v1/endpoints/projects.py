"""Projects endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Dict
from uuid import UUID, uuid4
from datetime import datetime
import json
import io
import re
import unicodedata
import zipfile
import logging

from app.db.session import get_db
from app.models.user import User
from app.models.document import Document, DocumentType
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectList,
    ProjectDeleteRequest,
    ContradictionResolution,
    ContradictionIntentionalRequest,
)
from app.schemas.instruction import (
    InstructionCreate,
    InstructionUpdate,
    InstructionResponse,
    InstructionList,
)
from app.schemas.novella import (
    ConceptGenerateRequest,
    ConceptPayload,
    ConceptResponse,
    ConceptProposalRequest,
    ConceptProposalResponse,
    SynopsisGenerateRequest,
    SynopsisUpdateRequest,
    SynopsisResponse,
    PlanPayload,
    PlanGenerateRequest,
    PlanUpdateRequest,
    PlanResponse,
)
from app.schemas.story_bible import (
    StoryBible,
    StoryBibleDraftValidationRequest,
    StoryBibleGlossary,
    StoryBibleValidationResponse,
    StoryBibleViolation,
    TimelineEvent,
    WorldRule,
)
from app.services.project_service import ProjectService
from app.services.novella_service import NovellaForgeService
from app.services.rag_service import RagService
from app.services.memory_service import MemoryService
from app.services.llm_client import DeepSeekClient
from app.core.security import get_current_active_user
from app.tasks.coherence_maintenance import (
    reconcile_project_memory,
    rebuild_project_rag,
    cleanup_old_drafts,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def normalize_project_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    return " ".join(normalized.split()).casefold()


def _load_instructions(project) -> list[dict]:
    metadata = project.project_metadata or {}
    instructions = metadata.get("instructions") if isinstance(metadata, dict) else None
    return instructions if isinstance(instructions, list) else []


def _save_instructions(project, instructions: list[dict]) -> None:
    metadata = project.project_metadata or {}
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["instructions"] = instructions
    project.project_metadata = metadata


def _serialize_instruction(raw: dict) -> InstructionResponse:
    created_at_value = raw.get("created_at")
    try:
        created_at = datetime.fromisoformat(created_at_value) if created_at_value else datetime.utcnow()
    except ValueError:
        created_at = datetime.utcnow()
    return InstructionResponse(
        id=UUID(str(raw.get("id"))),
        title=str(raw.get("title")),
        detail=str(raw.get("detail")),
        created_at=created_at,
    )


def _safe_filename(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", (value or "").strip())
    cleaned = re.sub(r"\s+", "-", cleaned).strip("-")
    if not cleaned:
        return fallback
    return cleaned[:120]


def _serialize_concept(project_id: UUID, entry: dict) -> ConceptResponse:
    updated_at_value = entry.get("updated_at")
    try:
        updated_at = datetime.fromisoformat(updated_at_value) if updated_at_value else datetime.utcnow()
    except ValueError:
        updated_at = datetime.utcnow()
    concept_data = entry.get("data") if isinstance(entry.get("data"), dict) else None
    if not concept_data and any(
        key in entry for key in ("title", "premise", "tone", "tropes", "emotional_orientation")
    ):
        concept_data = entry
    if concept_data is None:
        concept_data = {}
    return ConceptResponse(
        project_id=project_id,
        status=str(entry.get("status") or "draft"),
        concept=ConceptPayload(
            title=str(concept_data.get("title") or ""),
            premise=str(concept_data.get("premise") or ""),
            tone=str(concept_data.get("tone") or ""),
            tropes=list(concept_data.get("tropes") or []),
            emotional_orientation=str(concept_data.get("emotional_orientation") or ""),
        ),
        updated_at=updated_at,
    )


def _serialize_plan(project_id: UUID, entry: dict) -> PlanResponse:
    updated_at_value = entry.get("updated_at")
    try:
        updated_at = datetime.fromisoformat(updated_at_value) if updated_at_value else datetime.utcnow()
    except ValueError:
        updated_at = datetime.utcnow()
    plan_data = entry.get("data") if isinstance(entry.get("data"), dict) else None
    if not plan_data and any(key in entry for key in ("chapters", "arcs", "global_summary")):
        plan_data = {
            "global_summary": entry.get("global_summary") or "",
            "arcs": entry.get("arcs") or [],
            "chapters": entry.get("chapters") or [],
        }
    if plan_data is None:
        plan_data = {}
    if isinstance(plan_data, dict):
        plan_payload_data = {
            "global_summary": plan_data.get("global_summary") or "",
            "arcs": plan_data.get("arcs") or [],
            "chapters": plan_data.get("chapters") or [],
        }
    else:
        plan_payload_data = {"global_summary": "", "arcs": [], "chapters": []}
    return PlanResponse(
        project_id=project_id,
        status=str(entry.get("status") or "draft"),
        plan=PlanPayload.model_validate(plan_payload_data),
        updated_at=updated_at,
    )


def _serialize_synopsis(project_id: UUID, entry: dict) -> SynopsisResponse:
    updated_at_value = entry.get("updated_at")
    try:
        updated_at = datetime.fromisoformat(updated_at_value) if updated_at_value else datetime.utcnow()
    except ValueError:
        updated_at = datetime.utcnow()
    synopsis_text = entry.get("text") if isinstance(entry, dict) else None
    if not synopsis_text and isinstance(entry, dict):
        synopsis_text = entry.get("synopsis")
    if synopsis_text is None:
        synopsis_text = ""
    return SynopsisResponse(
        project_id=project_id,
        status=str(entry.get("status") or "draft"),
        synopsis=str(synopsis_text or ""),
        updated_at=updated_at,
    )


def _ensure_story_bible(metadata: Dict[str, Any]) -> Dict[str, Any]:
    bible_raw = metadata.get("story_bible")
    bible: Dict[str, Any] = bible_raw if isinstance(bible_raw, dict) else {}
    if not isinstance(bible.get("world_rules"), list):
        bible["world_rules"] = []
    if not isinstance(bible.get("timeline"), list):
        bible["timeline"] = []
    glossary = bible.get("glossary")
    if not isinstance(glossary, dict):
        glossary = {}
    if not isinstance(glossary.get("terms"), list):
        glossary["terms"] = []
    if not isinstance(glossary.get("places"), list):
        glossary["places"] = []
    if not isinstance(glossary.get("factions"), list):
        glossary["factions"] = []
    bible["glossary"] = glossary
    if not isinstance(bible.get("core_themes"), list):
        bible["core_themes"] = []
    if not isinstance(bible.get("established_facts"), list):
        bible["established_facts"] = []
    metadata["story_bible"] = bible
    return bible


def _build_bible_validation_block(bible: StoryBible) -> str:
    parts: list[str] = []
    if bible.world_rules:
        parts.append("REGLES DU MONDE:")
        for rule in bible.world_rules[:10]:
            parts.append(f"- {rule.rule}")
            if rule.exceptions:
                parts.append(f"  Exceptions: {', '.join(rule.exceptions)}")
    if bible.timeline:
        parts.append("\nTIMELINE:")
        for event in bible.timeline[-10:]:
            ref = f" ({event.time_reference})" if event.time_reference else ""
            parts.append(f"- Ch.{event.chapter_index}: {event.event}{ref}")
    if bible.established_facts:
        parts.append("\nFAITS ETABLIS:")
        for fact in bible.established_facts[:10]:
            parts.append(f"- {fact.fact} (ch.{fact.established_chapter})")
    return "\n".join(parts).strip()


def _parse_bible_validation_response(raw_text: str) -> StoryBibleValidationResponse:
    try:
        payload = json.loads(raw_text or "{}")
    except json.JSONDecodeError:
        logger.warning("Story bible validation returned invalid JSON.")
        return StoryBibleValidationResponse(
            violations=[],
            blocking=False,
            summary="Validation impossible: reponse non valide.",
        )

    raw_violations = payload.get("violations") or []
    violations: list[StoryBibleViolation] = []
    if isinstance(raw_violations, list):
        for entry in raw_violations:
            if not isinstance(entry, dict):
                continue
            violations.append(
                StoryBibleViolation(
                    type=str(entry.get("type") or "rule_violation"),
                    detail=str(entry.get("detail") or ""),
                    severity=str(entry.get("severity") or "warning"),
                    rule_id=entry.get("rule_id"),
                )
            )
    return StoryBibleValidationResponse(
        violations=violations,
        blocking=bool(payload.get("blocking")),
        summary=str(payload.get("summary") or ""),
    )


@router.get("/", response_model=ProjectList)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all projects for the current user.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (max 100)
    """
    project_service = ProjectService(db)
    projects, total = await project_service.get_all_by_user(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

    payload_projects = [
        ProjectResponse.model_validate(project) for project in projects
    ]
    return ProjectList(projects=payload_projects, total=total)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new project.

    - **genre**: Main genre (required)
    - **title**: Optional title (auto-generated if empty)
    - **description**: Optional description
    - **target_word_count**: Target word count
    - **structure_template**: Optional narrative template
    """
    project_service = ProjectService(db)
    project = await project_service.create(project_data, current_user.id)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific project by ID.

    Returns 404 if project not found or user doesn't have access.
    """
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return project


@router.get("/{project_id}/coherence-health")
async def get_coherence_health(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    continuity_raw = metadata.get("continuity")
    continuity: Dict[str, Any] = continuity_raw if isinstance(continuity_raw, dict) else {}
    last_memory_update = continuity.get("updated_at")

    rag_service = RagService()
    rag_document_count = None
    rag_error = None
    try:
        rag_document_count = await rag_service.acount_project_vectors(project_id)
    except Exception as exc:
        rag_error = str(exc)
        logger.exception("RAG health check failed for project %s", project_id)

    return {
        "project_id": str(project_id),
        "last_memory_update": last_memory_update,
        "rag_document_count": rag_document_count,
        "rag_error": rag_error,
    }


@router.get("/{project_id}/coherence-graph")
async def get_coherence_graph(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return coherence graph nodes and edges for visualization."""
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    memory_service = MemoryService()
    graph_data = memory_service.export_graph_for_visualization(str(project_id))
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    total_characters = len([node for node in nodes if node.get("type") == "Character"])
    total_locations = len([node for node in nodes if node.get("type") == "Location"])

    return {
        "project_id": str(project_id),
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_characters": total_characters,
            "total_locations": total_locations,
            "total_relations": len(edges),
        },
    }


@router.get("/{project_id}/contradictions")
async def list_contradictions(
    project_id: UUID,
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List tracked contradictions with optional status filter."""
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    contradictions = metadata.get("tracked_contradictions")
    if not isinstance(contradictions, list):
        contradictions = []

    if status:
        contradictions = [item for item in contradictions if item.get("status") == status]

    pending = len([item for item in contradictions if item.get("status") == "pending"])
    resolved = len([item for item in contradictions if item.get("status") == "resolved"])
    intentional = len([item for item in contradictions if item.get("status") == "intentional"])

    return {
        "contradictions": contradictions,
        "summary": {
            "total": len(contradictions),
            "pending": pending,
            "resolved": resolved,
            "intentional": intentional,
        },
    }


@router.post("/{project_id}/contradictions/{contradiction_id}/resolve")
async def resolve_contradiction(
    project_id: UUID,
    contradiction_id: str,
    resolution: ContradictionResolution,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a contradiction as resolved and optionally update the story bible."""
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    contradictions = metadata.get("tracked_contradictions")
    if not isinstance(contradictions, list):
        contradictions = []

    contradiction = next((item for item in contradictions if item.get("id") == contradiction_id), None)
    if not contradiction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contradiction not found")

    contradiction["status"] = "resolved"
    contradiction["resolution"] = {
        "type": resolution.type,
        "action_taken": resolution.action_taken,
        "resolved_by": str(current_user.id),
        "resolved_at": datetime.utcnow().isoformat(),
        "bible_update": resolution.bible_update,
    }

    if resolution.bible_update:
        bible = _ensure_story_bible(metadata)
        established = bible.setdefault("established_facts", [])
        detected = contradiction.get("detected_in_chapter")
        chapter_value = detected if isinstance(detected, int) and detected > 0 else 1
        established.append(
            {
                "fact": resolution.bible_update,
                "established_chapter": chapter_value,
                "cannot_contradict": True,
                "resolution_of_contradiction": contradiction_id,
            }
        )

    metadata["tracked_contradictions"] = contradictions
    project.project_metadata = metadata
    await db.commit()

    return {"status": "resolved", "contradiction": contradiction}


@router.post("/{project_id}/contradictions/{contradiction_id}/mark-intentional")
async def mark_contradiction_intentional(
    project_id: UUID,
    contradiction_id: str,
    payload: ContradictionIntentionalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a contradiction as intentional."""
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    contradictions = metadata.get("tracked_contradictions")
    if not isinstance(contradictions, list):
        contradictions = []

    contradiction = next((item for item in contradictions if item.get("id") == contradiction_id), None)
    if not contradiction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contradiction not found")

    contradiction["status"] = "intentional"
    contradiction["resolution"] = {
        "type": "intentional",
        "action_taken": payload.explanation,
        "resolved_by": str(current_user.id),
        "resolved_at": datetime.utcnow().isoformat(),
        "bible_update": payload.bible_update,
    }

    if payload.bible_update:
        bible = _ensure_story_bible(metadata)
        established = bible.setdefault("established_facts", [])
        detected = contradiction.get("detected_in_chapter")
        chapter_value = detected if isinstance(detected, int) and detected > 0 else 1
        established.append(
            {
                "fact": payload.bible_update,
                "established_chapter": chapter_value,
                "cannot_contradict": True,
                "resolution_of_contradiction": contradiction_id,
            }
        )

    metadata["tracked_contradictions"] = contradictions
    project.project_metadata = metadata
    await db.commit()

    return {"status": "intentional", "contradiction": contradiction}


@router.post("/{project_id}/maintenance/reconcile")
async def trigger_memory_reconciliation(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Schedule a memory reconciliation task for the project."""
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    reconcile_project_memory.delay(str(project_id))
    return {"status": "scheduled", "task": "reconcile_memory"}


@router.post("/{project_id}/maintenance/rebuild-rag")
async def trigger_rag_rebuild(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Schedule a full RAG rebuild for the project."""
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    rebuild_project_rag.delay(str(project_id))
    return {"status": "scheduled", "task": "rebuild_rag"}


@router.post("/{project_id}/maintenance/cleanup-drafts")
async def trigger_draft_cleanup(
    project_id: UUID,
    days_threshold: int = Query(default=30, ge=1, le=3650),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Schedule cleanup of old draft documents for the project."""
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    cleanup_old_drafts.delay(str(project_id), days_threshold)
    return {"status": "scheduled", "task": "cleanup_old_drafts", "days_threshold": days_threshold}

@router.get("/{project_id}/download")
async def download_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download all chapters as a zip archive with one markdown per chapter.
    """
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    documents_result = await db.execute(
        select(Document).where(Document.project_id == project_id).order_by(Document.order_index.asc())
    )
    documents = documents_result.scalars().all()
    chapters = [doc for doc in documents if doc.document_type == DocumentType.CHAPTER]

    used_names: set[str] = set()
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for fallback_index, doc in enumerate(chapters, start=1):
            metadata = doc.document_metadata if isinstance(doc.document_metadata, dict) else {}
            raw_index = metadata.get("chapter_index")
            if raw_index is None:
                chapter_index = (doc.order_index + 1) if doc.order_index is not None else fallback_index
            else:
                try:
                    chapter_index = int(raw_index)
                except (TypeError, ValueError):
                    chapter_index = (doc.order_index + 1) if doc.order_index is not None else fallback_index

            title = doc.title or f"Chapter {chapter_index}"
            safe_title = _safe_filename(title, f"chapter-{chapter_index}")
            base_name = f"{chapter_index:03d}-{safe_title}"
            filename = f"{base_name}.md"
            if filename in used_names:
                suffix = 2
                while True:
                    candidate = f"{base_name}-{suffix}.md"
                    if candidate not in used_names:
                        filename = candidate
                        break
                    suffix += 1
            used_names.add(filename)

            content_parts = []
            if doc.title:
                content_parts.append(f"# {doc.title}")
            if doc.content:
                content_parts.append(doc.content)
            payload = "\n\n".join(content_parts)
            archive.writestr(filename, payload)

    archive_buffer.seek(0)
    filename = f"{_safe_filename(project.title or 'project', 'project')}.zip"

    return Response(
        content=archive_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a project.

    All fields are optional. Only provided fields will be updated.
    """
    project_service = ProjectService(db)
    project = await project_service.update(project_id, project_data, current_user.id)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a project.

    This will also delete all associated documents and characters.
    """
    project_service = ProjectService(db)
    deleted = await project_service.delete(project_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return None


@router.post("/{project_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_with_confirmation(
    project_id: UUID,
    payload: ProjectDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a project with title confirmation.

    The provided title must exactly match the project title.
    """
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if normalize_project_title(project.title) != normalize_project_title(payload.confirm_title):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project title confirmation does not match",
        )

    await project_service.delete(project_id, current_user.id)
    return None


@router.get("/{project_id}/instructions", response_model=InstructionList)
async def list_instructions(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    instructions = _load_instructions(project)
    serialized = []
    for item in instructions:
        if not isinstance(item, dict):
            continue
        try:
            serialized.append(_serialize_instruction(item))
        except Exception:
            continue

    return InstructionList(instructions=serialized, total=len(serialized))


@router.post("/{project_id}/instructions", response_model=InstructionResponse, status_code=status.HTTP_201_CREATED)
async def create_instruction(
    project_id: UUID,
    payload: InstructionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    instruction_id = uuid4()
    created_at = datetime.utcnow().isoformat()
    instruction = {
        "id": str(instruction_id),
        "title": payload.title,
        "detail": payload.detail,
        "created_at": created_at,
    }
    instructions = _load_instructions(project)
    instructions.append(instruction)
    _save_instructions(project, instructions)
    await db.commit()
    await db.refresh(project)

    return _serialize_instruction(instruction)


@router.put("/{project_id}/instructions/{instruction_id}", response_model=InstructionResponse)
async def update_instruction(
    project_id: UUID,
    instruction_id: UUID,
    payload: InstructionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    instructions = _load_instructions(project)
    updated = None
    for item in instructions:
        if not isinstance(item, dict):
            continue
        if str(item.get("id")) != str(instruction_id):
            continue
        if payload.title is not None:
            item["title"] = payload.title
        if payload.detail is not None:
            item["detail"] = payload.detail
        updated = item
        break

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instruction not found")

    _save_instructions(project, instructions)
    await db.commit()
    await db.refresh(project)
    return _serialize_instruction(updated)


@router.delete("/{project_id}/instructions/{instruction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instruction(
    project_id: UUID,
    instruction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    instructions = _load_instructions(project)
    filtered = [
        item
        for item in instructions
        if isinstance(item, dict) and str(item.get("id")) != str(instruction_id)
    ]

    if len(filtered) == len(instructions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instruction not found")

    _save_instructions(project, filtered)
    await db.commit()
    await db.refresh(project)
    return None


@router.get("/{project_id}/story-bible", response_model=StoryBible)
async def get_story_bible(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    bible = _ensure_story_bible(metadata)
    return StoryBible.model_validate(bible)


@router.put("/{project_id}/story-bible/world-rules")
async def update_world_rules(
    project_id: UUID,
    rules: list[WorldRule],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    bible = _ensure_story_bible(metadata)
    bible["world_rules"] = [rule.model_dump() for rule in rules]
    project.project_metadata = metadata
    await db.commit()

    return {"status": "updated", "rules_count": len(rules)}


@router.put("/{project_id}/story-bible/timeline")
async def update_timeline(
    project_id: UUID,
    events: list[TimelineEvent],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    bible = _ensure_story_bible(metadata)
    bible["timeline"] = [event.model_dump() for event in events]
    project.project_metadata = metadata
    await db.commit()

    return {"status": "updated", "events_count": len(events)}


@router.put("/{project_id}/story-bible/glossary")
async def update_glossary(
    project_id: UUID,
    glossary: StoryBibleGlossary,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    bible = _ensure_story_bible(metadata)
    bible["glossary"] = glossary.model_dump()
    project.project_metadata = metadata
    await db.commit()

    return {
        "status": "updated",
        "term_count": len(glossary.terms),
        "place_count": len(glossary.places),
        "faction_count": len(glossary.factions),
    }


@router.post("/{project_id}/story-bible/validate-draft", response_model=StoryBibleValidationResponse)
async def validate_draft_against_bible(
    project_id: UUID,
    payload: StoryBibleDraftValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    bible = StoryBible.model_validate(_ensure_story_bible(metadata))
    bible_block = _build_bible_validation_block(bible)
    if not bible_block:
        logger.info("Story bible is empty for project %s", project_id)

    prompt = (
        "Tu es un analyste de coherence narrative. Reponds en francais uniquement. "
        "Compare le draft avec la story bible. Retourne un JSON strict avec:\n"
        "{"
        '"violations": [{"type": "rule_violation", "detail": "...", "severity": "blocking|warning", "rule_id": null}],'
        '"blocking": true|false, "summary": "..."'
        "}\n"
        "Story bible:\n"
        f"{bible_block}\n\n"
        "Draft:\n"
        f"{payload.draft_text}"
    )
    llm_client = DeepSeekClient()
    response = await llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=600,
        response_format={"type": "json_object"},
    )
    return _parse_bible_validation_response(response)


@router.get("/{project_id}/concept", response_model=ConceptResponse)
async def get_concept(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    metadata = project.project_metadata or {}
    concept_entry = metadata.get("concept") if isinstance(metadata, dict) else None
    if not concept_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    return _serialize_concept(project.id, concept_entry)


@router.post("/concept/proposal", response_model=ConceptProposalResponse)
async def generate_concept_proposal(
    payload: ConceptProposalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = NovellaForgeService(db)
    concept = await service.generate_concept_preview(payload.genre.value, payload.notes, user_id=current_user.id)
    return ConceptProposalResponse(
        status="draft",
        concept=ConceptPayload(**concept),
        updated_at=datetime.utcnow(),
    )


@router.post("/{project_id}/concept/generate", response_model=ConceptResponse)
async def generate_concept(
    project_id: UUID,
    payload: ConceptGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = NovellaForgeService(db)
    entry = await service.generate_concept(project_id, current_user.id, force=payload.force)
    return _serialize_concept(project_id, entry)


@router.put("/{project_id}/concept", response_model=ConceptResponse)
async def accept_concept(
    project_id: UUID,
    payload: ConceptPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = NovellaForgeService(db)
    entry = await service.accept_concept(project_id, current_user.id, payload.model_dump())
    return _serialize_concept(project_id, entry)


@router.get("/{project_id}/plan", response_model=PlanResponse)
async def get_plan(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    metadata = project.project_metadata or {}
    plan_entry = metadata.get("plan") if isinstance(metadata, dict) else None
    if not plan_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return _serialize_plan(project.id, plan_entry)


@router.post("/{project_id}/plan/generate", response_model=PlanResponse)
async def generate_plan(
    project_id: UUID,
    payload: PlanGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = NovellaForgeService(db)
    entry = await service.generate_plan(
        project_id,
        current_user.id,
        chapter_count=payload.chapter_count,
        arc_count=payload.arc_count,
        regenerate=payload.regenerate,
    )
    return _serialize_plan(project_id, entry)


@router.put("/{project_id}/plan/accept", response_model=PlanResponse)
async def accept_plan(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    plan_entry = metadata.get("plan")
    if not isinstance(plan_entry, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if "data" not in plan_entry and any(key in plan_entry for key in ("chapters", "arcs", "global_summary")):
        plan_entry = {
            "data": plan_entry,
            "status": "accepted",
            "updated_at": datetime.utcnow().isoformat(),
        }
    else:
        plan_entry["status"] = "accepted"
        plan_entry["updated_at"] = datetime.utcnow().isoformat()
    metadata["plan"] = plan_entry
    project.project_metadata = metadata
    await db.commit()
    await db.refresh(project)
    return _serialize_plan(project.id, plan_entry)


@router.put("/{project_id}/plan", response_model=PlanResponse)
async def update_plan(
    project_id: UUID,
    payload: PlanUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    plan_entry = metadata.get("plan") if isinstance(metadata, dict) else None
    status_value = "draft"
    if isinstance(plan_entry, dict) and plan_entry.get("status"):
        status_value = str(plan_entry.get("status"))
    metadata["plan"] = {
        "data": payload.plan.model_dump(),
        "status": status_value,
        "updated_at": datetime.utcnow().isoformat(),
    }
    project.project_metadata = metadata
    await db.commit()
    await db.refresh(project)
    return _serialize_plan(project.id, metadata["plan"])


@router.get("/{project_id}/synopsis", response_model=SynopsisResponse)
async def get_synopsis(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    metadata = project.project_metadata or {}
    synopsis_entry = metadata.get("synopsis") if isinstance(metadata, dict) else None
    if synopsis_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Synopsis not found")
    if isinstance(synopsis_entry, dict):
        payload = synopsis_entry
    else:
        payload = {"text": synopsis_entry}
    return _serialize_synopsis(project.id, payload)


@router.post("/{project_id}/synopsis/generate", response_model=SynopsisResponse)
async def generate_synopsis(
    project_id: UUID,
    payload: SynopsisGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = NovellaForgeService(db)
    entry = await service.generate_synopsis(project_id, current_user.id, notes=payload.notes)
    return _serialize_synopsis(project_id, entry)


@router.put("/{project_id}/synopsis", response_model=SynopsisResponse)
async def update_synopsis(
    project_id: UUID,
    payload: SynopsisUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    synopsis_entry = metadata.get("synopsis") if isinstance(metadata, dict) else None
    status_value = "draft"
    if isinstance(synopsis_entry, dict) and synopsis_entry.get("status"):
        status_value = str(synopsis_entry.get("status"))
    metadata["synopsis"] = {
        "text": payload.synopsis,
        "status": status_value,
        "updated_at": datetime.utcnow().isoformat(),
    }
    project.project_metadata = metadata
    await db.commit()
    await db.refresh(project)
    return _serialize_synopsis(project.id, metadata["synopsis"])


@router.put("/{project_id}/synopsis/accept", response_model=SynopsisResponse)
async def accept_synopsis(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    synopsis_entry = metadata.get("synopsis")
    if not synopsis_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Synopsis not found")
    if not isinstance(synopsis_entry, dict):
        synopsis_entry = {"text": str(synopsis_entry)}
    synopsis_entry["status"] = "accepted"
    synopsis_entry["updated_at"] = datetime.utcnow().isoformat()
    metadata["synopsis"] = synopsis_entry
    project.project_metadata = metadata
    await db.commit()
    await db.refresh(project)
    return _serialize_synopsis(project.id, synopsis_entry)
