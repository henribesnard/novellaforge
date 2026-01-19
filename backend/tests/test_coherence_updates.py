from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.document import DocumentType
from app.schemas.document import DocumentUpdate


@pytest.mark.asyncio
async def test_update_document_refreshes_memory_and_rag(monkeypatch):
    import app.api.v1.endpoints.documents as documents_endpoint

    project_id = uuid4()
    project = SimpleNamespace(id=project_id, project_metadata={})
    doc = SimpleNamespace(
        id=uuid4(),
        title="Chapitre 1",
        content="Alice est en bonne sante.",
        document_type=DocumentType.CHAPTER,
        order_index=0,
        word_count=0,
        document_metadata={"status": "approved"},
        project_id=project_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    class DummyDB:
        def __init__(self):
            self.project = project
            self.commits = 0

        async def get(self, model, lookup_id):
            if lookup_id == project_id:
                return self.project
            return None

        async def commit(self):
            self.commits += 1

    db = DummyDB()
    current_user = SimpleNamespace(id=uuid4())

    class DummyDocumentService:
        def __init__(self, db):
            self.db = db

        async def update(self, document_id, document_data, user_id):
            if document_data.content is not None:
                doc.content = document_data.content
            if document_data.metadata is not None:
                doc.document_metadata = document_data.metadata
            if document_data.title is not None:
                doc.title = document_data.title
            return doc

    class DummyMemoryService:
        def __init__(self):
            self.extract_called = False
            self.store_called = False

        async def extract_facts(self, chapter_text):
            self.extract_called = True
            return {
                "summary": "Alice est blessee.",
                "characters": [{"name": "Alice", "status": "injured"}],
                "locations": [],
                "relations": [],
                "events": [],
            }

        def merge_facts(self, metadata, facts):
            if not isinstance(metadata, dict):
                metadata = {}
            metadata["continuity"] = {"characters": facts.get("characters", [])}
            return metadata

        def update_neo4j(self, facts, project_id=None, chapter_index=None):
            return None

        def store_style_memory(self, project_id, chapter_id, chapter_text, summary):
            self.store_called = True

    class DummyRagService:
        def __init__(self):
            self.called = False

        async def aupdate_document(self, project_id, document):
            self.called = True
            return 1

    memory_service = DummyMemoryService()
    rag_service = DummyRagService()

    monkeypatch.setattr(documents_endpoint, "DocumentService", DummyDocumentService)
    monkeypatch.setattr(documents_endpoint, "MemoryService", lambda: memory_service)
    monkeypatch.setattr(documents_endpoint, "RagService", lambda: rag_service)

    response = await documents_endpoint.update_document(
        doc.id,
        DocumentUpdate(content="Alice est gravement blessee."),
        db,
        current_user,
    )

    assert response.metadata.get("coherence_update_error") is None
    assert db.project.project_metadata.get("continuity")
    assert memory_service.extract_called is True
    assert rag_service.called is True
    assert memory_service.store_called is True


@pytest.mark.asyncio
async def test_get_coherence_health_returns_counts(monkeypatch):
    import app.api.v1.endpoints.projects as projects_endpoint

    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={"continuity": {"updated_at": "2024-01-02T00:00:00"}},
    )
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    class DummyRagService:
        def __init__(self):
            self.called = False

        async def acount_project_vectors(self, pid):
            self.called = True
            return 12

    rag_service = DummyRagService()
    db = SimpleNamespace()

    monkeypatch.setattr(projects_endpoint, "ProjectService", DummyProjectService)
    monkeypatch.setattr(projects_endpoint, "RagService", lambda: rag_service)

    result = await projects_endpoint.get_coherence_health(project_id, db, current_user)

    assert result["project_id"] == str(project_id)
    assert result["last_memory_update"] == "2024-01-02T00:00:00"
    assert result["rag_document_count"] == 12


