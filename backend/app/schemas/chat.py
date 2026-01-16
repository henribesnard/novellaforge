"""Chat schemas"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class ChatMessageCreate(BaseModel):
    """Schema for creating a chat message"""
    message: str = Field(..., min_length=1)
    project_id: Optional[UUID] = None


class ChatMessageResponse(BaseModel):
    """Schema for chat message response"""
    response: str
    message_id: str
    project_context: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    """Schema for a chat message"""
    id: UUID
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    project_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="message_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response"""
    messages: List[ChatMessage]
    total: int
