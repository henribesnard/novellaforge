"""Character schemas"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class CharacterBase(BaseModel):
    """Base character schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    physical_description: Optional[str] = None
    personality: Optional[str] = None
    backstory: Optional[str] = None


class CharacterCreate(CharacterBase):
    """Schema for creating a new character"""
    project_id: UUID
    metadata: Optional[Dict[str, Any]] = None


class CharacterUpdate(BaseModel):
    """Schema for updating character"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    physical_description: Optional[str] = None
    personality: Optional[str] = None
    backstory: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        validation_alias="character_metadata",
        serialization_alias="metadata",
    )


class CharacterResponse(CharacterBase):
    """Schema for character response"""
    id: UUID
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="character_metadata",
        serialization_alias="metadata",
    )
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CharacterList(BaseModel):
    """Schema for character list response"""
    characters: list[CharacterResponse]
    total: int


class CharacterGenerateRequest(BaseModel):
    """Schema for auto-generating main characters"""
    project_id: UUID
    summary: str = Field(..., min_length=1)
    precision: Optional[str] = None
    count: Optional[int] = Field(None, ge=1, le=8)
