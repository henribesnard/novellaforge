"""Document service"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.document import Document
from app.models.project import Project
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentService:
    """Service for document operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _calculate_word_count(self, content: Optional[str]) -> int:
        """Calculate word count from content."""
        if not content:
            return 0
        return len(content.split())

    async def _verify_project_ownership(
        self,
        project_id: UUID,
        user_id: UUID
    ) -> Project:
        """
        Verify that user owns the project.

        Raises:
            HTTPException: If project not found or not owned by user
        """
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user_id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )

        return project

    async def get_by_id(
        self,
        document_id: UUID,
        user_id: UUID
    ) -> Optional[Document]:
        """
        Get document by ID (with ownership check via project).

        Args:
            document_id: Document ID
            user_id: User ID

        Returns:
            Document if found and user has access
        """
        result = await self.db.execute(
            select(Document)
            .join(Project)
            .where(
                Document.id == document_id,
                Project.owner_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_project(
        self,
        project_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Document], int]:
        """
        Get all documents for a project.

        Args:
            project_id: Project ID
            user_id: User ID (for ownership check)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (documents list, total count)
        """
        # Verify ownership
        await self._verify_project_ownership(project_id, user_id)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(Document.id)).where(
                Document.project_id == project_id
            )
        )
        total = count_result.scalar()

        # Get documents
        result = await self.db.execute(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.order_index.asc())
            .offset(skip)
            .limit(limit)
        )
        documents = result.scalars().all()

        return list(documents), total

    async def create(
        self,
        document_data: DocumentCreate,
        user_id: UUID
    ) -> Document:
        """
        Create a new document.

        Args:
            document_data: Document creation data
            user_id: User ID (for ownership check)

        Returns:
            Created document
        """
        # Verify ownership
        await self._verify_project_ownership(document_data.project_id, user_id)

        # Calculate word count
        word_count = self._calculate_word_count(document_data.content)

        document = Document(
            title=document_data.title,
            content=document_data.content,
            document_type=document_data.document_type,
            order_index=document_data.order_index,
            word_count=word_count,
            document_metadata=document_data.metadata or {},
            project_id=document_data.project_id
        )

        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)

        # Update project word count
        await self._update_project_word_count(document_data.project_id)

        return document

    async def update(
        self,
        document_id: UUID,
        document_data: DocumentUpdate,
        user_id: UUID
    ) -> Document:
        """
        Update document.

        Args:
            document_id: Document ID
            document_data: Update data
            user_id: User ID (for ownership check)

        Returns:
            Updated document

        Raises:
            HTTPException: If document not found or access denied
        """
        document = await self.get_by_id(document_id, user_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Update fields
        update_data = document_data.model_dump(exclude_unset=True)
        if "metadata" in update_data:
            document.document_metadata = update_data.pop("metadata") or {}
        for field, value in update_data.items():
            setattr(document, field, value)

        # Recalculate word count if content updated
        if document_data.content is not None:
            document.word_count = self._calculate_word_count(document.content)

        await self.db.commit()
        await self.db.refresh(document)

        # Update project word count
        await self._update_project_word_count(document.project_id)

        return document

    async def delete(self, document_id: UUID, user_id: UUID) -> bool:
        """
        Delete document.

        Args:
            document_id: Document ID
            user_id: User ID (for ownership check)

        Returns:
            True if deleted, False if not found
        """
        document = await self.get_by_id(document_id, user_id)
        if not document:
            return False

        project_id = document.project_id

        await self.db.delete(document)
        await self.db.commit()

        # Update project word count
        await self._update_project_word_count(project_id)

        return True

    async def _update_project_word_count(self, project_id: UUID):
        """Update total word count for a project."""
        result = await self.db.execute(
            select(func.sum(Document.word_count)).where(
                Document.project_id == project_id
            )
        )
        total_words = result.scalar() or 0

        # Update project
        project = await self.db.get(Project, project_id)
        if project:
            project.current_word_count = total_words
            await self.db.commit()
