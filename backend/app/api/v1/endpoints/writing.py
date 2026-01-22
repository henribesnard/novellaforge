"""Writing pipeline endpoints."""
from uuid import UUID
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.models.document import Document
from app.core.security import get_current_active_user, get_user_from_token
from app.schemas.writing import (
    IndexProjectRequest,
    IndexProjectResponse,
    ChapterGenerationRequest,
    ChapterGenerationResponse,
    ChapterCritique,
    ChapterApprovalRequest,
    ChapterApprovalResponse,
    PregeneratePlansRequest,
    PregeneratePlansResponse,
)
from app.services.rag_service import RagService
from app.services.writing_pipeline import WritingPipeline
from app.services.llm_client import DeepSeekClient

logger = logging.getLogger(__name__)

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


@router.websocket("/ws/generate/{project_id}")
async def websocket_generate_chapter(
    websocket: WebSocket,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for streaming chapter generation.

    Client should send a JSON message with:
    {
        "token": "jwt_token",
        "chapter_index": 1,  # optional
        "chapter_id": "uuid",  # optional
        "instruction": "...",  # optional
        "target_word_count": 1500  # optional
    }

    Server sends:
    - {"type": "status", "message": "..."} for status updates
    - {"type": "chunk", "content": "..."} for text chunks
    - {"type": "beat_complete", "beat_index": 0, "content": "..."} when a beat finishes
    - {"type": "complete", "document_id": "...", "word_count": 123} when done
    - {"type": "error", "message": "..."} on error
    """
    await websocket.accept()

    try:
        # Wait for initial message with auth token and params
        init_message = await websocket.receive_json()
        token = init_message.get("token")
        if not token:
            await websocket.send_json({"type": "error", "message": "Token required"})
            await websocket.close()
            return

        # Authenticate user
        try:
            user = await get_user_from_token(token, db)
            if not user:
                await websocket.send_json({"type": "error", "message": "Invalid token"})
                await websocket.close()
                return
        except Exception:
            await websocket.send_json({"type": "error", "message": "Authentication failed"})
            await websocket.close()
            return

        # Verify project access
        result = await db.execute(
            select(Project).where(Project.id == project_id, Project.owner_id == user.id)
        )
        project = result.scalar_one_or_none()
        if not project:
            await websocket.send_json({"type": "error", "message": "Project not found"})
            await websocket.close()
            return

        # Check plan status
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

        if not plan_data or plan_status != "accepted":
            await websocket.send_json({"type": "error", "message": "Plan not accepted"})
            await websocket.close()
            return

        await websocket.send_json({"type": "status", "message": "Starting generation..."})

        # Create pipeline and generate with streaming
        pipeline = WritingPipeline(db)

        # Generate chapter (non-streaming for now, but with status updates)
        await websocket.send_json({"type": "status", "message": "Collecting context..."})

        chapter_id = init_message.get("chapter_id")
        if chapter_id:
            chapter_id = UUID(chapter_id)

        state = {
            "project_id": project_id,
            "user_id": user.id,
            "chapter_id": chapter_id,
            "chapter_index": init_message.get("chapter_index"),
            "chapter_instruction": init_message.get("instruction"),
            "target_word_count": init_message.get("target_word_count"),
            "use_rag": True,
            "reindex_documents": False,
            "create_document": True,
            "auto_approve": False,
        }

        result = await pipeline.generate_chapter(state)

        # Send the completed chapter
        await websocket.send_json({
            "type": "complete",
            "chapter_title": result.get("chapter_title", ""),
            "content": result.get("chapter_text", ""),
            "document_id": result.get("document_id"),
            "word_count": result.get("word_count", 0),
            "critique": result.get("critique"),
            "continuity_alerts": result.get("continuity_alerts", []),
        })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for project {project_id}")
    except Exception as e:
        logger.exception(f"WebSocket error for project {project_id}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


async def _pregenerate_plans_task(
    project_id: UUID,
    user_id: UUID,
    count: int,
    db: AsyncSession,
):
    """Background task to pregenerate chapter plans."""
    try:
        pipeline = WritingPipeline(db)

        # Get project and find current chapter
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return

        metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
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

        for i in range(count):
            chapter_num = current_chapter + i

            # Skip if already pregenerated
            if str(chapter_num) in pregenerated_plans:
                continue

            # Build context and generate plan
            context = await pipeline.context_service.build_project_context(
                project_id=project_id,
                user_id=user_id,
            )

            state = {
                "project_id": project_id,
                "user_id": user_id,
                "chapter_index": chapter_num,
                "project_context": context,
            }

            # Generate plan using the plan_chapter node
            plan_result = await pipeline.plan_chapter(state)
            plan = plan_result.get("current_plan")

            if plan:
                pregenerated_plans[str(chapter_num)] = plan

        # Save pregenerated plans to metadata
        metadata["pregenerated_plans"] = pregenerated_plans
        project.project_metadata = metadata
        await db.commit()

        logger.info(f"Pregenerated {count} plans for project {project_id}")

    except Exception as e:
        logger.exception(f"Error pregenerating plans for project {project_id}: {e}")


@router.post("/pregenerate-plans", response_model=PregeneratePlansResponse)
async def pregenerate_plans(
    request: PregeneratePlansRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Pregenerate plans for the next N chapters in background.
    This speeds up chapter generation by having plans ready.
    """
    await _verify_project_access(db, request.project_id, current_user.id)

    background_tasks.add_task(
        _pregenerate_plans_task,
        project_id=request.project_id,
        user_id=current_user.id,
        count=request.count,
        db=db,
    )

    return PregeneratePlansResponse(
        success=True,
        status="started",
        chapters_to_plan=request.count,
    )
