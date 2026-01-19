"""Schemas for NovellaForge concept and planning workflows."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.project import Genre


class ConceptGenerateRequest(BaseModel):
    """Request to generate or regenerate a concept."""
    force: bool = False


class ConceptPayload(BaseModel):
    title: str = ""
    premise: str
    tone: str
    tropes: List[str]
    emotional_orientation: str


class ConceptProposalRequest(BaseModel):
    """Request to generate a concept proposal before project creation."""
    genre: Genre
    notes: Optional[str] = None


class ConceptProposalResponse(BaseModel):
    status: str
    concept: ConceptPayload
    updated_at: datetime


class ConceptResponse(BaseModel):
    project_id: UUID
    status: str
    concept: ConceptPayload
    updated_at: datetime


class SynopsisGenerateRequest(BaseModel):
    notes: Optional[str] = None


class SynopsisResponse(BaseModel):
    project_id: UUID
    status: str
    synopsis: str
    updated_at: datetime


class SynopsisUpdateRequest(BaseModel):
    synopsis: str


class ArcPlan(BaseModel):
    id: str
    title: str
    summary: str
    target_emotion: str
    chapter_start: int
    chapter_end: int


class ChapterPlan(BaseModel):
    index: int
    title: str
    summary: str
    emotional_stake: str
    arc_id: Optional[str] = None
    status: str = "planned"
    cliffhanger_type: Optional[str] = None
    required_plot_points: List[str] = Field(default_factory=list)
    optional_subplots: List[str] = Field(default_factory=list)
    arc_constraints: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    success_criteria: Optional[str] = None


class PlanPayload(BaseModel):
    global_summary: str
    arcs: List[ArcPlan]
    chapters: List[ChapterPlan]


class PlanGenerateRequest(BaseModel):
    chapter_count: Optional[int] = Field(default=None, ge=1, le=300)
    arc_count: Optional[int] = Field(default=None, ge=1, le=20)
    regenerate: bool = False


class PlanUpdateRequest(BaseModel):
    plan: PlanPayload


class PlanResponse(BaseModel):
    project_id: UUID
    status: str
    plan: PlanPayload
    updated_at: datetime
