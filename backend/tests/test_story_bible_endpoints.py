from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.v1.endpoints import projects as projects_module
from app.schemas.story_bible import (
    GlossaryFaction,
    GlossaryPlace,
    GlossaryTerm,
    StoryBibleDraftValidationRequest,
    StoryBibleGlossary,
    TimelineEvent,
    WorldRule,
)


class DummyDB:
    def __init__(self):
        self.commits = 0
        self.refreshes = 0

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshes += 1


@pytest.mark.asyncio
async def test_get_story_bible_returns_schema(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={"story_bible": {"world_rules": [{"rule": "No magic"}]}},
    )

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            return project if pid == project_id else None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    result = await projects_module.get_story_bible(
        project_id,
        db=DummyDB(),
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result.world_rules[0].rule == "No magic"


@pytest.mark.asyncio
async def test_update_world_rules_updates_metadata(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, project_metadata={})

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            return project if pid == project_id else None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    result = await projects_module.update_world_rules(
        project_id,
        [WorldRule(category="magic", rule="No magic in forest")],
        db=DummyDB(),
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result["rules_count"] == 1
    assert project.project_metadata["story_bible"]["world_rules"][0]["rule"] == "No magic in forest"


@pytest.mark.asyncio
async def test_update_timeline_updates_metadata(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, project_metadata={})

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            return project if pid == project_id else None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    result = await projects_module.update_timeline(
        project_id,
        [TimelineEvent(event="Battle", chapter_index=2)],
        db=DummyDB(),
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result["events_count"] == 1
    assert project.project_metadata["story_bible"]["timeline"][0]["event"] == "Battle"


@pytest.mark.asyncio
async def test_update_glossary_updates_metadata(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, project_metadata={})

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            return project if pid == project_id else None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    glossary = StoryBibleGlossary(
        terms=[GlossaryTerm(term="Blade", definition="Ancient blade")],
        places=[GlossaryPlace(name="Forest", description="Dark")],
        factions=[GlossaryFaction(name="Guard", description="Royal guard")],
    )
    result = await projects_module.update_glossary(
        project_id,
        glossary,
        db=DummyDB(),
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result["term_count"] == 1
    assert project.project_metadata["story_bible"]["glossary"]["terms"][0]["term"] == "Blade"


@pytest.mark.asyncio
async def test_validate_draft_against_bible(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={
            "story_bible": {
                "world_rules": [{"rule": "No magic", "importance": "critical"}]
            }
        },
    )

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            return project if pid == project_id else None

    class DummyLLM:
        async def chat(self, *args, **kwargs):
            return (
                '{"violations":[{"type":"rule_violation","detail":"Magic used","severity":"blocking"}],'
                '"blocking":true,"summary":"Violation found"}'
            )

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)
    monkeypatch.setattr(projects_module, "DeepSeekClient", lambda: DummyLLM())

    result = await projects_module.validate_draft_against_bible(
        project_id,
        StoryBibleDraftValidationRequest(draft_text="Magic sparks."),
        db=DummyDB(),
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result.blocking is True
    assert result.violations[0].detail == "Magic used"
