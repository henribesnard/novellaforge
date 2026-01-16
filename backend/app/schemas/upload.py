"""Upload schemas"""
from pydantic import BaseModel
from uuid import UUID


class UploadResponse(BaseModel):
    """Response schema for file upload"""
    success: bool
    message: str
    document_id: UUID | None = None
    word_count: int | None = None
    file_type: str | None = None
