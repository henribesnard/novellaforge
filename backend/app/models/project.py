"""Project model"""
from __future__ import annotations

from datetime import datetime
import enum
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document
    from app.models.character import Character


def utc_now():
    """Return current UTC time - compatible with SQLAlchemy default"""
    # Return timezone-naive UTC datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
    return datetime.utcnow()


class ProjectStatus(str, enum.Enum):
    """Project status enumeration"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Genre(str, enum.Enum):
    """Genre enumeration"""
    WEREWOLF = "werewolf"
    BILLIONAIRE = "billionaire"
    MAFIA = "mafia"
    FANTASY = "fantasy"
    VENGEANCE = "vengeance"
    FICTION = "fiction"
    SCIFI = "scifi"
    THRILLER = "thriller"
    ROMANCE = "romance"
    MYSTERY = "mystery"
    HORROR = "horror"
    HISTORICAL = "historical"
    OTHER = "other"


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    genre: Mapped[Optional[Genre]] = mapped_column(Enum(Genre), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        default=ProjectStatus.DRAFT,
        nullable=False,
    )

    # Metadata
    target_word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_word_count: Mapped[int] = mapped_column(Integer, default=0)

    # Structure
    structure_template: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # "3-act", "5-act", "hero-journey", etc.
    project_metadata: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
    )  # For flexible additional data (continuity, story_bible, tracked_contradictions)

    # Owner
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    characters: Mapped[list["Character"]] = relationship(
        "Character",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Project {self.title}>"
