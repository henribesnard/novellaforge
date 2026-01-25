"""Command handlers for the writing context."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.writing_pipeline import WritingPipeline
from app.infrastructure.cqrs import CommandHandler
from app.domains.writing.application.commands.generate_chapter import (
    GenerateChapterCommand,
    ApproveChapterCommand,
)


class GenerateChapterHandler(CommandHandler[GenerateChapterCommand, Dict[str, Any]]):
    """Handle chapter generation commands using the existing pipeline."""

    def __init__(
        self,
        db: AsyncSession,
        pipeline_factory: Optional[Callable[[AsyncSession], WritingPipeline]] = None,
    ) -> None:
        self.db = db
        self.pipeline_factory = pipeline_factory or (lambda db: WritingPipeline(db))

    async def handle(self, command: GenerateChapterCommand) -> Dict[str, Any]:
        pipeline = self.pipeline_factory(self.db)
        return await pipeline.generate_chapter(
            {
                "project_id": command.project_id,
                "user_id": command.user_id,
                "chapter_id": command.chapter_id,
                "chapter_index": command.chapter_index,
                "chapter_instruction": command.instruction,
                "target_word_count": command.target_word_count,
                "use_rag": command.use_rag,
                "reindex_documents": command.reindex_documents,
                "create_document": command.create_document,
                "auto_approve": command.auto_approve,
            }
        )


class ApproveChapterHandler(CommandHandler[ApproveChapterCommand, Dict[str, Any]]):
    """Handle chapter approval commands using the existing pipeline."""

    def __init__(
        self,
        db: AsyncSession,
        pipeline_factory: Optional[Callable[[AsyncSession], WritingPipeline]] = None,
    ) -> None:
        self.db = db
        self.pipeline_factory = pipeline_factory or (lambda db: WritingPipeline(db))

    async def handle(self, command: ApproveChapterCommand) -> Dict[str, Any]:
        pipeline = self.pipeline_factory(self.db)
        return await pipeline.approve_chapter(str(command.chapter_id), command.user_id)
