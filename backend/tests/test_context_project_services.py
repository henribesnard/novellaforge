from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.document import DocumentType
from app.models.project import ProjectStatus
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.context_service import ProjectContextService
from app.services.project_service import ProjectService


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

    def scalar(self):
        return self._scalar

    def scalars(self):
        return DummyScalars(self._scalars)


class DummyDB:
    def __init__(self, results=None):
        self._results = list(results or [])
        self.added = []
        self.commits = 0
        self.refreshes = 0
        self.deleted = []

    async def execute(self, *args, **kwargs):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshes += 1

    async def delete(self, obj):
        self.deleted.append(obj)


@pytest.mark.asyncio
async def test_build_project_context_includes_metadata_and_instructions():
    project_id = uuid4()
    user_id = uuid4()
    project_metadata = {
        "concept": {"data": {"premise": "Une premise claire"}},
        "plan": {"data": {"global_summary": "Synopsis global"}},
        "continuity": {"characters": []},
        "recent_chapter_summaries": ["Resume 1"],
        "story_bible": {
            "world_rules": [{"rule": "No magic", "importance": "critical"}]
        },
        "instructions": [
            {
                "id": str(uuid4()),
                "title": "Regle",
                "detail": "Toujours respecter la chronologie.",
                "created_at": "2024-01-02T00:00:00",
            },
            {"title": "", "detail": "ignore"},
        ],
        "constraints": {"max_chapters": 30},
    }
    project = SimpleNamespace(
        id=project_id,
        owner_id=user_id,
        title="Projet test",
        description="Desc",
        genre="fantasy",
        status=ProjectStatus.DRAFT,
        target_word_count=10000,
        current_word_count=1200,
        structure_template="3-act",
        project_metadata=project_metadata,
    )
    document = SimpleNamespace(
        id=uuid4(),
        title="Chapitre 1",
        document_type=DocumentType.CHAPTER,
        order_index=0,
        word_count=900,
        document_metadata={"chapter_index": 1},
        content="abcdefg",
    )
    character = SimpleNamespace(
        id=uuid4(),
        name="Alice",
        role="hero",
        description="Brave",
        personality="Courageuse",
        backstory="Origines mysterieuses",
        character_metadata={"role": "hero"},
    )

    results = [
        DummyResult(scalar=project),
        DummyResult(scalars=[document]),
        DummyResult(scalars=[character]),
    ]
    db = DummyDB(results)
    service = ProjectContextService(db)

    context = await service.build_project_context(
        project_id=project_id,
        user_id=user_id,
        document_preview_chars=5,
    )

    assert context["project"]["concept"] == {"premise": "Une premise claire"}
    assert context["project"]["plan"] == {"global_summary": "Synopsis global"}
    assert context["project"]["continuity"] == {"characters": []}
    assert context["project"]["recent_chapter_summaries"] == ["Resume 1"]
    assert context["story_bible"]["world_rules"][0]["rule"] == "No magic"
    assert context["constraints"] == {"max_chapters": 30}
    assert len(context["instructions"]) == 1
    assert context["instructions"][0]["title"] == "Regle"
    assert context["documents"][0]["content_preview"] == "abcde"
    assert context["documents"][0]["document_type"] == DocumentType.CHAPTER.value


@pytest.mark.asyncio
async def test_build_project_context_raises_on_missing_project():
    db = DummyDB([DummyResult(scalar=None)])
    service = ProjectContextService(db)

    with pytest.raises(HTTPException):
        await service.build_project_context(project_id=uuid4(), user_id=uuid4())


@pytest.mark.asyncio
async def test_project_service_create_sets_defaults():
    db = DummyDB()
    service = ProjectService(db)
    payload = ProjectCreate(genre="fantasy", title=None, description="Desc")

    project = await service.create(payload, user_id=uuid4())

    assert project.title == "Projet fantasy sans titre"
    assert project.target_word_count == 200000
    assert project.project_metadata["continuity"] == {}
    assert project.project_metadata["recent_chapter_summaries"] == []
    assert project.project_metadata["chapter_word_range"]["min"] == settings.CHAPTER_MIN_WORDS
    assert project.project_metadata["chapter_word_range"]["max"] == settings.CHAPTER_MAX_WORDS
    assert db.commits == 1
    assert db.refreshes == 1
    assert db.added


