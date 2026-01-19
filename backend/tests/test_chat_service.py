from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.chat import MessageRole
from app.models.document import DocumentType
from app.models.project import Genre, ProjectStatus
from app.services.chat_service import ChatService


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

    def scalars(self):
        return DummyScalars(self._scalars)


class DummyDB:
    def __init__(self, results=None):
        self._results = list(results or [])
        self.added = []
        self.commits = 0
        self.refreshes = 0

    async def execute(self, *args, **kwargs):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshes += 1
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()


@pytest.mark.asyncio
async def test_build_project_context_returns_empty_when_missing_project():
    db = DummyDB(results=[DummyResult(scalar=None)])
    service = ChatService(db)

    context = await service._build_project_context(uuid4())

    assert context == {}


@pytest.mark.asyncio
async def test_build_project_context_includes_project_documents_characters():
    project = SimpleNamespace(
        title="Project",
        description="Desc",
        genre=Genre.FANTASY,
        status=ProjectStatus.DRAFT,
        structure_template="3-act",
        current_word_count=50,
        target_word_count=200,
    )
    doc = SimpleNamespace(
        title="Chapter 1",
        document_type=DocumentType.CHAPTER,
        word_count=10,
        content="Hello",
    )
    character = SimpleNamespace(name="Alice", role="hero", description="Brave")
    db = DummyDB(
        results=[
            DummyResult(scalar=project),
            DummyResult(scalars=[doc]),
            DummyResult(scalars=[character]),
        ]
    )
    service = ChatService(db)

    context = await service._build_project_context(uuid4())

    assert context["project"]["genre"] == Genre.FANTASY.value
    assert context["documents"][0]["content_preview"] == "Hello"
    assert context["characters"][0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_get_conversation_history_orders_oldest_first():
    msg_new = SimpleNamespace(content="new")
    msg_old = SimpleNamespace(content="old")
    db = DummyDB(results=[DummyResult(scalars=[msg_new, msg_old])])
    service = ChatService(db)

    history = await service._get_conversation_history(uuid4(), limit=2)

    assert history == [msg_old, msg_new]


def test_build_system_prompt_includes_context_details():
    service = ChatService(db=SimpleNamespace())
    context = {
        "project": {
            "title": "Project",
            "genre": "fantasy",
            "description": "Desc",
            "structure_template": "3-act",
            "word_count": 10,
            "target_word_count": 100,
        },
        "characters": [{"name": "Alice", "role": "hero", "description": ""}],
        "documents": [{"title": "Chapter 1"}],
    }

    prompt = service._build_system_prompt(context)

    assert "CONTEXTE DU PROJET ACTUEL" in prompt
    assert "PERSONNAGES" in prompt
    assert "DOCUMENTS" in prompt


@pytest.mark.asyncio
async def test_send_message_saves_messages_and_returns_response(monkeypatch):
    db = DummyDB()
    service = ChatService(db)
    user_id = uuid4()
    project_id = uuid4()

    async def fake_build_context(pid):
        return {"project": {"title": "Project"}}

    async def fake_history(uid, pid=None, limit=10):
        return [SimpleNamespace(role=MessageRole.USER, content="Earlier")]

    async def fake_call(messages, temperature=0.7):
        assert messages[0]["role"] == "system"
        return "AI response"

    monkeypatch.setattr(service, "_build_project_context", fake_build_context)
    monkeypatch.setattr(service, "_get_conversation_history", fake_history)
    monkeypatch.setattr(service, "_call_deepseek_api", fake_call)

    response = await service.send_message(user_id, "Hello", project_id=project_id)

    assert response.response == "AI response"
    assert response.project_context["project"]["title"] == "Project"
    assert db.commits == 1
    assert db.refreshes == 1
    assert len(db.added) == 2
