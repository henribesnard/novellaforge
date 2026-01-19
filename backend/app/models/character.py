"""Character model"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


def utc_now():
    """Return current UTC time - compatible with SQLAlchemy default"""
    # Return timezone-naive UTC datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
    return datetime.utcnow()


class Character(Base):
    """Character model"""
    __tablename__ = "characters"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Character details
    physical_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    backstory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    character_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
    )  # For relationships, goals, etc.

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
    project: Mapped["Project"] = relationship("Project", back_populates="characters")

    def __repr__(self):
        return f"<Character {self.name}>"
