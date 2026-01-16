import pytest
from types import SimpleNamespace
from uuid import uuid4

from app.models.project import Genre
from app.services.novella_service import NovellaForgeService


class DummyDB:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshes = 0

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj) -> None:
        self.refreshes += 1


class DummyLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.called = False

    async def chat(self, *args, **kwargs) -> str:
        self.called = True
        return self.response


@pytest.mark.asyncio
async def test_generate_concept_respects_accepted(monkeypatch):
    project_id = uuid4()
    user_id = uuid4()
    metadata = {
        "concept": {
            "status": "accepted",
            "data": {"premise": "Keep this premise."},
            "updated_at": "2024-01-01T00:00:00",
        }
    }
    project = SimpleNamespace(
        id=project_id,
        owner_id=user_id,
        project_metadata=metadata,
        description="Existing description",
        genre=Genre.ROMANCE,
    )
    db = DummyDB()
    service = NovellaForgeService(db)
    dummy_llm = DummyLLM("{}")
    service.llm_client = dummy_llm

    async def fake_get_project(pid, uid):
        return project

    monkeypatch.setattr(service, "_get_project", fake_get_project)

    result = await service.generate_concept(project_id, user_id, force=False)

    assert result == metadata["concept"]
    assert dummy_llm.called is False


@pytest.mark.asyncio
async def test_generate_concept_sets_description(monkeypatch):
    project_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=user_id,
        project_metadata={},
        description=None,
        genre=Genre.FANTASY,
    )
    db = DummyDB()
    service = NovellaForgeService(db)
    service.llm_client = DummyLLM(
        '{"premise":"A new premise","tone":"dark","tropes":["x"],"emotional_orientation":"intense"}'
    )

    async def fake_get_project(pid, uid):
        return project

    monkeypatch.setattr(service, "_get_project", fake_get_project)

    result = await service.generate_concept(project_id, user_id, force=False)

    assert result["status"] == "draft"
    assert project.project_metadata["concept"]["data"]["premise"] == "A new premise"
    assert project.description == "A new premise"
    assert db.commits == 1
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_generate_plan_normalizes_fallback(monkeypatch):
    project_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=user_id,
        project_metadata={},
        description="",
        genre=Genre.THRILLER,
        target_word_count=6000,
    )
    db = DummyDB()
    service = NovellaForgeService(db)
    service.llm_client = DummyLLM(
        '{"global_summary":"x","arcs":[{"id":"arc-1","title":"Arc 1","summary":"s","target_emotion":"tension","chapter_start":1,"chapter_end":3}],"chapters":[]}'
    )

    async def fake_get_project(pid, uid):
        return project

    monkeypatch.setattr(service, "_get_project", fake_get_project)

    result = await service.generate_plan(
        project_id, user_id, chapter_count=3, arc_count=1, regenerate=True
    )

    plan = result["data"]
    assert len(plan["chapters"]) == 3
    assert len(plan["arcs"]) == 1
    assert plan["chapters"][0]["index"] == 1
    assert plan["chapters"][0]["status"] == "planned"
    assert db.commits == 1
    assert db.refreshes == 1
