"""Story bible schemas."""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorldRule(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    category: str = ""
    rule: str
    explanation: Optional[str] = None
    established_chapter: Optional[int] = Field(default=None, ge=1)
    exceptions: List[str] = Field(default_factory=list)
    importance: str = "medium"  # critical/high/medium/low


class TimelineEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event: str
    chapter_index: int = Field(..., ge=1)
    time_reference: Optional[str] = None
    absolute_date: Optional[str] = None
    duration: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    impact: Optional[str] = None


class GlossaryTerm(BaseModel):
    term: str
    definition: str
    first_mention_chapter: Optional[int] = Field(default=None, ge=1)
    aliases: List[str] = Field(default_factory=list)
    related_rules: List[UUID] = Field(default_factory=list)


class GlossaryPlace(BaseModel):
    name: str
    description: str
    first_mention_chapter: Optional[int] = Field(default=None, ge=1)
    rules: List[str] = Field(default_factory=list)
    atmosphere: Optional[str] = None


class GlossaryFaction(BaseModel):
    name: str
    description: str
    members: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    relationships: Dict[str, str] = Field(default_factory=dict)


class StoryBibleGlossary(BaseModel):
    terms: List[GlossaryTerm] = Field(default_factory=list)
    places: List[GlossaryPlace] = Field(default_factory=list)
    factions: List[GlossaryFaction] = Field(default_factory=list)


class CoreTheme(BaseModel):
    theme: str
    description: Optional[str] = None
    chapters_explored: List[int] = Field(default_factory=list)


class EstablishedFact(BaseModel):
    fact: str
    established_chapter: int = Field(..., ge=1)
    cannot_contradict: bool = True
    related_events: List[UUID] = Field(default_factory=list)
    resolution_of_contradiction: Optional[str] = None


class StoryBible(BaseModel):
    world_rules: List[WorldRule] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    glossary: StoryBibleGlossary = Field(default_factory=StoryBibleGlossary)
    core_themes: List[CoreTheme] = Field(default_factory=list)
    established_facts: List[EstablishedFact] = Field(default_factory=list)


class StoryBibleDraftValidationRequest(BaseModel):
    draft_text: str = Field(..., min_length=1)


class StoryBibleViolation(BaseModel):
    type: str
    detail: str
    severity: str
    rule_id: Optional[UUID] = None


class StoryBibleValidationResponse(BaseModel):
    violations: List[StoryBibleViolation] = Field(default_factory=list)
    blocking: bool = False
    summary: Optional[str] = None
