from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.rag_service as rag_service
from app.models.document import DocumentType
from app.services.rag_service import RagService


def test_update_document_reindexes_chunks(monkeypatch):
    calls = {}

    class DummySplitter:
        def split_text(self, text):
            return [text[:5], text[5:]]

    class DummyVectorStore:
        def __init__(self, client, collection_name, embeddings):
            self.client = client
            self.collection_name = collection_name
            self.embeddings = embeddings

        def add_texts(self, texts, metadatas):
            calls["texts"] = texts
            calls["metadatas"] = metadatas

    def record_delete(project_id, document_id):
        calls["deleted_project_id"] = project_id
        calls["deleted_document_id"] = document_id

    monkeypatch.setattr(rag_service, "Qdrant", DummyVectorStore)

    service = RagService.__new__(RagService)
    service.client = object()
    service.collection_name = "test"
    service.embeddings = object()
    service.text_splitter = DummySplitter()
    service._ensure_collection = lambda: None
    service._delete_document_vectors = record_delete

    project_id = uuid4()
    document_id = uuid4()
    doc = SimpleNamespace(
        id=document_id,
        content="hello world",
        title="Doc",
        order_index=2,
        document_type=DocumentType.CHAPTER,
    )

    count = service.update_document(project_id, doc)

    assert count == 2
    assert calls["deleted_project_id"] == project_id
    assert calls["deleted_document_id"] == document_id
    assert calls["texts"] == ["hello", " world"]
    assert calls["metadatas"][0]["project_id"] == str(project_id)
    assert calls["metadatas"][0]["document_id"] == str(document_id)


def test_update_document_handles_empty_content(monkeypatch):
    class DummySplitter:
        def split_text(self, text):
            return ["unused"]

    class DummyVectorStore:
        def __init__(self, client, collection_name, embeddings):
            raise AssertionError("Vector store should not be created for empty content")

    monkeypatch.setattr(rag_service, "Qdrant", DummyVectorStore)

    service = RagService.__new__(RagService)
    service.client = object()
    service.collection_name = "test"
    service.embeddings = object()
    service.text_splitter = DummySplitter()
    service._ensure_collection = lambda: None
    service._delete_document_vectors = lambda project_id, document_id: None

    project_id = uuid4()
    doc = SimpleNamespace(
        id=uuid4(),
        content="",
        title="Doc",
        order_index=0,
        document_type=DocumentType.CHAPTER,
    )

    assert service.update_document(project_id, doc) == 0


def test_count_project_vectors_uses_filter(monkeypatch):
    calls = {}

    class DummyCountResult:
        def __init__(self, count):
            self.count = count

    class DummyClient:
        def count(self, collection_name, count_filter, exact):
            calls["collection_name"] = collection_name
            calls["count_filter"] = count_filter
            calls["exact"] = exact
            return DummyCountResult(42)

        def collection_exists(self, collection_name):
            return True

    service = RagService.__new__(RagService)
    service.client = DummyClient()
    service.collection_name = "test"
    service._ensure_collection = lambda: None

    count = service.count_project_vectors(uuid4())

    assert count == 42
    assert calls["collection_name"] == "test"
    assert calls["exact"] is True


def test_ensure_collection_creates_when_missing():
    calls = {}

    class DummyClient:
        def collection_exists(self, collection_name):
            return False

        def create_collection(self, collection_name, vectors_config):
            calls["collection_name"] = collection_name
            calls["vectors_config"] = vectors_config

    service = RagService.__new__(RagService)
    service.client = DummyClient()
    service.collection_name = "test"

    service._ensure_collection()

    assert calls["collection_name"] == "test"
    assert calls["vectors_config"] is not None


def test_delete_project_vectors_builds_filter():
    calls = {}

    class DummyClient:
        def delete(self, collection_name, points_selector):
            calls["collection_name"] = collection_name
            calls["points_selector"] = points_selector

    service = RagService.__new__(RagService)
    service.client = DummyClient()
    service.collection_name = "test"

    project_id = uuid4()
    service._delete_project_vectors(project_id)

    assert calls["collection_name"] == "test"
    assert calls["points_selector"].must[0].key == "project_id"
    assert calls["points_selector"].must[0].match.value == str(project_id)


