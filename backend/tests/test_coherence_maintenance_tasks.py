from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.tasks import coherence_maintenance as tasks_module


class DummyScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class DummyResult:
    def __init__(self, scalars=None):
        self._scalars = scalars or []

    def scalars(self):
        return DummyScalars(self._scalars)


class DummySession:
    def __init__(self, results=None, projects=None):
        self._results = list(results or [])
        self._projects = projects or {}
        self.commits = 0
        self.deleted = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def execute(self, *args, **kwargs):
        return self._results.pop(0)

    async def get(self, model, key):
        return self._projects.get(key)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.commits += 1


class DummyMemoryService:
    async def extract_facts(self, chapter_text):
        return {
            "summary": "",
            "characters": [{"name": chapter_text, "status": "alive"}],
            "locations": [],
            "relations": [],
            "events": [],
        }

    def merge_facts(self, metadata, facts):
        continuity = metadata.get("continuity") if isinstance(metadata, dict) else None
        if not isinstance(continuity, dict):
            continuity = {
                "characters": [],
                "locations": [],
                "relations": [],
                "events": [],
            }
        continuity["characters"] = [*continuity.get("characters", []), *facts.get("characters", [])]
        metadata["continuity"] = continuity
        return metadata


class DummyRagService:
    def __init__(self):
        self.calls = []

    async def aindex_documents(self, project_id, documents, clear_existing=True):
        self.calls.append((project_id, documents, clear_existing))
        return 12


@pytest.mark.asyncio
async def test_reconcile_project_memory_updates_metadata(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={"continuity": {"characters": [{"name": "Alice", "status": "alive"}]}},
    )
    docs = [
        SimpleNamespace(content=f"Char-{idx}", document_metadata={"status": "approved"})
        for idx in range(6)
    ]
    session = DummySession(results=[DummyResult(scalars=docs)], projects={project_id: project})

    monkeypatch.setattr(tasks_module, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(tasks_module, "MemoryService", DummyMemoryService)

    result = await tasks_module._reconcile_project_memory(str(project_id))

    assert result["updated"] is True
    assert result["chapters_processed"] == 6
    assert "last_reconciliation" in project.project_metadata
    assert session.commits == 1


@pytest.mark.asyncio
async def test_rebuild_project_rag_indexes_documents(monkeypatch):
    project_id = uuid4()
    docs = [SimpleNamespace(id=uuid4(), content="text")]
    session = DummySession(results=[DummyResult(scalars=docs)])
    rag_service = DummyRagService()

    monkeypatch.setattr(tasks_module, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(tasks_module, "RagService", lambda: rag_service)

    result = await tasks_module._rebuild_project_rag(str(project_id))

    assert result["reindexed"] is True
    assert result["chunks_count"] == 12
    assert rag_service.calls
    call_project_id, call_docs, clear_existing = rag_service.calls[0]
    assert call_project_id == project_id
    assert call_docs == docs
    assert clear_existing is True


@pytest.mark.asyncio
async def test_cleanup_old_drafts_deletes_only_drafts(monkeypatch):
    project_id = uuid4()
    cutoff = datetime.utcnow() - timedelta(days=40)
    old_draft = SimpleNamespace(
        document_metadata={"status": "draft"},
        created_at=cutoff,
    )
    old_approved = SimpleNamespace(
        document_metadata={"status": "approved"},
        created_at=cutoff,
    )
    session = DummySession(results=[DummyResult(scalars=[old_draft, old_approved])])

    monkeypatch.setattr(tasks_module, "AsyncSessionLocal", lambda: session)

    result = await tasks_module._cleanup_old_drafts(str(project_id), days_threshold=30)

    assert result["deleted_drafts"] == 1
    assert session.deleted == [old_draft]
    assert session.commits == 1
