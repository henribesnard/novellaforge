"""Document model"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum
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


class DocumentType(str, enum.Enum):
    """Document type enumeration"""
    CHAPTER = "chapter"
    SCENE = "scene"
    NOTE = "note"
    OUTLINE = "outline"


class Document(Base):
    """Document model"""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    document_type = Column(Enum(DocumentType), default=DocumentType.CHAPTER, nullable=False)

    # Metadata
    order_index = Column(Integer, default=0)  # For ordering chapters/scenes
    word_count = Column(Integer, default=0)
    document_metadata = Column(JSONB, default=dict)  # For additional data (tags, notes, etc.)

    # Project relationship
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    project = relationship("Project", back_populates="documents")

    def __repr__(self):
        return f"<Document {self.title}>"
