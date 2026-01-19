from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.v1.endpoints import agents as agents_module
from app.schemas.agents import (
    ConsistencyChapterRequest,
    ConsistencyProjectRequest,
    ConsistencyFixesRequest,
)


class DummyAgent:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, task_data, context):
        self.calls.append((task_data, context))
        return {"success": True, "payload": task_data}


@pytest.mark.asyncio
async def test_analyze_chapter_consistency_uses_agent_and_context(monkeypatch):
    dummy_agent = DummyAgent()
    context = {"project": {"metadata": {}}, "story_bible": {}, "documents": []}

    async def fake_context(db, project_id, user_id):
        return context

    monkeypatch.setattr(agents_module.AgentFactory, "create_agent", lambda *_: dummy_agent)
    monkeypatch.setattr(agents_module, "_load_project_context", fake_context)

    request = ConsistencyChapterRequest(chapter_text="Texte", project_id=uuid4())
    result = await agents_module.analyze_chapter_consistency(
        request,
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result["success"] is True
    assert dummy_agent.calls[0][0]["action"] == "analyze_chapter"
    assert dummy_agent.calls[0][1] == context


@pytest.mark.asyncio
async def test_analyze_project_consistency_uses_agent(monkeypatch):
    dummy_agent = DummyAgent()
    context = {"project": {"metadata": {}}, "story_bible": {}, "documents": []}

    async def fake_context(db, project_id, user_id):
        return context

    monkeypatch.setattr(agents_module.AgentFactory, "create_agent", lambda *_: dummy_agent)
    monkeypatch.setattr(agents_module, "_load_project_context", fake_context)

    request = ConsistencyProjectRequest(project_id=uuid4())
    result = await agents_module.analyze_project_consistency(
        request,
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result["success"] is True
    assert dummy_agent.calls[0][0]["action"] == "analyze_project"


@pytest.mark.asyncio
async def test_suggest_consistency_fixes(monkeypatch):
    dummy_agent = DummyAgent()

    monkeypatch.setattr(agents_module.AgentFactory, "create_agent", lambda *_: dummy_agent)

    request = ConsistencyFixesRequest(chapter_text="Texte", issues=[{"description": "Issue"}])
    result = await agents_module.suggest_consistency_fixes(
        request,
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result["success"] is True
    assert dummy_agent.calls[0][0]["action"] == "suggest_fixes"
