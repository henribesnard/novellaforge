import pytest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.models.project import Genre
from app.core.config import settings
from app.services.novella_service import NovellaForgeService


class DummyDB:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshes = 0

    async def execute(self, *args, **kwargs):
        class DummyResult:
            def fetchall(self):
                return []

        return DummyResult()

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
        project_metadata={
            "concept": {
                "status": "accepted",
                "data": {
                    "premise": "A gritty thriller premise",
                    "tone": "dark",
                    "tropes": ["conspiracy"],
                    "emotional_orientation": "tension",
                },
                "updated_at": "2024-01-01T00:00:00",
            }
        },
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


@pytest.mark.asyncio
async def test_generate_plan_includes_plot_constraints(monkeypatch):
    project_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=user_id,
        project_metadata={
            "concept": {
                "status": "accepted",
                "data": {
                    "premise": "A gritty thriller premise",
                    "tone": "dark",
                    "tropes": ["conspiracy"],
                    "emotional_orientation": "tension",
                },
                "updated_at": "2024-01-01T00:00:00",
            }
        },
        description="",
        genre=Genre.THRILLER,
        target_word_count=6000,
    )
    db = DummyDB()
    service = NovellaForgeService(db)
    service.llm_client = DummyLLM(
        '{"global_summary":"x","arcs":[{"id":"arc-1","title":"Arc 1","summary":"s","target_emotion":"tension","chapter_start":1,"chapter_end":1}],'
        '"chapters":[{"index":1,"title":"Ch1","summary":"S","emotional_stake":"high","arc_id":"arc-1",'
        '"cliffhanger_type":"revelation","required_plot_points":"Reveal, Secret",'
        '"optional_subplots":["Side"],"arc_constraints":"Keep tension",'
        '"forbidden_actions":["No death"],"success_criteria":"Shock"}]}'
    )

    async def fake_get_project(pid, uid):
        return project

    monkeypatch.setattr(service, "_get_project", fake_get_project)

    result = await service.generate_plan(
        project_id, user_id, chapter_count=1, arc_count=1, regenerate=True
    )

    chapter = result["data"]["chapters"][0]
    assert chapter["required_plot_points"] == ["Reveal", "Secret"]
    assert chapter["forbidden_actions"] == ["No death"]
    assert chapter["success_criteria"] == "Shock"


@pytest.mark.asyncio
async def test_generate_synopsis_rejects_unaccepted_concept(monkeypatch):
    project_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=user_id,
        project_metadata={"concept": {"status": "draft", "data": {}}},
    )
    service = NovellaForgeService(DummyDB())

    async def fake_get_project(pid, uid):
        return project

    monkeypatch.setattr(service, "_get_project", fake_get_project)

    with pytest.raises(HTTPException) as excinfo:
        await service.generate_synopsis(project_id, user_id)

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_generate_synopsis_uses_fallback_on_invalid_json(monkeypatch):
    project_id = uuid4()
    user_id = uuid4()
    concept = {"premise": "Premise", "tone": "tone", "tropes": [], "emotional_orientation": "x"}
    project = SimpleNamespace(
        id=project_id,
        owner_id=user_id,
        project_metadata={"concept": {"status": "accepted", "data": concept}},
    )
    db = DummyDB()
    service = NovellaForgeService(db)
    service.llm_client = DummyLLM("not-json")

    async def fake_get_project(pid, uid):
        return project

    monkeypatch.setattr(service, "_get_project", fake_get_project)

    result = await service.generate_synopsis(project_id, user_id)

    assert result["status"] == "draft"
    assert "synopsis" in project.project_metadata
    assert db.commits == 1
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_accept_concept_updates_project(monkeypatch):
    project_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=user_id,
        project_metadata=None,
        description=None,
        title=None,
    )
    db = DummyDB()
    service = NovellaForgeService(db)

    async def fake_get_project(pid, uid):
        return project

    monkeypatch.setattr(service, "_get_project", fake_get_project)

    concept = {"premise": "Premise", "title": "Title"}
    result = await service.accept_concept(project_id, user_id, concept)

    assert result["status"] == "accepted"
    assert project.description == "Premise"
    assert project.title == "Title"
    assert db.commits == 1
    assert db.refreshes == 1


def test_chapter_word_range_defaults_and_bounds():
    service = NovellaForgeService(DummyDB())
    metadata = {"chapter_word_range": {"min": -5, "max": 999999}}

    assert service._get_chapter_min(metadata) == settings.CHAPTER_MIN_WORDS
    assert service._get_chapter_max(metadata) == settings.CHAPTER_MAX_WORDS

    valid = {
        "chapter_word_range": {
            "min": settings.CHAPTER_MIN_WORDS + 10,
            "max": settings.CHAPTER_MAX_WORDS - 10,
        }
    }
    assert service._get_chapter_min(valid) == settings.CHAPTER_MIN_WORDS + 10
    assert service._get_chapter_max(valid) == settings.CHAPTER_MAX_WORDS - 10
