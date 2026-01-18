"""Documents endpoints"""
import math
import re
from datetime import datetime
from uuid import uuid4
from httpx import ReadTimeout
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any, Optional
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.models.document import Document, DocumentType
from app.models.project import Project
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentList,
    ElementCreateRequest,
    ElementGenerateRequest,
    DocumentVersionCreate,
    DocumentVersionSummary,
    DocumentVersionResponse,
    DocumentVersionList,
    DocumentCommentCreate,
    DocumentComment,
    DocumentCommentList,
)
from app.services.document_service import DocumentService
from app.services.context_service import ProjectContextService
from app.services.llm_client import DeepSeekClient
from app.core.config import settings
from app.core.security import get_current_active_user

router = APIRouter()

ELEMENT_TYPE_DEFS: Dict[str, Dict[str, Any]] = {
    "partie": {"label": "Partie", "level": 1, "document_type": DocumentType.OUTLINE},
    "chapitre": {"label": "Chapitre", "level": 2, "document_type": DocumentType.CHAPTER},
    "sous-chapitre": {"label": "Sous-chapitre", "level": 3, "document_type": DocumentType.OUTLINE},
    "section": {"label": "Section", "level": 4, "document_type": DocumentType.OUTLINE},
}


def _normalize_element_type(raw_type: str) -> str:
    value = (raw_type or "").strip().lower()
    if value not in ELEMENT_TYPE_DEFS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported element type",
        )
    return value


def _infer_element_type(document: Document) -> Optional[str]:
    metadata = document.document_metadata or {}
    element_type = metadata.get("element_type")
    if isinstance(element_type, str) and element_type in ELEMENT_TYPE_DEFS:
        return element_type

    if document.document_type == DocumentType.CHAPTER:
        return "chapitre"

    return None


def _element_level(element_type: Optional[str]) -> int:
    if not element_type:
        return 0
    return ELEMENT_TYPE_DEFS.get(element_type, {}).get("level", 0)


def _count_words(text: str) -> int:
    return len(text.split())


def _parse_version(value: Optional[str]) -> tuple[int, int]:
    if not value:
        return (1, 0)
    match = re.match(r"^v(?P<major>\d+)(?:\.(?P<minor>\d+))?$", value.strip())
    if not match:
        return (1, 0)
    major = int(match.group("major"))
    minor = int(match.group("minor") or 0)
    return (major, minor)


def _format_version(major: int, minor: int) -> str:
    if minor <= 0:
        return f"v{major}"
    return f"v{major}.{minor:02d}"


def _safe_filename(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", (value or "").strip())
    cleaned = re.sub(r"\s+", "-", cleaned).strip("-")
    if not cleaned:
        return fallback
    return cleaned[:120]


def _load_versions(metadata: Dict[str, Any]) -> list[dict]:
    versions = metadata.get("versions") if isinstance(metadata, dict) else None
    return versions if isinstance(versions, list) else []


def _load_comments(metadata: Dict[str, Any]) -> list[dict]:
    comments = metadata.get("comments") if isinstance(metadata, dict) else None
    return comments if isinstance(comments, list) else []


def _get_version_label(versions: list[dict], version_id: Optional[UUID]) -> Optional[str]:
    if not version_id:
        return None
    for entry in versions:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("id")) == str(version_id):
            return entry.get("version")
    return None


def _serialize_comment(entry: dict) -> Optional[dict]:
    if not isinstance(entry, dict):
        return None
    comment_id = entry.get("id")
    content = entry.get("content")
    created_at = entry.get("created_at")
    user_id = entry.get("user_id")
    if not comment_id or not content or not created_at or not user_id:
        return None
    try:
        created_at_dt = datetime.fromisoformat(str(created_at))
    except (TypeError, ValueError):
        created_at_dt = datetime.utcnow()
    applied_ids = entry.get("applied_version_ids")
    applied_list = applied_ids if isinstance(applied_ids, list) else None
    return {
        "id": UUID(str(comment_id)),
        "content": str(content),
        "created_at": created_at_dt,
        "user_id": UUID(str(user_id)),
        "version_id": UUID(str(entry.get("version_id"))) if entry.get("version_id") else None,
        "applied_version_ids": applied_list,
    }


