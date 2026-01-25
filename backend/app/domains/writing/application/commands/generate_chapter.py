"""Commands for the writing context."""
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.infrastructure.cqrs import Command


@dataclass(frozen=True)
class GenerateChapterCommand(Command):
    project_id: UUID
    user_id: UUID
    chapter_index: Optional[int] = None
    chapter_id: Optional[UUID] = None
    instruction: Optional[str] = None
    target_word_count: Optional[int] = None
    use_rag: bool = True
    reindex_documents: bool = False
    create_document: bool = True
    auto_approve: bool = False


@dataclass(frozen=True)
class ApproveChapterCommand(Command):
    chapter_id: UUID
    user_id: UUID
