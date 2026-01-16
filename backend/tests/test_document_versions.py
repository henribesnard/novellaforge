import pytest
from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime

from app.api.v1.endpoints import documents as documents_module
from app.models.document import DocumentType
from app.schemas.document import DocumentVersionCreate, ElementGenerateRequest


class DummyDocument:
    def __init__(self, doc_id, project_id, title, content, metadata):
        self.id = doc_id
        self.project_id = project_id
        self.title = title
        self.content = content
        self.document_metadata = metadata
        self.document_type = DocumentType.CHAPTER


class DummyDocumentService:
    def __init__(self, document):
        self.document = document
        self.last_update_payload = None

    async def get_by_id(self, document_id, user_id):
        return self.document

    async def update(self, document_id, document_data, user_id):
        self.last_update_payload = document_data
        update_data = document_data.model_dump(exclude_unset=True)
        if "metadata" in update_data:
            self.document.document_metadata = update_data["metadata"]
        if "content" in update_data:
            self.document.content = update_data["content"]
        return self.document


class DummyContextService:
    def __init__(self, db):
        self.db = db

    async def build_project_context(self, project_id, user_id):
        return {
            "project": {"title": "Projet test", "genre": None, "description": ""},
            "instructions": [],
            "characters": [],
            "documents": [],
            "constraints": {},
        }


class DummyDeepSeekClient:
    async def chat(self, messages, temperature=0.7, max_tokens=2000, model=None):
        return "Texte genere pour le chapitre."


@pytest.mark.asyncio
async def test_manual_edit_creates_version(monkeypatch):
    doc_id = uuid4()
    project_id = uuid4()
    source_version_id = uuid4()
    metadata = {
        "versions": [
            {
                "id": str(source_version_id),
                "version": "v1",
                "created_at": datetime.utcnow().isoformat(),
                "content": "Contenu initial",
                "word_count": 2,
            }
        ],
        "current_version": "v1",
    }
    document = DummyDocument(doc_id, project_id, "Chapitre 1", "Contenu initial", metadata)
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)

    payload = DocumentVersionCreate(content="Contenu corrige")
    user = SimpleNamespace(id=uuid4())

    await documents_module.create_document_version(doc_id, payload, db=None, current_user=user)

    updated_metadata = document.document_metadata
    assert updated_metadata["current_version"] == "v1.01"
    latest_version = updated_metadata["versions"][-1]
    assert latest_version["source_type"] == "manual_edit"
    assert latest_version["source_version_id"] == str(source_version_id)


@pytest.mark.asyncio
async def test_generate_element_applies_selected_comment(monkeypatch):
    doc_id = uuid4()
    project_id = uuid4()
    source_version_id = uuid4()
    comment_id = uuid4()
    other_comment_id = uuid4()
    metadata = {
        "versions": [
            {
                "id": str(source_version_id),
                "version": "v1",
                "created_at": datetime.utcnow().isoformat(),
                "content": "Version source",
                "word_count": 2,
            }
        ],
        "current_version": "v1",
        "comments": [
            {
                "id": str(comment_id),
                "content": "Corriger cette phrase.",
                "created_at": datetime.utcnow().isoformat(),
                "user_id": str(uuid4()),
                "version_id": str(source_version_id),
                "applied_version_ids": [],
            },
            {
                "id": str(other_comment_id),
                "content": "Autre remarque.",
                "created_at": datetime.utcnow().isoformat(),
                "user_id": str(uuid4()),
                "version_id": str(source_version_id),
                "applied_version_ids": [],
            },
        ],
    }
    document = DummyDocument(doc_id, project_id, "Chapitre 1", "Version source", metadata)
    service = DummyDocumentService(document)
    monkeypatch.setattr(documents_module, "DocumentService", lambda db: service)
    monkeypatch.setattr(documents_module, "ProjectContextService", DummyContextService)
    monkeypatch.setattr(documents_module, "DeepSeekClient", DummyDeepSeekClient)

    payload = ElementGenerateRequest(
        source_version_id=source_version_id,
        comment_ids=[comment_id],
    )
    user = SimpleNamespace(id=uuid4())

    await documents_module.generate_element(doc_id, payload, db=None, current_user=user)

    updated_metadata = document.document_metadata
    latest_version = updated_metadata["versions"][-1]
    assert latest_version["source_comment_ids"] == [str(comment_id)]
    comment_entry = next(item for item in updated_metadata["comments"] if item["id"] == str(comment_id))
    assert latest_version["id"] in comment_entry["applied_version_ids"]
    other_entry = next(item for item in updated_metadata["comments"] if item["id"] == str(other_comment_id))
    assert other_entry["applied_version_ids"] == []
