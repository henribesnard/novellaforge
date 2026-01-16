"""Chat message model"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(
        Enum(
            MessageRole,
            values_callable=lambda obj: [e.value for e in obj],
            name="messagerole",
        ),
        nullable=False,
    )
    content = Column(Text, nullable=False)

    # Optional project context
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)

    # User who sent/received the message
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Additional metadata (renamed to avoid conflict with SQLAlchemy's metadata)
    message_metadata = Column("metadata", JSONB, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="chat_messages")
    project = relationship("Project")

    def __repr__(self):
        return f"<ChatMessage {self.role}: {self.content[:50]}>"
