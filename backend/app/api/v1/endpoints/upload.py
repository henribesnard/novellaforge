"""File upload endpoints"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.models.document import Document, DocumentType
from app.core.security import get_current_active_user
from app.services.file_processor import FileProcessor
from app.services.document_service import DocumentService
from app.schemas.document import DocumentCreate
from app.schemas.upload import UploadResponse

router = APIRouter()


async def _get_next_order_index(db: AsyncSession, project_id: UUID) -> int:
    result = await db.execute(
        select(func.max(Document.order_index)).where(Document.project_id == project_id)
    )
    max_index = result.scalar()
    return (max_index + 1) if max_index is not None else 0


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    document_title: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload and process a document file.

    Supported formats: TXT, DOCX, PDF, MD
    Maximum file size: 10 MB

    Args:
        file: The file to upload
        project_id: ID of the project to attach the document to
        document_title: Optional custom title (defaults to filename)
    """
    try:
        # Verify project exists and belongs to user
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(
                Project.id == project_uuid,
                Project.owner_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )

        # Read file content
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
        file_content = await file.read()

        # Process file
        content, _ = await FileProcessor.process_file(file.filename, file_content)

        # Create document
        title = (document_title or file.filename).strip()
        order_index = await _get_next_order_index(db, project_uuid)
        document_service = DocumentService(db)
        document = await document_service.create(
            DocumentCreate(
                title=title,
                content=content,
                document_type=DocumentType.CHAPTER,
                order_index=order_index,
                project_id=project_uuid,
                metadata={
                    "original_filename": file.filename,
                    "file_type": file.content_type,
                },
            ),
            current_user.id,
        )

        return UploadResponse(
            success=True,
            message=f"File '{file.filename}' uploaded successfully",
            document_id=document.id,
            word_count=document.word_count,
            file_type=file.content_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )
