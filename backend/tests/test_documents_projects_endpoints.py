import io
import zipfile
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import documents as documents_module
from app.api.v1.endpoints import projects as projects_module
from app.models.document import DocumentType
from app.schemas.instruction import InstructionCreate, InstructionUpdate


class DummyResult:
    def __init__(self, scalar=None, scalars=None):
        self._scalar = scalar
        self._scalars = scalars or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        class DummyScalars:
            def __init__(self, items):
                self._items = items

            def all(self):
                return self._items

        return DummyScalars(self._scalars)


@pytest.mark.asyncio
async def test_download_document_uses_project_title_and_index(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, title="Project Test")
    doc = SimpleNamespace(
        id=uuid4(),
        title="Chapter 3",
        content="Sample content.",
        document_type=DocumentType.CHAPTER,
        order_index=0,
        word_count=2,
        document_metadata={"chapter_index": 3},
        project_id=project_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    class DummyDB:
        async def execute(self, *args, **kwargs):
            return DummyResult(scalar=project)

    class DummyDocumentService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, document_id, user_id):
            return doc

    current_user = SimpleNamespace(id=uuid4())

    monkeypatch.setattr(documents_module, "DocumentService", DummyDocumentService)

    response = await documents_module.download_document(doc.id, DummyDB(), current_user)

    assert response.headers["Content-Disposition"].endswith(
        'filename="Project-Test_chapitre_3.md"'
    )
    assert b"# Chapter 3" in response.body
    assert b"Sample content." in response.body


@pytest.mark.asyncio
async def test_download_project_creates_zip_and_handles_duplicates(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, title="Project Test")
    doc_one = SimpleNamespace(
        id=uuid4(),
        title="Chapter One",
        content="Alpha",
        document_type=DocumentType.CHAPTER,
        order_index=0,
        document_metadata={"chapter_index": 1},
    )
    doc_two = SimpleNamespace(
        id=uuid4(),
        title="Chapter One",
        content="Beta",
        document_type=DocumentType.CHAPTER,
        order_index=1,
        document_metadata={"chapter_index": 1},
    )
    doc_other = SimpleNamespace(
        id=uuid4(),
        title="Outline",
        content="Skip",
        document_type=DocumentType.OUTLINE,
        order_index=2,
        document_metadata={},
    )

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    class DummyDB:
        async def execute(self, *args, **kwargs):
            return DummyResult(scalars=[doc_one, doc_two, doc_other])

    current_user = SimpleNamespace(id=uuid4())
    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    response = await projects_module.download_project(project_id, DummyDB(), current_user)

    with zipfile.ZipFile(io.BytesIO(response.body)) as archive:
        names = sorted(archive.namelist())
        assert names == ["001-Chapter-One-2.md", "001-Chapter-One.md"]
        first_payload = archive.read("001-Chapter-One.md").decode("utf-8")
        second_payload = archive.read("001-Chapter-One-2.md").decode("utf-8")
        assert "# Chapter One" in first_payload
        assert "Alpha" in first_payload
        assert "Beta" in second_payload


@pytest.mark.asyncio
async def test_instruction_crud_flow(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, project_metadata={})
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    class DummyDB:
        def __init__(self):
            self.commits = 0
            self.refreshes = 0

        async def commit(self):
            self.commits += 1

        async def refresh(self, obj):
            self.refreshes += 1

    db = DummyDB()
    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    created = await projects_module.create_instruction(
        project_id,
        InstructionCreate(title="Rule", detail="Follow continuity."),
        db,
        current_user,
    )
    assert created.title == "Rule"
    assert db.commits == 1
    assert db.refreshes == 1

    listed = await projects_module.list_instructions(project_id, db, current_user)
    assert listed.total == 1
    assert listed.instructions[0].title == "Rule"

    updated = await projects_module.update_instruction(
        project_id,
        UUID(str(created.id)),
        InstructionUpdate(title="Rule Updated", detail=None),
        db,
        current_user,
    )
    assert updated.title == "Rule Updated"

    await projects_module.delete_instruction(
        project_id,
        UUID(str(created.id)),
        db,
        current_user,
    )
    assert project.project_metadata.get("instructions") == []


@pytest.mark.asyncio
async def test_instruction_update_missing_raises(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={"instructions": [{"id": str(uuid4()), "title": "Rule", "detail": "Keep"}]},
    )
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    class DummyDB:
        async def commit(self):
            return None

        async def refresh(self, obj):
            return None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    with pytest.raises(HTTPException):
        await projects_module.update_instruction(
            project_id,
            uuid4(),
            InstructionUpdate(title="Missing", detail=None),
            DummyDB(),
            current_user,
        )


def test_version_helpers_format_and_parse():
    assert documents_module._parse_version("v2") == (2, 0)
    assert documents_module._parse_version("v3.07") == (3, 7)
    assert documents_module._parse_version("bad") == (1, 0)
    assert documents_module._format_version(2, 0) == "v2"
    assert documents_module._format_version(2, 3) == "v2.03"


def test_get_source_content_excerpt():
    versions = [
        {
            "id": "v1",
            "version": "v1",
            "content": "A" * 3300,
        }
    ]
    excerpt, version_label = documents_module._get_source_content(versions, UUID("00000000-0000-0000-0000-000000000001"))
    assert version_label is None
    excerpt, version_label = documents_module._get_source_content(versions, UUID("00000000-0000-0000-0000-000000000000"))
    assert excerpt == ""
    assert version_label is None

    version_id = UUID("11111111-1111-1111-1111-111111111111")
    versions[0]["id"] = str(version_id)
    excerpt, version_label = documents_module._get_source_content(versions, version_id)
    assert "[...]" in excerpt
    assert version_label == "v1"


def test_serialize_version_includes_content_when_requested():
    entry = {
        "id": str(uuid4()),
        "version": "v1",
        "created_at": datetime.utcnow().isoformat(),
        "content": "Hello world",
        "word_count": "not-int",
        "min_word_count": 100,
        "max_word_count": 200,
        "summary": "Sum",
    }
    payload = documents_module._serialize_version(entry, current_version="v1", include_content=True)
    assert payload is not None
    assert payload["content"] == "Hello world"
    assert payload["is_current"] is True
    assert payload["word_count"] == 2