def test_delete_document_vectors_builds_filter():
    calls = {}

    class DummyClient:
        def delete(self, collection_name, points_selector):
            calls["collection_name"] = collection_name
            calls["points_selector"] = points_selector

    service = RagService.__new__(RagService)
    service.client = DummyClient()
    service.collection_name = "test"

    project_id = uuid4()
    document_id = uuid4()
    service._delete_document_vectors(project_id, document_id)

    keys = {cond.key for cond in calls["points_selector"].must}
    assert calls["collection_name"] == "test"
    assert keys == {"project_id", "document_id"}


def test_index_documents_adds_texts(monkeypatch):
    calls = {}

    class DummySplitter:
        def split_text(self, text):
            return [text[:5], text[5:]]

    class DummyVectorStore:
        def __init__(self, client, collection_name, embeddings):
            self.client = client
            self.collection_name = collection_name
            self.embeddings = embeddings

        def add_texts(self, texts, metadatas):
            calls["texts"] = texts
            calls["metadatas"] = metadatas

    monkeypatch.setattr(rag_service, "Qdrant", DummyVectorStore)

    service = RagService.__new__(RagService)
    service.client = object()
    service.collection_name = "test"
    service.embeddings = object()
    service.text_splitter = DummySplitter()
    service._ensure_collection = lambda: None
    service._delete_project_vectors = lambda project_id: calls.setdefault("deleted", project_id)

    project_id = uuid4()
    docs = [
        SimpleNamespace(
            id=uuid4(),
            content="hello world",
            title="Doc",
            order_index=1,
            document_type=DocumentType.CHAPTER,
        ),
        SimpleNamespace(
            id=uuid4(),
            content="",
            title="Empty",
            order_index=2,
            document_type=DocumentType.NOTE,
        ),
    ]

    count = service.index_documents(project_id, docs, clear_existing=True)

    assert count == 2
    assert calls["deleted"] == project_id
    assert calls["texts"] == ["hello", " world"]
    assert calls["metadatas"][0]["project_id"] == str(project_id)
    assert calls["metadatas"][0]["document_type"] == DocumentType.CHAPTER.value


def test_retrieve_returns_page_content(monkeypatch):
    calls = {}

    class DummyVectorStore:
        def __init__(self, client, collection_name, embeddings):
            self.client = client
            self.collection_name = collection_name
            self.embeddings = embeddings

        def similarity_search(self, query, k, filter):
            calls["query"] = query
            calls["k"] = k
            calls["filter"] = filter
            return [
                SimpleNamespace(page_content="one"),
                SimpleNamespace(page_content="two"),
            ]

    monkeypatch.setattr(rag_service, "Qdrant", DummyVectorStore)

    service = RagService.__new__(RagService)
    service.client = object()
    service.collection_name = "test"
    service.embeddings = object()
    service._ensure_collection = lambda: None

    project_id = uuid4()
    result = service.retrieve(project_id, "query", top_k=2)

    assert result == ["one", "two"]
    assert calls["k"] == 2


@pytest.mark.asyncio
async def test_aupdate_document_calls_sync(monkeypatch):
    called = {}

    def fake_update(project_id, document):
        called["project_id"] = project_id
        called["document_id"] = document.id
        return 3

    service = RagService.__new__(RagService)
    service.update_document = fake_update

    project_id = uuid4()
    doc = SimpleNamespace(id=uuid4())

    result = await service.aupdate_document(project_id, doc)

    assert result == 3
    assert called["project_id"] == project_id
    assert called["document_id"] == doc.id


@pytest.mark.asyncio
async def test_acount_project_vectors_calls_sync():
    called = {}

    def fake_count(project_id):
        called["project_id"] = project_id
        return 9

    service = RagService.__new__(RagService)
    service.count_project_vectors = fake_count

    project_id = uuid4()
    result = await service.acount_project_vectors(project_id)

    assert result == 9
    assert called["project_id"] == project_id
