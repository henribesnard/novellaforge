"""Chat endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatMessage,
    ChatHistoryResponse,
)
from app.services.chat_service import ChatService
from app.core.security import get_current_active_user

router = APIRouter()


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Send a chat message to NovellaForge and get a response.

    - **message**: The message to send (required)
    - **project_id**: Optional project ID for context
    """
    chat_service = ChatService(db)

    try:
        response = await chat_service.send_message(
            user_id=current_user.id,
            message_content=data.message,
            project_id=data.project_id,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}",
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    project_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get chat history for the current user.

    - **project_id**: Optional project ID to filter messages
    - **limit**: Maximum number of messages to return (max 100)
    """
    chat_service = ChatService(db)

    try:
        messages = await chat_service.get_history(
            user_id=current_user.id,
            project_id=project_id,
            limit=limit,
        )

        return ChatHistoryResponse(
            messages=messages,
            total=len(messages),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get chat history: {str(e)}",
        )
