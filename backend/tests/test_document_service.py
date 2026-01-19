from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.document import DocumentType
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.document_service import DocumentService


class DummyScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class DummyResult:
    def __init__(self, scalar=None, scalars=None):
        self._scalar = scalar
        self._scalars = scalars or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalar(self):
        return self._scalar

    def scalars(self):
        return DummyScalars(self._scalars)


class DummyDB:
    def __init__(self, results=None, projects=None):
        self._results = list(results or [])
        self._projects = projects or {}
        self.added = []
        self.commits = 0
        self.refreshes = 0
        self.deleted = []

    async def execute(self, *args, **kwargs):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshes += 1

    async def delete(self, obj):
        self.deleted.append(obj)

    async def get(self, model, key):
        return self._projects.get(key)


@pytest.mark.asyncio
async def test_get_all_by_project_returns_documents():
    project_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(id=project_id, owner_id=user_id)
    doc_one = SimpleNamespace(id=uuid4())
    doc_two = SimpleNamespace(id=uuid4())
    db = DummyDB(
        results=[
            DummyResult(scalar=project),
            DummyResult(scalar=2),
            DummyResult(scalars=[doc_one, doc_two]),
        ]
    )
    service = DocumentService(db)

    documents, total = await service.get_all_by_project(project_id, user_id, skip=0, limit=10)

    assert total == 2
    assert documents == [doc_one, doc_two]


@pytest.mark.asyncio
async def test_get_all_by_project_requires_ownership():
    db = DummyDB(results=[DummyResult(scalar=None)])
    service = DocumentService(db)

    with pytest.raises(HTTPException):
        await service.get_all_by_project(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_create_sets_word_count_and_metadata():
    project_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(id=project_id, owner_id=user_id, current_word_count=0)
    db = DummyDB(
        results=[
            DummyResult(scalar=project),
            DummyResult(scalar=5),
        ],
        projects={project_id: project},
    )
    service = DocumentService(db)
    payload = DocumentCreate(
        title="Doc",
        content="hello world",
        document_type=DocumentType.CHAPTER,
        project_id=project_id,
        order_index=1,
        metadata=None,
    )

    document = await service.create(payload, user_id)

    assert document.word_count == 2
    assert document.document_metadata == {}
    assert db.commits == 2
    assert db.refreshes == 1
    assert db.added


@pytest.mark.asyncio
async def test_update_updates_content_and_word_count():
    project_id = uuid4()
    user_id = uuid4()
    document = SimpleNamespace(
        id=uuid4(),
        title="Doc",
        content="old",
        document_metadata={"status": "draft"},
        word_count=1,
        project_id=project_id,
    )
    project = SimpleNamespace(id=project_id, current_word_count=1)
    db = DummyDB(
        results=[
            DummyResult(scalar=document),
            DummyResult(scalar=4),
        ],
        projects={project_id: project},
    )
    service = DocumentService(db)
    update_payload = DocumentUpdate(content="new content", metadata={"status": "done"})

    updated = await service.update(document.id, update_payload, user_id)

    assert updated.content == "new content"
    assert updated.word_count == 2
    assert updated.document_metadata == {"status": "done"}
    assert db.commits == 2
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_update_missing_document_raises():
    db = DummyDB(results=[DummyResult(scalar=None)])
    service = DocumentService(db)

    with pytest.raises(HTTPException):
        await service.update(uuid4(), DocumentUpdate(title="x"), uuid4())


@pytest.mark.asyncio
async def test_delete_removes_document_and_updates_words():
    project_id = uuid4()
    user_id = uuid4()
    document = SimpleNamespace(id=uuid4(), project_id=project_id)
    project = SimpleNamespace(id=project_id, current_word_count=5)
    db = DummyDB(
        results=[
            DummyResult(scalar=document),
            DummyResult(scalar=0),
        ],
        projects={project_id: project},
    )
    service = DocumentService(db)

    deleted = await service.delete(document.id, user_id)

    assert deleted is True
    assert db.deleted == [document]
    assert db.commits == 2


@pytest.mark.asyncio
async def test_delete_missing_document_returns_false():
    db = DummyDB(results=[DummyResult(scalar=None)])
    service = DocumentService(db)

    deleted = await service.delete(uuid4(), uuid4())

    assert deleted is False


@pytest.mark.asyncio
async def test_update_project_word_count_skips_missing_project():
    project_id = uuid4()
    db = DummyDB(results=[DummyResult(scalar=0)], projects={})
    service = DocumentService(db)

    await service._update_project_word_count(project_id)

    assert db.commits == 0
