from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.api.v1.endpoints.upload as upload_module
from app.models.document import DocumentType


class DummyResult:
    def __init__(self, project):
        self._project = project

    def scalar_one_or_none(self):
        return self._project


class DummyDB:
    def __init__(self, project=None):
        self.project = project
        self.rollback_calls = 0

    async def execute(self, *args, **kwargs):
        return DummyResult(self.project)

    async def rollback(self):
        self.rollback_calls += 1


class DummyFile:
    def __init__(self, filename, content_type, payload):
        self.filename = filename
        self.content_type = content_type
        self._payload = payload

    async def read(self):
        return self._payload


@pytest.mark.asyncio
async def test_upload_file_rejects_missing_filename():
    db = DummyDB(project=SimpleNamespace(id=uuid4(), owner_id=uuid4()))
    file = DummyFile(filename="", content_type="text/plain", payload=b"hello")

    with pytest.raises(HTTPException) as excinfo:
        await upload_module.upload_file(
            file=file,
            project_id=str(db.project.id),
            document_title=None,
            db=db,
            current_user=SimpleNamespace(id=db.project.owner_id),
        )

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_upload_file_rejects_missing_project():
    db = DummyDB(project=None)
    file = DummyFile(filename="note.txt", content_type="text/plain", payload=b"hello")

    with pytest.raises(HTTPException) as excinfo:
        await upload_module.upload_file(
            file=file,
            project_id=str(uuid4()),
            document_title=None,
            db=db,
            current_user=SimpleNamespace(id=uuid4()),
        )

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_upload_file_success(monkeypatch):
    project = SimpleNamespace(id=uuid4(), owner_id=uuid4())
    db = DummyDB(project=project)
    file = DummyFile(filename="note.txt", content_type="text/plain", payload=b"hello world")
    created = {}

    async def fake_process_file(filename, payload):
        return "content", 2

    class DummyDocumentService:
        def __init__(self, db):
            self.db = db

        async def create(self, data, user_id):
            created["data"] = data
            created["user_id"] = user_id
            return SimpleNamespace(id=uuid4(), word_count=2)

    async def fake_next_index(db, project_id):
        return 3

    monkeypatch.setattr(upload_module.FileProcessor, "process_file", fake_process_file)
    monkeypatch.setattr(upload_module, "DocumentService", DummyDocumentService)
    monkeypatch.setattr(upload_module, "_get_next_order_index", fake_next_index)

    result = await upload_module.upload_file(
        file=file,
        project_id=str(project.id),
        document_title=None,
        db=db,
        current_user=SimpleNamespace(id=project.owner_id),
    )

    assert result.success is True
    assert result.word_count == 2
    assert result.file_type == "text/plain"
    assert created["user_id"] == project.owner_id
    assert created["data"].document_type == DocumentType.CHAPTER
    assert created["data"].order_index == 3


@pytest.mark.asyncio
async def test_upload_file_rolls_back_on_error(monkeypatch):
    project = SimpleNamespace(id=uuid4(), owner_id=uuid4())
    db = DummyDB(project=project)
    file = DummyFile(filename="note.txt", content_type="text/plain", payload=b"hello")

    async def fake_process_file(filename, payload):
        raise Exception("boom")

    async def fake_next_index(db, project_id):
        return 0

    monkeypatch.setattr(upload_module.FileProcessor, "process_file", fake_process_file)
    monkeypatch.setattr(upload_module, "_get_next_order_index", fake_next_index)

    with pytest.raises(HTTPException) as excinfo:
        await upload_module.upload_file(
            file=file,
            project_id=str(project.id),
            document_title=None,
            db=db,
            current_user=SimpleNamespace(id=project.owner_id),
        )

    assert excinfo.value.status_code == 500
    assert db.rollback_calls == 1
