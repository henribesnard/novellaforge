"""Schemas for writing pipeline requests and responses."""
from typing import Optional, Dict, Any, List, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class IndexProjectRequest(BaseModel):
    """Index all documents for a project into vector memory."""
    project_id: UUID
    clear_existing: bool = True


class IndexProjectResponse(BaseModel):
    success: bool
    chunks_indexed: int


class ChapterGenerationRequest(BaseModel):
    """Request to generate or rewrite a single chapter."""
    project_id: UUID
    chapter_id: Optional[UUID] = None
    chapter_index: Optional[int] = Field(default=None, ge=1)
    instruction: Optional[str] = None
    rewrite_focus: Optional[Literal["emotion", "tension", "action", "custom"]] = None
    target_word_count: Optional[int] = Field(None, ge=100)
    use_rag: bool = True
    reindex_documents: bool = False
    create_document: bool = True
    auto_approve: bool = False


class ChapterCritique(BaseModel):
    score: float
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    cliffhanger_ok: bool = False
    pacing_ok: bool = False


class ChapterGenerationResponse(BaseModel):
    success: bool
    chapter_title: str
    plan: Optional[Dict[str, Any]] = None
    content: str
    word_count: int
    document_id: Optional[str] = None
    critique: Optional[ChapterCritique] = None
    needs_review: bool = True
    continuity_alerts: List[str] = Field(default_factory=list)
    retrieved_chunks: List[str] = Field(default_factory=list)


class ChapterApprovalRequest(BaseModel):
    document_id: UUID


class ChapterApprovalResponse(BaseModel):
    success: bool
    document_id: str
    status: str
    summary: Optional[str] = None
