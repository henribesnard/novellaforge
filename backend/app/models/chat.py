"""Chat message model"""
from __future__ import annotations

from datetime import datetime
import enum
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project


def utc_now():
    """Return current UTC time - compatible with SQLAlchemy default"""
    # Return timezone-naive UTC datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
    return datetime.utcnow()


class MessageRole(str, enum.Enum):
    """Message role enumeration"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(Base):
    """Chat message model"""
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role: Mapped[MessageRole] = mapped_column(
        Enum(
            MessageRole,
            values_callable=lambda obj: [e.value for e in obj],
            name="messagerole",
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional project context
    project_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    # User who sent/received the message
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Additional metadata (renamed to avoid conflict with SQLAlchemy's metadata)
    message_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_messages")
    project: Mapped[Optional["Project"]] = relationship("Project")

    def __repr__(self):
        return f"<ChatMessage {self.role}: {self.content[:50]}>"
