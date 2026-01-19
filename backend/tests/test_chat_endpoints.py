from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import chat as chat_module
from app.schemas.chat import ChatMessageCreate


class DummyChatService:
    def __init__(self, db):
        self.db = db
        self.response = None
        self.history = None
        self.error = None

    async def send_message(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.response

    async def get_history(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.history


@pytest.mark.asyncio
async def test_send_chat_message_returns_response(monkeypatch):
    service = DummyChatService(db=None)
    service.response = {"response": "ok", "message_id": "1"}

    monkeypatch.setattr(chat_module, "ChatService", lambda db: service)

    result = await chat_module.send_chat_message(
        data=ChatMessageCreate(message="Hello", project_id=None),
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result == service.response


@pytest.mark.asyncio
async def test_send_chat_message_wraps_errors(monkeypatch):
    service = DummyChatService(db=None)
    service.error = RuntimeError("boom")

    monkeypatch.setattr(chat_module, "ChatService", lambda db: service)

    with pytest.raises(HTTPException) as excinfo:
        await chat_module.send_chat_message(
            data=ChatMessageCreate(message="Hello", project_id=None),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )

    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_get_chat_history_returns_messages(monkeypatch):
    service = DummyChatService(db=None)
    service.history = [
        SimpleNamespace(
            id=uuid4(),
            role="assistant",
            content="Hello",
            created_at="2024-01-01T00:00:00",
        )
    ]

    monkeypatch.setattr(chat_module, "ChatService", lambda db: service)

    result = await chat_module.get_chat_history(
        project_id=None,
        limit=10,
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result.total == 1
    assert result.messages[0].content == "Hello"


@pytest.mark.asyncio
async def test_get_chat_history_wraps_errors(monkeypatch):
    service = DummyChatService(db=None)
    service.error = RuntimeError("boom")

    monkeypatch.setattr(chat_module, "ChatService", lambda db: service)

    with pytest.raises(HTTPException) as excinfo:
        await chat_module.get_chat_history(
            project_id=None,
            limit=10,
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )

    assert excinfo.value.status_code == 500