async def _ensure_versions_for_document(
    *,
    document: Document,
    document_service: DocumentService,
    user_id: UUID,
) -> tuple[list[dict], Optional[str]]:
    metadata = document.document_metadata or {}
    versions = _load_versions(metadata)
    current_version = metadata.get("current_version") if isinstance(metadata, dict) else None
    if versions:
        return versions, current_version

    content = (document.content or "").strip()
    if not content:
        return versions, current_version

    base_version = "v1"
    versions.append(
        {
            "id": str(uuid4()),
            "version": base_version,
            "created_at": datetime.utcnow().isoformat(),
            "content": content,
            "word_count": _count_words(content),
            "min_word_count": metadata.get("min_word_count"),
            "max_word_count": metadata.get("max_word_count"),
            "summary": metadata.get("summary"),
            "instructions": None,
            "source_version_id": None,
            "source_version": None,
            "source_type": None,
            "source_comment_ids": None,
        }
    )

    metadata_updates = {
        **(metadata if isinstance(metadata, dict) else {}),
        "versions": versions,
        "current_version": base_version,
    }
    await document_service.update(
        document.id,
        DocumentUpdate(metadata=metadata_updates),
        user_id,
    )
    return versions, base_version


def _get_source_content(versions: list[dict], source_version_id: Optional[UUID]) -> tuple[str, Optional[str]]:
    if not source_version_id:
        return ("", None)
    for entry in versions:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("id")) == str(source_version_id):
            content = str(entry.get("content") or "")
            source_version = entry.get("version")
            if len(content) <= 3200:
                return (content, source_version)
            head = content[:1600]
            tail = content[-1600:]
            excerpt = f"{head}\n\n[...]\n\n{tail}"
            return (excerpt, source_version)
    return ("", None)


def _serialize_version(entry: dict, current_version: Optional[str], include_content: bool) -> Optional[dict]:
    if not isinstance(entry, dict):
        return None
    version_id = entry.get("id")
    version = entry.get("version")
    content = entry.get("content")
    if not version_id or not version or content is None:
        return None
    created_at = entry.get("created_at")
    try:
        created_at_dt = datetime.fromisoformat(created_at) if created_at else datetime.utcnow()
    except ValueError:
        created_at_dt = datetime.utcnow()

    word_count = entry.get("word_count")
    if not isinstance(word_count, int):
        word_count = _count_words(str(content))

    base = {
        "id": UUID(str(version_id)),
        "version": str(version),
        "created_at": created_at_dt,
        "word_count": word_count,
        "min_word_count": entry.get("min_word_count"),
        "max_word_count": entry.get("max_word_count"),
        "summary": entry.get("summary"),
        "instructions": entry.get("instructions"),
        "source_version_id": entry.get("source_version_id"),
        "source_version": entry.get("source_version"),
        "source_type": entry.get("source_type"),
        "source_comment_ids": entry.get("source_comment_ids"),
        "is_current": str(version) == str(current_version),
    }
    if include_content:
        base["content"] = str(content)
    return base


def _build_element_prompt(
    *,
    mode: str,
    element_label: str,
    element_type: str,
    title: str,
    summary: str,
    user_instructions: str,
    comment_block: str,
    context_block: str,
    min_words: Optional[int],
    max_words: Optional[int],
    current_words: int,
    chunk_target: Optional[int],
    continuation_hint: str,
    source_content: str,
) -> str:
    min_line = f"Minimum word count: {min_words}" if min_words else "Minimum word count: none"
    max_line = f"Maximum word count: {max_words}" if max_words else "Maximum word count: none"
    chunk_line = (
        f"Write the next part in about {chunk_target} words."
        if chunk_target
        else "Write the full content."
    )
    source_block = f"Existing content to correct:\n{source_content}\n" if source_content else ""
    comments = comment_block or "none"
    return (
        f"{mode.capitalize()} the {element_label.lower()} content for this project.\n"
        f"Title: {title}\n"
        f"Element type: {element_type}\n"
        f"User instructions: {user_instructions or 'none'}\n"
        f"User comments:\n{comments}\n"
        f"Summary: {summary or 'none'}\n"
        f"{min_line}\n"
        f"{max_line}\n"
        f"Current word count: {current_words}\n"
        f"{chunk_line}\n"
        f"{continuation_hint}\n\n"
        f"{source_block}"
        f"{context_block}\n"
        "Return only the next part of the content without repeating earlier text."
    )


async def _get_next_order_index(db: AsyncSession, project_id: UUID) -> int:
    result = await db.execute(
        select(func.max(Document.order_index)).where(Document.project_id == project_id)
    )
    max_index = result.scalar()
    return (max_index + 1) if max_index is not None else 0


async def _get_next_element_index(
    db: AsyncSession,
    project_id: UUID,
    element_type: str,
) -> int:
    result = await db.execute(
        select(Document).where(Document.project_id == project_id)
    )
    documents = result.scalars().all()
    current_max = 0
    seen = 0
    for doc in documents:
        doc_type = _infer_element_type(doc)
        if doc_type != element_type:
            continue
        seen += 1
        metadata = doc.document_metadata or {}
        try:
            index = int(metadata.get("element_index", 0))
        except (TypeError, ValueError):
            index = 0
        current_max = max(current_max, index)
    return max(current_max, seen) + 1


def _validate_parent_child(parent: Document, child_type: str) -> None:
    parent_type = _infer_element_type(parent)
    parent_level = _element_level(parent_type)
    child_level = _element_level(child_type)
    if parent_level and child_level <= parent_level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid element hierarchy",
        )


def _format_context_block(context: Dict[str, Any]) -> str:
    project = context.get("project", {})
    instructions = context.get("instructions", [])
    characters = context.get("characters", [])
    documents = context.get("documents", [])
    constraints = context.get("constraints", {})

    instruction_lines = [
        f"- {item.get('title')}: {item.get('detail')}"
        for item in instructions
        if item.get("title") and item.get("detail")
    ]
    character_lines = [
        f"- {char.get('name')}: {char.get('description') or ''}"
        for char in characters
        if char.get("name")
    ]
    document_lines = [
        f"- {doc.get('title')}"
        for doc in documents
        if doc.get("title")
    ]

    return (
        "PROJECT CONTEXT:\n"
        f"Title: {project.get('title')}\n"
        f"Genre: {project.get('genre')}\n"
        f"Description: {project.get('description')}\n"
        f"Structure: {project.get('structure_template')}\n"
        f"Instructions:\n{chr(10).join(instruction_lines) if instruction_lines else '- none'}\n"
        f"Characters:\n{chr(10).join(character_lines) if character_lines else '- none'}\n"
        f"Existing elements:\n{chr(10).join(document_lines) if document_lines else '- none'}\n"
        f"Constraints: {constraints}\n"
    )


