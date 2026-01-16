"""Project model"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    genre = Column(Enum(Genre), nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT, nullable=False)

    # Metadata
    target_word_count = Column(Integer, nullable=True)
    current_word_count = Column(Integer, default=0)

    # Structure
    structure_template = Column(String(50), nullable=True)  # "3-act", "5-act", "hero-journey", etc.
    project_metadata = Column(MutableDict.as_mutable(JSONB), default=dict)  # For flexible additional data

    # Owner
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project {self.title}>"
