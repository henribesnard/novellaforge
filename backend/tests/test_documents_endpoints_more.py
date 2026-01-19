from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import documents as documents_module
from app.models.document import DocumentType
from app.schemas.document import DocumentCommentCreate, ElementGenerateRequest


class DummyDocumentService:
    def __init__(self, document):
        self.document = document
        self.update_calls = []

    async def get_by_id(self, document_id, user_id):
        return self.document

    async def update(self, document_id, document_data, user_id):
        update_data = document_data.model_dump(exclude_unset=True)
        if "metadata" in update_data:
            self.document.document_metadata = update_data["metadata"]
        if "content" in update_data:
            self.document.content = update_data["content"]
        if "title" in update_data:
            self.document.title = update_data["title"]
        self.update_calls.append(update_data)
        return self.document


class DummyContextService:
    def __init__(self, db):
        self.db = db

    async def build_project_context(self, project_id, user_id):
        return {
            "project": {"title": "Project", "genre": None, "description": ""},
            "instructions": [],
            "characters": [],
            "documents": [],
            "constraints": {},
        }


@pytest.mark.asyncio
async def test_list_document_comments_filters_invalid_entries(monkeypatch):
    comment_id = uuid4()
    document = SimpleNamespace(
        id=uuid4(),
        document_metadata={
            "comments": [
                {
                    "id": str(comment_id),
                    "content": "Check this.",
                    "created_at": datetime.utcnow().isoformat(),
                    "user_id": str(uuid4()),
                    "version_id": None,
                },
                {"content": "missing id"},
            ]
        },
    )
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)

    result = await documents_module.list_document_comments(document.id, db=None, current_user=SimpleNamespace(id=uuid4()))

    assert result.total == 1
    assert result.comments[0].id == comment_id


@pytest.mark.asyncio
async def test_create_document_comment_requires_existing_version(monkeypatch):
    document = SimpleNamespace(
        id=uuid4(),
        document_metadata={
            "versions": [
                {
                    "id": str(uuid4()),
                    "version": "v1",
                    "created_at": datetime.utcnow().isoformat(),
                    "content": "text",
                }
            ],
            "current_version": "v1",
        },
        content="text",
    )
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)

    with pytest.raises(HTTPException):
        await documents_module.create_document_comment(
            document.id,
            DocumentCommentCreate(content="Note", version_id=uuid4()),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )


@pytest.mark.asyncio
async def test_create_document_comment_creates_versions_when_missing(monkeypatch):
    document = SimpleNamespace(
        id=uuid4(),
        document_metadata={},
        content="Some content",
        title="Doc",
    )
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)

    result = await documents_module.create_document_comment(
        document.id,
        DocumentCommentCreate(content="Check this."),
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result.content == "Check this."
    assert document.document_metadata.get("versions")
    assert document.document_metadata.get("current_version") == "v1"
    assert document.document_metadata.get("comments")
    assert len(service.update_calls) == 2


@pytest.mark.asyncio
async def test_list_document_versions_creates_initial_version(monkeypatch):
    document = SimpleNamespace(
        id=uuid4(),
        document_metadata={},
        content="Initial content",
        title="Doc",
    )
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)

    result = await documents_module.list_document_versions(
        document.id,
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result.total == 1
    assert result.versions[0].version == "v1"


@pytest.mark.asyncio
async def test_get_document_version_not_found(monkeypatch):
    version_id = uuid4()
    document = SimpleNamespace(
        id=uuid4(),
        document_metadata={
            "versions": [
                {
                    "id": str(uuid4()),
                    "version": "v1",
                    "created_at": datetime.utcnow().isoformat(),
                    "content": "text",
                }
            ],
            "current_version": "v1",
        },
        content="text",
    )
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)

    with pytest.raises(HTTPException):
        await documents_module.get_document_version(
            document.id,
            version_id,
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )


@pytest.mark.asyncio
async def test_get_document_version_returns_content(monkeypatch):
    version_id = uuid4()
    document = SimpleNamespace(
        id=uuid4(),
        document_metadata={
            "versions": [
                {
                    "id": str(version_id),
                    "version": "v1",
                    "created_at": datetime.utcnow().isoformat(),
                    "content": "text",
                    "word_count": 1,
                }
            ],
            "current_version": "v1",
        },
        content="text",
    )
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)

    result = await documents_module.get_document_version(
        document.id,
        version_id,
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result.content == "text"
    assert result.is_current is True


@pytest.mark.asyncio
async def test_generate_element_rejects_invalid_word_range(monkeypatch):
    document = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        title="Doc",
        content="",
        document_type=DocumentType.CHAPTER,
        document_metadata={},
    )
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)
    monkeypatch.setattr(documents_module, "ProjectContextService", DummyContextService)

    with pytest.raises(HTTPException):
        await documents_module.generate_element(
            document.id,
            ElementGenerateRequest(min_word_count=120, max_word_count=10),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )


@pytest.mark.asyncio
async def test_generate_element_requires_source_version(monkeypatch):
    document = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        title="Doc",
        content="Base content",
        document_type=DocumentType.CHAPTER,
        document_metadata={},
    )
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)
    monkeypatch.setattr(documents_module, "ProjectContextService", DummyContextService)

    with pytest.raises(HTTPException):
        await documents_module.generate_element(
            document.id,
            ElementGenerateRequest(source_version_id=uuid4()),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )


@pytest.mark.asyncio
async def test_generate_element_rejects_missing_comment_selection(monkeypatch):
    document = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        title="Doc",
        content="Base content",
        document_type=DocumentType.CHAPTER,
        document_metadata={
            "comments": [
                {
                    "id": str(uuid4()),
                    "content": "Other comment",
                    "created_at": datetime.utcnow().isoformat(),
                    "user_id": str(uuid4()),
                    "version_id": None,
                    "applied_version_ids": [],
                }
            ]
        },
    )
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)
    monkeypatch.setattr(documents_module, "ProjectContextService", DummyContextService)

    with pytest.raises(HTTPException):
        await documents_module.generate_element(
            document.id,
            ElementGenerateRequest(comment_ids=[uuid4()]),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )
