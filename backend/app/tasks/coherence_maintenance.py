"""Maintenance tasks for coherence data."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentType
from app.models.project import Project, ProjectStatus
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService


logger = logging.getLogger(__name__)


def _parse_project_id(project_id: str) -> Optional[UUID]:
    try:
        return UUID(str(project_id))
    except (TypeError, ValueError):
        logger.warning("Invalid project id provided to maintenance task: %s", project_id)
        return None


def _is_status(doc: Document, expected: str) -> bool:
    metadata = doc.document_metadata if isinstance(doc.document_metadata, dict) else {}
    return str(metadata.get("status") or "").lower() == expected


def _compare_continuity(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    changes = {
        "added_characters": [],
        "removed_characters": [],
        "status_changes": [],
        "significant_changes": False,
    }

    old_chars = {
        item.get("name"): item
        for item in (old.get("characters") or [])
        if isinstance(item, dict) and item.get("name")
    }
    new_chars = {
        item.get("name"): item
        for item in (new.get("characters") or [])
        if isinstance(item, dict) and item.get("name")
    }

    changes["added_characters"] = list(set(new_chars.keys()) - set(old_chars.keys()))
    changes["removed_characters"] = list(set(old_chars.keys()) - set(new_chars.keys()))

    for name in set(old_chars.keys()) & set(new_chars.keys()):
        if old_chars[name].get("status") != new_chars[name].get("status"):
            changes["status_changes"].append(
                {
                    "character": name,
                    "old_status": old_chars[name].get("status"),
                    "new_status": new_chars[name].get("status"),
                }
            )

    changes["significant_changes"] = (
        len(changes["added_characters"])
        + len(changes["removed_characters"])
        + len(changes["status_changes"])
    ) > 5
    return changes


async def _reconcile_project_memory(project_id: str) -> Dict[str, Any]:
    """Reconcile continuity memory with approved chapters."""
    project_uuid = _parse_project_id(project_id)
    if not project_uuid:
        return {"error": "Invalid project id"}

    async with AsyncSessionLocal() as db:
        project = await db.get(Project, project_uuid)
        if not project:
            return {"error": "Project not found"}

        result = await db.execute(
            select(Document)
            .where(
                Document.project_id == project_uuid,
                Document.document_type == DocumentType.CHAPTER,
            )
            .order_by(Document.order_index.asc())
        )
        chapters = list(result.scalars().all())
        approved = [doc for doc in chapters if _is_status(doc, "approved")]

        memory = MemoryService()
        fresh_metadata: Dict[str, Any] = {
            "continuity": {
                "characters": [],
                "locations": [],
                "relations": [],
                "events": [],
            }
        }

        for chapter in approved:
            if not chapter.content:
                continue
            facts = await memory.extract_facts(chapter.content)
            fresh_metadata = memory.merge_facts(fresh_metadata, facts)

        new_continuity = fresh_metadata.get("continuity") or {}
        metadata = project.project_metadata if isinstance(project.project_metadata, dict) else {}
        current_continuity = metadata.get("continuity")
        current_continuity = current_continuity if isinstance(current_continuity, dict) else {}
        differences = _compare_continuity(current_continuity, new_continuity)

        updated = False
        if differences["significant_changes"]:
            metadata["continuity"] = new_continuity
            metadata["last_reconciliation"] = datetime.utcnow().isoformat()
            project.project_metadata = metadata
            await db.commit()
            updated = True

        logger.info(
            "Reconciled project %s: approved=%s updated=%s",
            project_id,
            len(approved),
            updated,
        )
        return {
            "reconciled": True,
            "updated": updated,
            "chapters_processed": len(approved),
            "differences": differences,
        }


async def _rebuild_project_rag(project_id: str) -> Dict[str, Any]:
    """Rebuild the RAG index for a project."""
    project_uuid = _parse_project_id(project_id)
    if not project_uuid:
        return {"error": "Invalid project id"}

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(Document.project_id == project_uuid)
        )
        documents = list(result.scalars().all())

    rag = RagService()
    count = await rag.aindex_documents(project_uuid, documents, clear_existing=True)
    logger.info("Rebuilt RAG for project %s: chunks=%s", project_id, count)
    return {"reindexed": True, "chunks_count": count}


async def _cleanup_old_drafts(project_id: str, days_threshold: int) -> Dict[str, Any]:
    """Delete old draft documents beyond a threshold."""
    project_uuid = _parse_project_id(project_id)
    if not project_uuid:
        return {"error": "Invalid project id"}

    cutoff = datetime.utcnow() - timedelta(days=days_threshold)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(
                Document.project_id == project_uuid,
                Document.created_at < cutoff,
            )
        )
        documents = list(result.scalars().all())
        old_drafts = [doc for doc in documents if _is_status(doc, "draft")]

        for draft in old_drafts:
            await db.delete(draft)

        if old_drafts:
            await db.commit()

    logger.info(
        "Cleanup drafts for project %s: deleted=%s",
        project_id,
        len(old_drafts),
    )
    return {"deleted_drafts": len(old_drafts)}


async def _reconcile_all_active_projects() -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Project).where(Project.status != ProjectStatus.ARCHIVED)
        )
        projects = list(result.scalars().all())

    results = []
    for project in projects:
        results.append(await _reconcile_project_memory(str(project.id)))

    return {"projects_processed": len(projects), "results": results}


async def _rebuild_all_project_rags() -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Project).where(Project.status != ProjectStatus.ARCHIVED)
        )
        projects = list(result.scalars().all())

    results = []
    for project in projects:
        results.append(await _rebuild_project_rag(str(project.id)))

    return {"projects_processed": len(projects), "results": results}


@celery_app.task(name="reconcile_project_memory")
def reconcile_project_memory(project_id: str) -> Dict[str, Any]:
    return asyncio.run(_reconcile_project_memory(project_id))


@celery_app.task(name="rebuild_project_rag")
def rebuild_project_rag(project_id: str) -> Dict[str, Any]:
    return asyncio.run(_rebuild_project_rag(project_id))


@celery_app.task(name="cleanup_old_drafts")
def cleanup_old_drafts(project_id: str, days_threshold: int = 30) -> Dict[str, Any]:
    return asyncio.run(_cleanup_old_drafts(project_id, days_threshold))


@celery_app.task(name="reconcile_all_active_projects")
def reconcile_all_active_projects() -> Dict[str, Any]:
    return asyncio.run(_reconcile_all_active_projects())


@celery_app.task(name="rebuild_all_project_rags")
def rebuild_all_project_rags() -> Dict[str, Any]:
    return asyncio.run(_rebuild_all_project_rags())