@pytest.mark.asyncio
async def test_build_project_context_handles_flat_concept_and_plan():
    project_id = uuid4()
    user_id = uuid4()
    project_metadata = {
        "concept": {
            "premise": "Premise",
            "tone": "Tone",
            "tropes": ["one"],
            "emotional_orientation": "mood",
        },
        "plan": {
            "global_summary": "Summary",
            "arcs": [],
            "chapters": [],
        },
        "instructions": ["bad", {"title": "Rule", "detail": "Keep"}],
    }
    project = SimpleNamespace(
        id=project_id,
        owner_id=user_id,
        title="Project",
        description="Desc",
        genre="fantasy",
        status=ProjectStatus.DRAFT,
        target_word_count=10000,
        current_word_count=1200,
        structure_template=None,
        project_metadata=project_metadata,
    )

    results = [
        DummyResult(scalar=project),
        DummyResult(scalars=[]),
        DummyResult(scalars=[]),
    ]
    db = DummyDB(results)
    service = ProjectContextService(db)

    context = await service.build_project_context(
        project_id=project_id,
        user_id=user_id,
        document_preview_chars=5,
    )

    assert context["project"]["concept"]["premise"] == "Premise"
    assert context["project"]["plan"]["global_summary"] == "Summary"
    assert len(context["instructions"]) == 1


@pytest.mark.asyncio
async def test_build_project_context_handles_non_dict_metadata():
    project_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=user_id,
        title="Project",
        description="Desc",
        genre="fantasy",
        status=ProjectStatus.DRAFT,
        target_word_count=10000,
        current_word_count=1200,
        structure_template=None,
        project_metadata="invalid",
    )

    results = [
        DummyResult(scalar=project),
        DummyResult(scalars=[]),
        DummyResult(scalars=[]),
    ]
    db = DummyDB(results)
    service = ProjectContextService(db)

    context = await service.build_project_context(
        project_id=project_id,
        user_id=user_id,
        document_preview_chars=5,
    )

    assert context["project"]["concept"] is None
    assert context["project"]["plan"] is None
    assert context["project"]["continuity"] == {}
    assert context["project"]["recent_chapter_summaries"] == []


@pytest.mark.asyncio
async def test_project_service_update_applies_metadata(monkeypatch):
    db = DummyDB()
    service = ProjectService(db)
    project = SimpleNamespace(
        id=uuid4(),
        owner_id=uuid4(),
        title="Ancien",
        description="",
        genre="romance",
        status=ProjectStatus.DRAFT,
        target_word_count=5000,
        current_word_count=120,
        structure_template=None,
        project_metadata={"continuity": {"characters": []}},
    )

    async def fake_get_by_id(project_id, user_id):
        return project

    monkeypatch.setattr(service, "get_by_id", fake_get_by_id)
    update_payload = ProjectUpdate(
        title="Nouveau",
        current_word_count=250,
        project_metadata={"continuity": {"updated_at": "2024-01-03T00:00:00"}},
    )

    updated = await service.update(project.id, update_payload, user_id=project.owner_id)

    assert updated.title == "Nouveau"
    assert updated.current_word_count == 250
    assert updated.project_metadata == {"continuity": {"updated_at": "2024-01-03T00:00:00"}}
    assert db.commits == 1
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_project_service_delete_returns_true(monkeypatch):
    db = DummyDB()
    service = ProjectService(db)
    project = SimpleNamespace(id=uuid4(), owner_id=uuid4())

    async def fake_get_by_id(project_id, user_id):
        return project

    monkeypatch.setattr(service, "get_by_id", fake_get_by_id)

    deleted = await service.delete(project.id, project.owner_id)

    assert deleted is True
    assert db.deleted == [project]
    assert db.commits == 1
