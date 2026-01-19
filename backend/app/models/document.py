"""Document model"""
from __future__ import annotations

from datetime import datetime
import enum
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


def utc_now():
    """Return current UTC time - compatible with SQLAlchemy default"""
    # Return timezone-naive UTC datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
    return datetime.utcnow()


class DocumentType(str, enum.Enum):
    """Document type enumeration"""
    CHAPTER = "chapter"
    SCENE = "scene"
    NOTE = "note"
    OUTLINE = "outline"


class Document(Base):
    """Document model"""
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType),
        default=DocumentType.CHAPTER,
        nullable=False,
    )

    # Metadata
    order_index: Mapped[int] = mapped_column(Integer, default=0)  # For ordering chapters/scenes
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    document_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
    )  # For additional data (tags, notes, etc.)

    # Project relationship
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="documents")

    def __repr__(self):
        return f"<Document {self.title}>"
