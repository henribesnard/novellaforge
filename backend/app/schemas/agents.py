"""Schemas for agent analysis requests."""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConsistencyChapterRequest(BaseModel):
    """Request for chapter-level coherence analysis."""
    chapter_text: str
    project_id: Optional[UUID] = None
    memory_context: Optional[str] = None
    story_bible: Optional[Dict[str, Any]] = None
    previous_chapters: List[str] = Field(default_factory=list)


class ConsistencyProjectRequest(BaseModel):
    """Request for project-wide coherence analysis."""
    project_id: UUID
    all_chapters: Optional[List[Dict[str, Any]]] = None
    story_bible: Optional[Dict[str, Any]] = None
    continuity_memory: Optional[Dict[str, Any]] = None


class ConsistencyFixesRequest(BaseModel):
    """Request for coherence fix suggestions."""
    chapter_text: str
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    context: Optional[str] = None
    project_id: Optional[UUID] = None
