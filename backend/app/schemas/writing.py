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


class PlotPointValidation(BaseModel):
    covered_points: List[str] = Field(default_factory=list)
    missing_points: List[str] = Field(default_factory=list)
    forbidden_violations: List[str] = Field(default_factory=list)
    coverage_score: float = 0.0
    explanation: Optional[str] = None


class ContinuityValidation(BaseModel):
    severe_issues: List[Dict[str, Any]] = Field(default_factory=list)
    minor_issues: List[Dict[str, Any]] = Field(default_factory=list)
    coherence_score: float = 0.0
    blocking: bool = False
    plot_point_validation: Optional[PlotPointValidation] = None
    graph_issues: List[Dict[str, Any]] = Field(default_factory=list)


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
    continuity_validation: Optional[ContinuityValidation] = None
    retrieved_chunks: List[str] = Field(default_factory=list)


class ChapterApprovalRequest(BaseModel):
    document_id: UUID


class ChapterApprovalResponse(BaseModel):
    success: bool
    document_id: str
    status: str
    summary: Optional[str] = None
    rag_updated: bool = False
    rag_update_error: Optional[str] = None


class StreamingChapterRequest(BaseModel):
    """Request for streaming chapter generation via WebSocket."""
    project_id: UUID
    chapter_id: Optional[UUID] = None
    chapter_index: Optional[int] = Field(default=None, ge=1)
    instruction: Optional[str] = None
    target_word_count: Optional[int] = Field(None, ge=100)
    use_rag: bool = True


class PregeneratePlansRequest(BaseModel):
    """Request to pregenerate plans for upcoming chapters."""
    project_id: UUID
    count: int = Field(default=5, ge=1, le=20)


class PregeneratePlansResponse(BaseModel):
    success: bool
    status: str
    chapters_to_plan: int
    task_id: Optional[str] = None