@router.get("/", response_model=DocumentList)
async def list_documents(
    project_id: UUID = Query(..., description="Project ID to filter documents"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all documents for a project.

    - **project_id**: Project ID (required)
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (max 100)
    """
    document_service = DocumentService(db)
    documents, total = await document_service.get_all_by_project(
        project_id=project_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

    return DocumentList(documents=documents, total=total)


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new document.

    - **title**: Document title (required)
    - **content**: Document content
    - **document_type**: Type (chapter, scene, note, outline)
    - **project_id**: Project ID (required)
    - **order_index**: Order index for sorting
    """
    document_service = DocumentService(db)
    document = await document_service.create(document_data, current_user.id)
    return document


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific document by ID.

    Returns 404 if document not found or user doesn't have access.
    """
    document_service = DocumentService(db)
    document = await document_service.get_by_id(document_id, current_user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download a single document as a markdown file.
    """
    document_service = DocumentService(db)
    document = await document_service.get_by_id(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    project_title = None
    project_result = await db.execute(
        select(Project).where(
            Project.id == document.project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = project_result.scalar_one_or_none()
    if project and project.title:
        project_title = project.title

    metadata = document.document_metadata if isinstance(document.document_metadata, dict) else {}
    raw_index = metadata.get("chapter_index")
    try:
        chapter_index = int(raw_index)
    except (TypeError, ValueError):
        chapter_index = (document.order_index + 1) if document.order_index is not None else None

    if document.document_type == DocumentType.CHAPTER and project_title and chapter_index:
        safe_project = _safe_filename(project_title, "project")
        filename = f"{safe_project}_chapitre_{chapter_index}.md"
    else:
        title = document.title or "document"
        filename = f"{_safe_filename(title, 'document')}.md"
    content_parts = []
    if document.title:
        content_parts.append(f"# {document.title}")
    if document.content:
        content_parts.append(document.content)
    payload = "\n\n".join(content_parts)

    return Response(
        content=payload,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    document_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a document.

    All fields are optional. Only provided fields will be updated.
    Word count is automatically recalculated if content is updated.
    """
    document_service = DocumentService(db)
    document = await document_service.update(document_id, document_data, current_user.id)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a document.

    Project word count is automatically updated after deletion.
    """
    document_service = DocumentService(db)
    deleted = await document_service.delete(document_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return None


@router.post("/elements", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_element(
    payload: ElementCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a structured element (partie, chapitre, section, sous-chapitre).
    """
    element_type = _normalize_element_type(payload.element_type)
    document_service = DocumentService(db)

    parent = None
    if payload.parent_id:
        parent = await document_service.get_by_id(payload.parent_id, current_user.id)
        if not parent or parent.project_id != payload.project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent element not found",
            )
        _validate_parent_child(parent, element_type)

    element_index = await _get_next_element_index(db, payload.project_id, element_type)
    order_index = await _get_next_order_index(db, payload.project_id)
    element_label = ELEMENT_TYPE_DEFS[element_type]["label"]
    document_type = ELEMENT_TYPE_DEFS[element_type]["document_type"]

    metadata = {
        "element_type": element_type,
        "element_index": element_index,
        "parent_id": str(payload.parent_id) if payload.parent_id else None,
    }

    document = await document_service.create(
        DocumentCreate(
            title=f"{element_label} {element_index}",
            content="",
            document_type=document_type,
            project_id=payload.project_id,
            order_index=order_index,
            metadata=metadata,
        ),
        current_user.id,
    )

    return document


@router.post("/{document_id}/generate", response_model=DocumentResponse)
async def generate_element(
    document_id: UUID,
    payload: ElementGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate or rewrite an element based on project context and instructions.
    """
    document_service = DocumentService(db)
    document = await document_service.get_by_id(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    context_service = ProjectContextService(db)
    context = await context_service.build_project_context(
        project_id=document.project_id,
        user_id=current_user.id,
    )

    element_type = _infer_element_type(document) or "chapitre"
    element_label = ELEMENT_TYPE_DEFS.get(element_type, {}).get("label", "Element")
    mode = "rewrite" if (document.content or "").strip() else "write"
    user_instructions = (payload.instructions or "").strip()
    summary = (payload.summary or "").strip()
    context_block = _format_context_block(context)
    min_words = payload.min_word_count
    max_words = payload.max_word_count
    if min_words and max_words and max_words < min_words:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum word count must be greater than or equal to minimum word count",
        )
    metadata = document.document_metadata or {}
    versions = _load_versions(metadata)
    comments = _load_comments(metadata)
    source_content, source_version = _get_source_content(versions, payload.source_version_id)
    if payload.source_version_id and not source_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source version not found",
        )
    if source_content:
        mode = "rewrite"
    chunk_word_target = 1200
    max_iterations = 1
    if min_words:
        estimated = math.ceil(min_words / chunk_word_target)
        max_iterations = min(24, max(1, estimated + 2))

    comment_lines: list[str] = []
    comment_ids: list[str] = []
    selected_comment_ids = (
        {str(cid) for cid in payload.comment_ids} if payload.comment_ids is not None else None
    )
    if comments:
        version_lookup = {
            str(entry.get("id")): entry.get("version")
            for entry in versions
            if isinstance(entry, dict) and entry.get("id")
        }
        for entry in comments:
            if not isinstance(entry, dict):
                continue
            comment_id = entry.get("id")
            if selected_comment_ids is not None and str(comment_id) not in selected_comment_ids:
                continue
            content_text = str(entry.get("content") or "").strip()
            if not content_text:
                continue
            if comment_id:
                comment_ids.append(str(comment_id))
            version_id = entry.get("version_id")
            version_label = version_lookup.get(str(version_id)) if version_id else None
            suffix = f" (version {version_label})" if version_label else ""
            comment_lines.append(f"- {content_text}{suffix}")
    comment_block = "\n".join(comment_lines)
    if selected_comment_ids is not None and payload.comment_ids and not comment_lines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    llm_client = DeepSeekClient()
    content = ""
    current_words = 0
    for _ in range(max_iterations):
        if min_words and current_words >= min_words:
            break
        if max_words and current_words >= max_words:
            break
        remaining_min = min_words - current_words if min_words else None
        remaining_max = max_words - current_words if max_words else None
        remaining = remaining_min if remaining_min is not None else remaining_max
        if remaining_max is not None and remaining is not None:
            remaining = min(remaining, remaining_max)
        chunk_target = min(chunk_word_target, remaining) if remaining else None
        if content:
            excerpt = content[-1200:]
            continuation_hint = (
                "Last excerpt:\n"
                f"{excerpt}\n"
                "Continue from the excerpt without repeating earlier text."
            )
        else:
            continuation_hint = "Start the element from the beginning."
        prompt = _build_element_prompt(
            mode=mode,
            element_label=element_label,
            element_type=element_type,
            title=document.title,
            summary=summary,
            user_instructions=user_instructions,
            comment_block=comment_block,
            context_block=context_block,
            min_words=min_words,
            max_words=max_words,
            current_words=current_words,
            chunk_target=chunk_target,
            continuation_hint=continuation_hint,
            source_content=source_content,
        )
        try:
            part = await llm_client.chat(
                messages=[
                    {"role": "system", "content": "You are NovellaForge, a French literary writing assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=max(1, settings.CHAT_MAX_TOKENS),
            )
        except ReadTimeout as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Generation timed out. Try a smaller minimum word count or retry.",
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
        part = (part or "").strip()
        if not part:
            break
        content = f"{content}\n\n{part}" if content else part
        current_words = _count_words(content)
        if max_words and current_words > max_words:
            words = content.split()
            content = " ".join(words[:max_words])
            current_words = max_words
            break
        if not min_words:
            break

    current_version = metadata.get("current_version") if isinstance(metadata, dict) else None
    existing_content = (document.content or "").strip()
    if not versions and existing_content:
        base_version = "v1"
        versions.append(
            {
                "id": str(uuid4()),
                "version": base_version,
                "created_at": datetime.utcnow().isoformat(),
                "content": existing_content,
                "word_count": _count_words(existing_content),
                "min_word_count": metadata.get("min_word_count"),
                "max_word_count": metadata.get("max_word_count"),
                "summary": metadata.get("summary"),
                "instructions": None,
                "source_type": None,
                "source_comment_ids": None,
            }
        )
        current_version = base_version

    if versions:
        last_version = versions[-1].get("version") if isinstance(versions[-1], dict) else current_version
        major, minor = _parse_version(str(last_version))
        minor = minor + 1 if minor >= 0 else 1
        next_version = _format_version(major, minor)
    else:
        next_version = "v1"

    if source_content:
        source_type = "commented_rewrite" if comment_lines else "rewrite"
    else:
        source_type = "commented_generate" if comment_lines else "generate"

    version_id = str(uuid4())
    version_entry = {
        "id": version_id,
        "version": next_version,
        "created_at": datetime.utcnow().isoformat(),
        "content": content.strip(),
        "word_count": _count_words(content),
        "min_word_count": min_words,
        "max_word_count": max_words,
        "summary": summary or None,
        "instructions": user_instructions or None,
        "source_version_id": str(payload.source_version_id) if payload.source_version_id else None,
        "source_version": source_version,
        "source_type": source_type,
        "source_comment_ids": comment_ids or None,
    }
    versions.append(version_entry)

    if comment_ids:
        for entry in comments:
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get("id")
            if not entry_id or str(entry_id) not in comment_ids:
                continue
            applied = entry.get("applied_version_ids")
            applied_list = applied if isinstance(applied, list) else []
            if version_id not in applied_list:
                applied_list.append(version_id)
            entry["applied_version_ids"] = applied_list

    metadata_updates = {
        **(metadata if isinstance(metadata, dict) else {}),
        "versions": versions,
        "current_version": next_version,
        "comments": comments,
    }
    if min_words is not None:
        metadata_updates["min_word_count"] = min_words
    if max_words is not None:
        metadata_updates["max_word_count"] = max_words
    if summary:
        metadata_updates["summary"] = summary

    update_payload = DocumentUpdate(content=content.strip(), metadata=metadata_updates)

    updated = await document_service.update(
        document_id,
        update_payload,
        current_user.id,
    )
    return updated


@router.post("/{document_id}/versions", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document_version(
    document_id: UUID,
    payload: DocumentVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a manual version for a document."""
    document_service = DocumentService(db)
    document = await document_service.get_by_id(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content is required")

    metadata = document.document_metadata or {}
    versions = _load_versions(metadata)
    current_version = metadata.get("current_version") if isinstance(metadata, dict) else None
    existing_content = (document.content or "").strip()
    if not versions and existing_content:
        base_version = "v1"
        versions.append(
            {
                "id": str(uuid4()),
                "version": base_version,
                "created_at": datetime.utcnow().isoformat(),
                "content": existing_content,
                "word_count": _count_words(existing_content),
                "min_word_count": metadata.get("min_word_count"),
                "max_word_count": metadata.get("max_word_count"),
                "summary": metadata.get("summary"),
                "instructions": None,
                "source_type": None,
                "source_comment_ids": None,
            }
        )
        current_version = base_version

    source_version_id: Optional[UUID] = payload.source_version_id
    if source_version_id:
        source_version = _get_version_label(versions, source_version_id)
        if not source_version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source version not found")
    else:
        source_version = None
        if current_version:
            for entry in versions:
                if isinstance(entry, dict) and str(entry.get("version")) == str(current_version):
                    source_version_id = UUID(str(entry.get("id")))
                    source_version = entry.get("version")
                    break

    if versions:
        last_version = versions[-1].get("version") if isinstance(versions[-1], dict) else current_version
        major, minor = _parse_version(str(last_version))
        minor = minor + 1 if minor >= 0 else 1
        next_version = _format_version(major, minor)
    else:
        next_version = "v1"

    version_entry = {
        "id": str(uuid4()),
        "version": next_version,
        "created_at": datetime.utcnow().isoformat(),
        "content": content,
        "word_count": _count_words(content),
        "min_word_count": metadata.get("min_word_count"),
        "max_word_count": metadata.get("max_word_count"),
        "summary": metadata.get("summary"),
        "instructions": None,
        "source_version_id": str(source_version_id) if source_version_id else None,
        "source_version": source_version,
        "source_type": "manual_edit",
        "source_comment_ids": None,
        "edited_by": str(current_user.id),
    }
    versions.append(version_entry)

    metadata_updates = {
        **(metadata if isinstance(metadata, dict) else {}),
        "versions": versions,
        "current_version": next_version,
    }

    updated = await document_service.update(
        document_id,
        DocumentUpdate(content=content, metadata=metadata_updates),
        current_user.id,
    )
    return updated


@router.get("/{document_id}/versions", response_model=DocumentVersionList)
async def list_document_versions(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all versions for a document."""
    document_service = DocumentService(db)
    document = await document_service.get_by_id(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    metadata = document.document_metadata or {}
    versions, current_version = await _ensure_versions_for_document(
        document=document,
        document_service=document_service,
        user_id=current_user.id,
    )
    serialized: list[DocumentVersionSummary] = []
    for entry in versions:
        payload = _serialize_version(entry, current_version, include_content=False)
        if not payload:
            continue
        serialized.append(DocumentVersionSummary(**payload))

    return DocumentVersionList(versions=serialized, total=len(serialized))


@router.get("/{document_id}/comments", response_model=DocumentCommentList)
async def list_document_comments(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List comments for a document."""
    document_service = DocumentService(db)
    document = await document_service.get_by_id(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    metadata = document.document_metadata or {}
    comments = _load_comments(metadata)
    serialized: list[DocumentComment] = []
    for entry in comments:
        payload = _serialize_comment(entry)
        if not payload:
            continue
        serialized.append(DocumentComment(**payload))

    return DocumentCommentList(comments=serialized, total=len(serialized))


@router.post("/{document_id}/comments", response_model=DocumentComment, status_code=status.HTTP_201_CREATED)
async def create_document_comment(
    document_id: UUID,
    payload: DocumentCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a comment for a document."""
    document_service = DocumentService(db)
    document = await document_service.get_by_id(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment content is required")

    metadata = document.document_metadata or {}
    versions, current_version = await _ensure_versions_for_document(
        document=document,
        document_service=document_service,
        user_id=current_user.id,
    )
    if payload.version_id and not _get_version_label(versions, payload.version_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    comments = _load_comments(metadata)

    comment_entry = {
        "id": str(uuid4()),
        "content": content,
        "created_at": datetime.utcnow().isoformat(),
        "user_id": str(current_user.id),
        "version_id": str(payload.version_id) if payload.version_id else None,
        "applied_version_ids": [],
    }
    comments.append(comment_entry)

    metadata_updates = {
        **(metadata if isinstance(metadata, dict) else {}),
        "comments": comments,
    }
    if versions:
        metadata_updates["versions"] = versions
    if current_version:
        metadata_updates["current_version"] = current_version
    await document_service.update(
        document_id,
        DocumentUpdate(metadata=metadata_updates),
        current_user.id,
    )

    serialized = _serialize_comment(comment_entry)
    if not serialized:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create comment")
    return DocumentComment(**serialized)


@router.get("/{document_id}/versions/{version_id}", response_model=DocumentVersionResponse)
async def get_document_version(
    document_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific version for a document."""
    document_service = DocumentService(db)
    document = await document_service.get_by_id(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    metadata = document.document_metadata or {}
    versions, current_version = await _ensure_versions_for_document(
        document=document,
        document_service=document_service,
        user_id=current_user.id,
    )
    for entry in versions:
        if str(entry.get("id")) != str(version_id):
            continue
        payload = _serialize_version(entry, current_version, include_content=True)
        if not payload:
            break
        return DocumentVersionResponse(**payload)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
