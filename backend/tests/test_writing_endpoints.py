from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import writing as writing_module
from app.schemas.writing import ChapterApprovalRequest, ChapterGenerationRequest, IndexProjectRequest


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
    def __init__(self, results=None):
        self._results = list(results or [])

    async def execute(self, *args, **kwargs):
        return self._results.pop(0)


@pytest.mark.asyncio
async def test_index_project_documents_indexes(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, owner_id=uuid4())
    docs = [SimpleNamespace(id=uuid4())]
    db = DummyDB(results=[DummyResult(scalar=project), DummyResult(scalars=docs)])

    class DummyRag:
        async def aindex_documents(self, project_id, documents, clear_existing=True):
            return 3

    monkeypatch.setattr(writing_module, "RagService", lambda: DummyRag())

    result = await writing_module.index_project_documents(
        IndexProjectRequest(project_id=project_id, clear_existing=True),
        db=db,
        current_user=SimpleNamespace(id=project.owner_id),
    )

    assert result.chunks_indexed == 3


@pytest.mark.asyncio
async def test_generate_chapter_requires_plan(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=uuid4(),
        project_metadata={},
    )
    db = DummyDB(results=[DummyResult(scalar=project)])

    with pytest.raises(HTTPException):
        await writing_module.generate_chapter(
            ChapterGenerationRequest(project_id=project_id),
            db=db,
            current_user=SimpleNamespace(id=project.owner_id),
        )


@pytest.mark.asyncio
async def test_generate_chapter_requires_accepted_plan(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=uuid4(),
        project_metadata={"plan": {"data": {"chapters": []}, "status": "draft"}},
    )
    db = DummyDB(results=[DummyResult(scalar=project)])

    with pytest.raises(HTTPException):
        await writing_module.generate_chapter(
            ChapterGenerationRequest(project_id=project_id),
            db=db,
            current_user=SimpleNamespace(id=project.owner_id),
        )


@pytest.mark.asyncio
async def test_generate_chapter_missing_chapter_id(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=uuid4(),
        project_metadata={"plan": {"data": {"chapters": []}, "status": "accepted"}},
    )
    db = DummyDB(results=[DummyResult(scalar=project), DummyResult(scalar=None)])

    with pytest.raises(HTTPException):
        await writing_module.generate_chapter(
            ChapterGenerationRequest(project_id=project_id, chapter_id=uuid4()),
            db=db,
            current_user=SimpleNamespace(id=project.owner_id),
        )


@pytest.mark.asyncio
async def test_generate_chapter_maps_rewrite_focus(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=uuid4(),
        project_metadata={"plan": {"data": {"chapters": []}, "status": "accepted"}},
    )
    db = DummyDB(results=[DummyResult(scalar=project)])

    captured = {}

    class DummyPipeline:
        def __init__(self, db):
            self.db = db

        async def generate_chapter(self, state):
            captured["instruction"] = state.get("chapter_instruction")
            return {
                "chapter_title": "Title",
                "chapter_text": "Content",
                "word_count": 5,
                "critique": {
                    "score": 9,
                    "issues": ["issue"],
                    "suggestions": ["suggest"],
                    "cliffhanger_ok": True,
                    "pacing_ok": True,
                },
            }

    monkeypatch.setattr(writing_module, "WritingPipeline", DummyPipeline)

    result = await writing_module.generate_chapter(
        ChapterGenerationRequest(project_id=project_id, rewrite_focus="tension"),
        db=db,
        current_user=SimpleNamespace(id=project.owner_id),
    )

    assert captured["instruction"] == "Renforce la tension dans ce chapitre."
    assert result.critique is not None
    assert result.critique.score == 9


@pytest.mark.asyncio
async def test_approve_chapter_missing_returns_404(monkeypatch):
    class DummyPipeline:
        def __init__(self, db):
            self.db = db

        async def approve_chapter(self, document_id, user_id):
            return {}

    monkeypatch.setattr(writing_module, "WritingPipeline", DummyPipeline)

    with pytest.raises(HTTPException):
        await writing_module.approve_chapter(
            ChapterApprovalRequest(document_id=uuid4()),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )


@pytest.mark.asyncio
async def test_approve_chapter_success(monkeypatch):
    class DummyPipeline:
        def __init__(self, db):
            self.db = db

        async def approve_chapter(self, document_id, user_id):
            return {
                "document_id": document_id,
                "status": "approved",
                "summary": "Summary",
                "rag_updated": True,
                "rag_update_error": None,
            }

    monkeypatch.setattr(writing_module, "WritingPipeline", DummyPipeline)

    result = await writing_module.approve_chapter(
        ChapterApprovalRequest(document_id=uuid4()),
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result.success is True
    assert result.status == "approved"


@pytest.mark.asyncio
async def test_lazy_generate_next_success(monkeypatch):
    project_id = uuid4()
    owner_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        project_metadata={},
        generation_mode="lazy",
    )
    # First query: _verify_project_access, second: func.max(order_index)
    db = DummyDB(results=[DummyResult(scalar=project), DummyResult(scalar=0)])

    captured = {}

    class DummyPipeline:
        def __init__(self, db):
            self.db = db

        async def generate_chapter_lazy(self, **kwargs):
            captured.update(kwargs)
            return {
                "chapter_title": "Chapitre 1",
                "chapter_text": "Il etait une fois...",
                "document_id": str(uuid4()),
                "word_count": 500,
            }

    monkeypatch.setattr(writing_module, "WritingPipeline", DummyPipeline)

    from app.schemas.writing import LazyGenerationRequest

    result = await writing_module.lazy_generate_next(
        LazyGenerationRequest(project_id=project_id),
        db=db,
        current_user=SimpleNamespace(id=owner_id),
    )

    assert result.success is True
    assert result.chapter_title == "Chapitre 1"
    assert result.word_count == 500
    assert captured["chapter_index"] == 1


@pytest.mark.asyncio
async def test_lazy_generate_next_missing_document(monkeypatch):
    project_id = uuid4()
    owner_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        project_metadata={},
    )
    db = DummyDB(results=[DummyResult(scalar=project), DummyResult(scalar=0)])

    class DummyPipeline:
        def __init__(self, db):
            self.db = db

        async def generate_chapter_lazy(self, **kwargs):
            return {"chapter_title": "Titre", "chapter_text": "", "word_count": 0}

    monkeypatch.setattr(writing_module, "WritingPipeline", DummyPipeline)

    from app.schemas.writing import LazyGenerationRequest

    with pytest.raises(HTTPException) as exc_info:
        await writing_module.lazy_generate_next(
            LazyGenerationRequest(project_id=project_id),
            db=db,
            current_user=SimpleNamespace(id=owner_id),
        )
    assert exc_info.value.status_code == 500
