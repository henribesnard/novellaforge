"""Schemas for coherence features."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class IntentionalMystery(BaseModel):
    """An intentional contradiction/mystery in the narrative."""

    id: str
    description: str = Field(..., min_length=10)
    contradiction_type: str = Field(
        ...,
        pattern="^(lie|unreliable_narrator|hidden_info|time_paradox|identity_secret)$"
    )
    introduced_chapter: int = Field(..., ge=1)
    resolution_planned_chapter: Optional[int] = Field(None, ge=1)
    characters_involved: List[str] = Field(default_factory=list)
    hints_to_drop: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolution_chapter: Optional[int] = None


class IntentionalMysteryCreate(BaseModel):
    """Schema for creating an intentional mystery."""

    description: str = Field(..., min_length=10)
    contradiction_type: str = Field(
        ...,
        pattern="^(lie|unreliable_narrator|hidden_info|time_paradox|identity_secret)$"
    )
    introduced_chapter: int = Field(..., ge=1)
    resolution_planned_chapter: Optional[int] = Field(None, ge=1)
    characters_involved: List[str] = Field(default_factory=list)
    hints_to_drop: List[str] = Field(default_factory=list)


class ChekhovGunSchema(BaseModel):
    """Schema for a Chekhov's Gun."""

    element: str
    element_type: str = Field(
        ...,
        pattern="^(object|skill|threat|promise|foreshadowing|question)$"
    )
    expectation: str
    introduced_chapter: int
    urgency: int = Field(5, ge=1, le=10)
    resolved: bool = False
    resolved_chapter: Optional[int] = None
    hints_dropped: List[dict] = Field(default_factory=list)


class ChekhovGunCreate(BaseModel):
    """Schema for creating a Chekhov's Gun."""

    element: str = Field(..., min_length=3)
    element_type: str = Field(
        ...,
        pattern="^(object|skill|threat|promise|foreshadowing|question)$"
    )
    expectation: str = Field(..., min_length=10)
    introduced_chapter: int = Field(..., ge=1)
    urgency: int = Field(5, ge=1, le=10)


class VoiceAnalysisResult(BaseModel):
    """Result of voice consistency analysis."""

    character: str
    voice_consistency_score: float = Field(..., ge=0.0, le=1.0)
    analysis_available: bool
    drift_detected: bool = False
    dialogues_analyzed: int = 0
    reference_dialogues: int = 0
    outlier_dialogues: List[dict] = Field(default_factory=list)


class CharacterDriftResult(BaseModel):
    """Result of character drift detection."""

    character: str
    chapter_index: int
    drift_detected: bool
    drift_type: Optional[str] = None
    severity: int = Field(0, ge=0, le=10)
    analysis: str = ""
    established_traits: List[str] = Field(default_factory=list)
    conflicting_behavior: Optional[str] = None
    justification_found: bool = False
    justification_event: Optional[str] = None
    suggested_resolution: Optional[str] = None


class POVViolation(BaseModel):
    """A POV violation found in text."""

    type: str = Field(
        ...,
        pattern="^(forbidden_thoughts|impossible_knowledge|accidental_omniscience)$"
    )
    severity: str = Field(..., pattern="^(high|medium|low)$")
    location: str
    character_involved: Optional[str] = None
    explanation: str
    suggested_fix: Optional[str] = None


class POVValidationResult(BaseModel):
    """Result of POV validation."""

    pov_character: str
    pov_type: str
    violations: List[POVViolation] = Field(default_factory=list)
    valid: bool
    overall_assessment: Optional[str] = None


class SemanticContradiction(BaseModel):
    """A semantic contradiction detected between facts."""

    new_fact: str
    established_fact: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    contradiction_type: str
    pattern: Optional[tuple] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: str = Field("medium", pattern="^(high|medium|low)$")


class RecursiveMemoryContext(BaseModel):
    """Context built by recursive memory system."""

    global_synopsis: Optional[str] = None
    arc_summary: Optional[str] = None
    recent_chapters: List[dict] = Field(default_factory=list)


class CoherenceAnalysisRequest(BaseModel):
    """Request for coherence analysis."""

    project_id: str
    chapter_index: int
    chapter_text: str
    include_semantic: bool = True
    include_character_drift: bool = True
    include_voice: bool = True
    include_pov: bool = True


class CoherenceAnalysisResponse(BaseModel):
    """Full coherence analysis response."""

    project_id: str
    chapter_index: int
    overall_score: float = Field(..., ge=0.0, le=10.0)

    # ConsistencyAnalyst results
    contradictions: List[dict] = Field(default_factory=list)
    timeline_issues: List[dict] = Field(default_factory=list)
    character_inconsistencies: List[dict] = Field(default_factory=list)
    world_rule_violations: List[dict] = Field(default_factory=list)

    # Additional analyses
    semantic_contradictions: List[SemanticContradiction] = Field(default_factory=list)
    character_drift: List[CharacterDriftResult] = Field(default_factory=list)
    voice_analysis: dict = Field(default_factory=dict)
    pov_validation: Optional[POVValidationResult] = None

    # Filtered intentional inconsistencies
    filtered_intentional: List[dict] = Field(default_factory=list)

    # Summary
    blocking_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
