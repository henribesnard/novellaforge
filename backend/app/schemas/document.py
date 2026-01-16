"""Document schemas"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

from app.models.document import DocumentType


class DocumentBase(BaseModel):
    """Base document schema"""
    title: str = Field(..., min_length=1, max_length=255)
    content: Optional[str] = None
    document_type: DocumentType = DocumentType.CHAPTER


class DocumentCreate(DocumentBase):
    """Schema for creating a new document"""
    project_id: UUID
    order_index: int = 0
    metadata: Optional[Dict[str, Any]] = None


class DocumentUpdate(BaseModel):
    """Schema for updating document"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    document_type: Optional[DocumentType] = None
    order_index: Optional[int] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        validation_alias="document_metadata",
        serialization_alias="metadata",
    )

    model_config = ConfigDict(populate_by_name=True)


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: UUID
    order_index: int
    word_count: int
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="document_metadata",
        serialization_alias="metadata",
    )
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DocumentList(BaseModel):
    """Schema for document list response"""
    documents: list[DocumentResponse]
    total: int


class ElementCreateRequest(BaseModel):
    """Schema for creating a structured element"""
    project_id: UUID
    element_type: str = Field(..., min_length=1, max_length=50)
    parent_id: Optional[UUID] = None


class ElementGenerateRequest(BaseModel):
    """Schema for generating or rewriting an element"""
    instructions: Optional[str] = None
    min_word_count: Optional[int] = Field(None, ge=1)
    max_word_count: Optional[int] = Field(None, ge=1)
    summary: Optional[str] = None
    source_version_id: Optional[UUID] = None
    comment_ids: Optional[list[UUID]] = None


class DocumentVersionCreate(BaseModel):
    """Schema for creating a manual document version"""
    content: str = Field(..., min_length=1)
    source_version_id: Optional[UUID] = None


class DocumentVersionSummary(BaseModel):
    """Summary of a document version"""
    id: UUID
    version: str
    created_at: datetime
    word_count: int
    min_word_count: Optional[int] = None
    max_word_count: Optional[int] = None
    summary: Optional[str] = None
    instructions: Optional[str] = None
    source_version_id: Optional[str] = None
    source_version: Optional[str] = None
    source_type: Optional[str] = None
    source_comment_ids: Optional[list[str]] = None
    is_current: bool = False


class DocumentVersionResponse(DocumentVersionSummary):
    """Document version with content"""
    content: str


class DocumentVersionList(BaseModel):
    """Schema for list of document versions"""
    versions: list[DocumentVersionSummary]
    total: int


class DocumentCommentCreate(BaseModel):
    """Schema for creating a document comment"""
    content: str = Field(..., min_length=1)
    version_id: Optional[UUID] = None


class DocumentComment(BaseModel):
    """Schema for document comment"""
    id: UUID
    content: str
    created_at: datetime
    user_id: UUID
    version_id: Optional[UUID] = None
    applied_version_ids: Optional[list[str]] = None


class DocumentCommentList(BaseModel):
    """Schema for list of document comments"""
    comments: list[DocumentComment]
    total: int
