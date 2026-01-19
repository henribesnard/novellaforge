"""Writing pipeline endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.models.document import Document
from app.core.security import get_current_active_user
from app.schemas.writing import (
    IndexProjectRequest,
    IndexProjectResponse,
    ChapterGenerationRequest,
    ChapterGenerationResponse,
    ChapterCritique,
    ChapterApprovalRequest,
    ChapterApprovalResponse,
)
from app.services.rag_service import RagService
from app.services.writing_pipeline import WritingPipeline

router = APIRouter()


async def _verify_project_access(db: AsyncSession, project_id: UUID, user_id: UUID) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied",
        )
    return project


@router.post("/index", response_model=IndexProjectResponse)
async def index_project_documents(
    request: IndexProjectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Index all documents for a project into Qdrant."""
    await _verify_project_access(db, request.project_id, current_user.id)

    documents_result = await db.execute(
        select(Document).where(Document.project_id == request.project_id)
    )
    documents = list(documents_result.scalars().all())

    rag_service = RagService()
    chunks_indexed = await rag_service.aindex_documents(
        project_id=request.project_id,
        documents=documents,
        clear_existing=request.clear_existing,
    )

    return IndexProjectResponse(success=True, chunks_indexed=chunks_indexed)


@router.post("/generate-chapter", response_model=ChapterGenerationResponse)
async def generate_chapter(
    request: ChapterGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Generate a chapter with autonomous context collection."""
    project = await _verify_project_access(db, request.project_id, current_user.id)
    metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
    plan_entry = metadata.get("plan")
    plan_data = None
    plan_status = "draft"
    if isinstance(plan_entry, dict):
        if isinstance(plan_entry.get("data"), dict):
            plan_data = plan_entry.get("data")
            plan_status = str(plan_entry.get("status") or "draft")
        elif any(key in plan_entry for key in ("chapters", "arcs", "global_summary")):
            plan_data = plan_entry
            plan_status = str(plan_entry.get("status") or "draft")
    if not plan_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan non genere")
    if plan_status != "accepted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan non accepte")

    if request.chapter_id:
        doc_result = await db.execute(
            select(Document).where(
                Document.id == request.chapter_id,
                Document.project_id == request.project_id,
            )
        )
        if not doc_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

    instruction = request.instruction
    if request.rewrite_focus and not instruction:
        focus_map = {
            "emotion": "Renforce l'emotion dans ce chapitre.",
            "tension": "Renforce la tension dans ce chapitre.",
            "action": "Renforce l'action dans ce chapitre.",
            "custom": "Renforce cet aspect dans ce chapitre.",
        }
        instruction = focus_map.get(request.rewrite_focus) or "Renforce cet aspect dans ce chapitre."

    pipeline = WritingPipeline(db)
    result = await pipeline.generate_chapter(
        {
            "project_id": request.project_id,
            "user_id": current_user.id,
            "chapter_id": request.chapter_id,
            "chapter_index": request.chapter_index,
            "chapter_instruction": instruction,
            "target_word_count": request.target_word_count,
            "use_rag": request.use_rag,
            "reindex_documents": request.reindex_documents,
            "create_document": request.create_document,
            "auto_approve": request.auto_approve,
        }
    )

    critique_payload = result.get("critique") or {}
    critique = None
    if critique_payload:
        critique = ChapterCritique(
            score=float(critique_payload.get("score") or 0.0),
            issues=critique_payload.get("issues") or [],
            suggestions=critique_payload.get("suggestions") or [],
            cliffhanger_ok=bool(critique_payload.get("cliffhanger_ok")),
            pacing_ok=bool(critique_payload.get("pacing_ok")),
        )

    return ChapterGenerationResponse(
        success=True,
        chapter_title=result.get("chapter_title", ""),
        plan=result.get("plan"),
        content=result.get("chapter_text", ""),
        word_count=result.get("word_count", 0),
        document_id=result.get("document_id"),
        critique=critique,
        needs_review=not request.auto_approve,
        continuity_alerts=result.get("continuity_alerts", []),
        continuity_validation=result.get("continuity_validation"),
        retrieved_chunks=result.get("retrieved_chunks", []),
    )


@router.post("/approve-chapter", response_model=ChapterApprovalResponse)
async def approve_chapter(
    request: ChapterApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Approve a draft chapter and update continuity memory."""
    pipeline = WritingPipeline(db)
    result = await pipeline.approve_chapter(str(request.document_id), current_user.id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

    return ChapterApprovalResponse(
        success=True,
        document_id=result.get("document_id", str(request.document_id)),
        status=result.get("status", "approved"),
        summary=result.get("summary"),
        rag_updated=bool(result.get("rag_updated")),
        rag_update_error=result.get("rag_update_error"),
    )