@pytest.mark.asyncio
async def test_get_coherence_health_handles_rag_error(monkeypatch):
    import app.api.v1.endpoints.projects as projects_endpoint

    project_id = uuid4()
    project = SimpleNamespace(id=project_id, project_metadata={"continuity": {}})
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    class DummyRagService:
        async def acount_project_vectors(self, pid):
            raise RuntimeError("boom")

    db = SimpleNamespace()

    monkeypatch.setattr(projects_endpoint, "ProjectService", DummyProjectService)
    monkeypatch.setattr(projects_endpoint, "RagService", DummyRagService)

    result = await projects_endpoint.get_coherence_health(project_id, db, current_user)

    assert result["rag_document_count"] is None
    assert result["rag_error"]


@pytest.mark.asyncio
async def test_update_document_skips_coherence_when_not_approved(monkeypatch):
    import app.api.v1.endpoints.documents as documents_endpoint

    project_id = uuid4()
    doc = SimpleNamespace(
        id=uuid4(),
        title="Chapitre brouillon",
        content="Texte initial.",
        document_type=DocumentType.CHAPTER,
        order_index=0,
        word_count=0,
        document_metadata={"status": "draft"},
        project_id=project_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    class DummyDB:
        async def get(self, model, lookup_id):
            return None

        async def commit(self):
            return None

    current_user = SimpleNamespace(id=uuid4())

    class DummyDocumentService:
        def __init__(self, db):
            self.db = db

        async def update(self, document_id, document_data, user_id):
            if document_data.content is not None:
                doc.content = document_data.content
            if document_data.metadata is not None:
                doc.document_metadata = document_data.metadata
            return doc

    class DummyMemoryService:
        def __init__(self):
            self.called = False

        async def extract_facts(self, chapter_text):
            self.called = True
            return {}

    class DummyRagService:
        def __init__(self):
            self.called = False

        async def aupdate_document(self, project_id, document):
            self.called = True
            return 0

    memory_service = DummyMemoryService()
    rag_service = DummyRagService()

    monkeypatch.setattr(documents_endpoint, "DocumentService", DummyDocumentService)
    monkeypatch.setattr(documents_endpoint, "MemoryService", lambda: memory_service)
    monkeypatch.setattr(documents_endpoint, "RagService", lambda: rag_service)

    response = await documents_endpoint.update_document(
        doc.id,
        DocumentUpdate(content="Texte modifie."),
        DummyDB(),
        current_user,
    )

    assert response.metadata.get("coherence_update_error") is None
    assert memory_service.called is False
    assert rag_service.called is False


@pytest.mark.asyncio
async def test_update_document_reports_coherence_errors(monkeypatch):
    import app.api.v1.endpoints.documents as documents_endpoint

    project_id = uuid4()
    project = SimpleNamespace(id=project_id, project_metadata={})
    doc = SimpleNamespace(
        id=uuid4(),
        title="Chapitre 2",
        content="Texte initial.",
        document_type=DocumentType.CHAPTER,
        order_index=0,
        word_count=0,
        document_metadata={"status": "approved"},
        project_id=project_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    class DummyDB:
        async def get(self, model, lookup_id):
            if lookup_id == project_id:
                return project
            return None

        async def commit(self):
            return None

    current_user = SimpleNamespace(id=uuid4())

    class DummyDocumentService:
        def __init__(self, db):
            self.db = db

        async def update(self, document_id, document_data, user_id):
            if document_data.metadata is not None:
                doc.document_metadata = document_data.metadata
            if document_data.content is not None:
                doc.content = document_data.content
            return doc

    class DummyMemoryService:
        async def extract_facts(self, chapter_text):
            raise RuntimeError("memory explode")

        def merge_facts(self, metadata, facts):
            return {}

        def update_neo4j(self, facts, project_id=None, chapter_index=None):
            return None

        def store_style_memory(self, project_id, chapter_id, chapter_text, summary):
            return None

    class DummyRagService:
        async def aupdate_document(self, project_id, document):
            raise RuntimeError("rag explode")

    monkeypatch.setattr(documents_endpoint, "DocumentService", DummyDocumentService)
    monkeypatch.setattr(documents_endpoint, "MemoryService", DummyMemoryService)
    monkeypatch.setattr(documents_endpoint, "RagService", DummyRagService)

    response = await documents_endpoint.update_document(
        doc.id,
        DocumentUpdate(content="Texte modifie."),
        DummyDB(),
        current_user,
    )

    assert response.metadata.get("coherence_update_error")
