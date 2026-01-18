"""Projects endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID, uuid4
from datetime import datetime
import io
import re
import unicodedata
import zipfile

from app.db.session import get_db
from app.models.user import User
from app.models.document import Document, DocumentType
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectList,
    ProjectDeleteRequest,
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
    PlanGenerateRequest,
    PlanUpdateRequest,
    PlanResponse,
)
from app.services.project_service import ProjectService
from app.services.novella_service import NovellaForgeService
from app.core.security import get_current_active_user

router = APIRouter()


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
    return PlanResponse(
        project_id=project_id,
        status=str(entry.get("status") or "draft"),
        plan=plan_data,
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

    return ProjectList(projects=projects, total=total)


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
