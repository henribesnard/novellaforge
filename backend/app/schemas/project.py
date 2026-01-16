"""Project schemas"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

from app.models.project import ProjectStatus, Genre


class ProjectBase(BaseModel):
    """Base project schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    genre: Optional[Genre] = None
    target_word_count: Optional[int] = Field(None, gt=0)
    structure_template: Optional[str] = None


class ProjectCreate(BaseModel):
    """Schema for creating a new project"""
    genre: Genre
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    target_word_count: Optional[int] = Field(None, gt=0)
    structure_template: Optional[str] = None


class ProjectUpdate(BaseModel):
    """Schema for updating project"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    genre: Optional[Genre] = None
    status: Optional[ProjectStatus] = None
    target_word_count: Optional[int] = Field(None, gt=0)
    current_word_count: Optional[int] = Field(None, ge=0)
    structure_template: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        validation_alias="project_metadata",
        serialization_alias="metadata",
    )


class ProjectDeleteRequest(BaseModel):
    """Schema for deleting a project with confirmation"""
    confirm_title: str = Field(..., min_length=1, max_length=255)


class ProjectResponse(ProjectBase):
    """Schema for project response"""
    id: UUID
    status: ProjectStatus
    current_word_count: int
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="project_metadata",
        serialization_alias="metadata",
    )
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProjectList(BaseModel):
    """Schema for project list response"""
    projects: list[ProjectResponse]
    total: int
