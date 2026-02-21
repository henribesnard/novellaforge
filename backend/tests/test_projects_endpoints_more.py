from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import projects as projects_module

from app.schemas.novella import (
    ArcPlan,
    ChapterPlan,
    ConceptGenerateRequest,
    ConceptPayload,
    PlanGenerateRequest,
    PlanPayload,
    PlanUpdateRequest,
)
from app.schemas.project import ProjectDeleteRequest
from app.schemas.project import ContradictionResolution, ContradictionIntentionalRequest


class DummyDB:
    def __init__(self):
        self.commits = 0
        self.refreshes = 0

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshes += 1


@pytest.mark.asyncio
async def test_delete_project_with_confirmation_mismatch(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, title="My Project")
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

        async def delete(self, pid, uid):
            return True

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    with pytest.raises(HTTPException):
        await projects_module.delete_project_with_confirmation(
            project_id,
            ProjectDeleteRequest(confirm_title="Other title"),
            db=DummyDB(),
            current_user=current_user,
        )


@pytest.mark.asyncio
async def test_delete_project_with_confirmation_success(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, title="My Project")
    current_user = SimpleNamespace(id=uuid4())
    deleted = {"called": False}

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

        async def delete(self, pid, uid):
            deleted["called"] = True
            return True

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    result = await projects_module.delete_project_with_confirmation(
        project_id,
        ProjectDeleteRequest(confirm_title="my project"),
        db=DummyDB(),
        current_user=current_user,
    )

    assert result is None
    assert deleted["called"] is True


@pytest.mark.asyncio
async def test_get_concept_returns_payload(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={
            "concept": {
                "status": "draft",
                "updated_at": "2024-01-01T00:00:00",
                "data": {
                    "title": "Title",
                    "premise": "Premise",
                    "tone": "tone",
                    "tropes": ["one"],
                    "emotional_orientation": "mood",
                },
            }
        },
    )

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    result = await projects_module.get_concept(project_id, db=None, current_user=SimpleNamespace(id=uuid4()))

    assert result.status == "draft"
    assert result.concept.premise == "Premise"


@pytest.mark.asyncio
async def test_get_concept_missing_raises(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, project_metadata={})

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    with pytest.raises(HTTPException):
        await projects_module.get_concept(project_id, db=None, current_user=SimpleNamespace(id=uuid4()))


@pytest.mark.asyncio
async def test_generate_and_accept_concept(monkeypatch):
    project_id = uuid4()
    current_user = SimpleNamespace(id=uuid4())
    entry = {
        "status": "draft",
        "updated_at": "2024-01-01T00:00:00",
        "data": {
            "title": "Title",
            "premise": "Premise",
            "tone": "tone",
            "tropes": ["one"],
            "emotional_orientation": "mood",
        },
    }
    accepted_entry = {**entry, "status": "accepted"}

    class DummyNovellaService:
        def __init__(self, db):
            self.db = db

        async def generate_concept(self, pid, uid, force=False):
            return entry

        async def accept_concept(self, pid, uid, payload):
            return accepted_entry

    monkeypatch.setattr(projects_module, "NovellaForgeService", DummyNovellaService)

    generated = await projects_module.generate_concept(
        project_id,
        ConceptGenerateRequest(force=False),
        db=None,
        current_user=current_user,
    )
    accepted = await projects_module.accept_concept(
        project_id,
        ConceptPayload(
            title="Title",
            premise="Premise",
            tone="tone",
            tropes=["one"],
            emotional_orientation="mood",
        ),
        db=None,
        current_user=current_user,
    )

    assert generated.status == "draft"
    assert accepted.status == "accepted"


@pytest.mark.asyncio
async def test_get_and_generate_plan(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={
            "plan": {
                "status": "draft",
                "updated_at": "2024-01-02T00:00:00",
                "data": {"global_summary": "Summary", "arcs": [], "chapters": []},
            }
        },
    )
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    class DummyNovellaService:
        def __init__(self, db):
            self.db = db

        async def generate_plan(self, pid, uid, chapter_count=None, arc_count=None, regenerate=False):
            return project.project_metadata["plan"]

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)
    monkeypatch.setattr(projects_module, "NovellaForgeService", DummyNovellaService)

    existing = await projects_module.get_plan(project_id, db=None, current_user=current_user)
    generated = await projects_module.generate_plan(
        project_id,
        PlanGenerateRequest(chapter_count=1, arc_count=1, regenerate=False),
        db=None,
        current_user=current_user,
    )

    assert existing.status == "draft"
    assert generated.plan.global_summary == "Summary"


@pytest.mark.asyncio
async def test_accept_plan_wraps_legacy_format(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={"plan": {"global_summary": "Summary", "chapters": [], "arcs": []}},
    )
    current_user = SimpleNamespace(id=uuid4())
    db = DummyDB()

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    result = await projects_module.accept_plan(project_id, db=db, current_user=current_user)

    assert result.status == "accepted"
    assert project.project_metadata["plan"]["status"] == "accepted"
    assert "data" in project.project_metadata["plan"]
    assert db.commits == 1
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_update_plan_preserves_status(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={"plan": {"status": "accepted", "data": {"global_summary": "", "arcs": [], "chapters": []}}},
    )
    current_user = SimpleNamespace(id=uuid4())
    db = DummyDB()

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    plan_payload = PlanPayload(
        global_summary="New Summary",
        arcs=[ArcPlan(id="arc-1", title="Arc", summary="Sum", target_emotion="tension", chapter_start=1, chapter_end=1)],
        chapters=[ChapterPlan(index=1, title="Ch1", summary="S", emotional_stake="high")],
    )
    result = await projects_module.update_plan(
        project_id,
        PlanUpdateRequest(plan=plan_payload),
        db=db,
        current_user=current_user,
    )

    assert result.status == "accepted"
    assert project.project_metadata["plan"]["status"] == "accepted"
    assert project.project_metadata["plan"]["data"]["global_summary"] == "New Summary"


@pytest.mark.asyncio
async def test_generate_concept_proposal(monkeypatch):
    current_user = SimpleNamespace(id=uuid4())

    class DummyNovellaService:
        def __init__(self, db):
            self.db = db

        async def generate_concept_preview(self, genre, notes, user_id):
            return {
                "title": "Title",
                "premise": "Premise",
                "tone": "tone",
                "tropes": ["one"],
                "emotional_orientation": "mood",
            }

    monkeypatch.setattr(projects_module, "NovellaForgeService", DummyNovellaService)

    result = await projects_module.generate_concept_proposal(
        payload=projects_module.ConceptProposalRequest(genre="fantasy", notes=None),
        db=None,
        current_user=current_user,
    )

    assert result.status == "draft"
    assert result.concept.premise == "Premise"


@pytest.mark.asyncio
async def test_get_coherence_graph(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, project_metadata={})
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    class DummyMemoryService:
        def export_graph_for_visualization(self, project_id_value):
            return {
                "nodes": [
                    {"id": "1", "label": "Alice", "type": "Character", "properties": {}},
                    {"id": "2", "label": "Dock", "type": "Location", "properties": {}},
                ],
                "edges": [
                    {"source": "1", "target": "2", "type": "RELATION", "properties": {}},
                ],
            }

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)
    monkeypatch.setattr(projects_module, "MemoryService", DummyMemoryService)

    result = await projects_module.get_coherence_graph(
        project_id,
        db=None,
        current_user=current_user,
    )

    assert result["stats"]["total_characters"] == 1
    assert result["stats"]["total_locations"] == 1
    assert result["stats"]["total_relations"] == 1


@pytest.mark.asyncio
async def test_trigger_memory_reconciliation(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id)
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    class DummyTask:
        def __init__(self):
            self.calls = []

        def delay(self, *args):
            self.calls.append(args)

    task = DummyTask()
    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)
    monkeypatch.setattr(projects_module, "reconcile_project_memory", task)

    result = await projects_module.trigger_memory_reconciliation(
        project_id,
        db=None,
        current_user=current_user,
    )

    assert result["task"] == "reconcile_memory"
    assert task.calls == [(str(project_id),)]


@pytest.mark.asyncio
async def test_trigger_rag_rebuild(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id)
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    class DummyTask:
        def __init__(self):
            self.calls = []

        def delay(self, *args):
            self.calls.append(args)

    task = DummyTask()
    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)
    monkeypatch.setattr(projects_module, "rebuild_project_rag", task)

    result = await projects_module.trigger_rag_rebuild(
        project_id,
        db=None,
        current_user=current_user,
    )

    assert result["task"] == "rebuild_rag"
    assert task.calls == [(str(project_id),)]


@pytest.mark.asyncio
async def test_trigger_draft_cleanup(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(id=project_id)
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    class DummyTask:
        def __init__(self):
            self.calls = []

        def delay(self, *args):
            self.calls.append(args)

    task = DummyTask()
    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)
    monkeypatch.setattr(projects_module, "cleanup_old_drafts", task)

    result = await projects_module.trigger_draft_cleanup(
        project_id,
        days_threshold=45,
        db=None,
        current_user=current_user,
    )

    assert result["task"] == "cleanup_old_drafts"
    assert result["days_threshold"] == 45
    assert task.calls == [(str(project_id), 45)]


@pytest.mark.asyncio
async def test_list_contradictions_returns_summary(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={
            "tracked_contradictions": [
                {"id": "c1", "status": "pending"},
                {"id": "c2", "status": "resolved"},
                {"id": "c3", "status": "intentional"},
                {"id": "c4", "status": "pending"},
            ]
        },
    )
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    result = await projects_module.list_contradictions(
        project_id,
        status=None,
        db=None,
        current_user=current_user,
    )

    assert result["summary"]["total"] == 4
    assert result["summary"]["pending"] == 2
    assert result["summary"]["resolved"] == 1
    assert result["summary"]["intentional"] == 1


@pytest.mark.asyncio
async def test_list_contradictions_filters_status(monkeypatch):
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_metadata={
            "tracked_contradictions": [
                {"id": "c1", "status": "pending"},
                {"id": "c2", "status": "resolved"},
            ]
        },
    )
    current_user = SimpleNamespace(id=uuid4())

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    result = await projects_module.list_contradictions(
        project_id,
        status="resolved",
        db=None,
        current_user=current_user,
    )

    assert result["summary"]["total"] == 1
    assert result["summary"]["pending"] == 0
    assert result["summary"]["resolved"] == 1
    assert result["summary"]["intentional"] == 0
    assert result["contradictions"][0]["id"] == "c2"


@pytest.mark.asyncio
async def test_resolve_contradiction_updates_story_bible(monkeypatch):
    project_id = uuid4()
    contradiction_id = "c1"
    project = SimpleNamespace(
        id=project_id,
        project_metadata={
            "tracked_contradictions": [
                {"id": contradiction_id, "status": "pending", "detected_in_chapter": 3}
            ]
        },
    )
    current_user = SimpleNamespace(id=uuid4())
    db = DummyDB()

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    payload = ContradictionResolution(
        type="explanation",
        action_taken="Clarified resurrection.",
        bible_update="Bob returned after the ritual.",
    )
    result = await projects_module.resolve_contradiction(
        project_id,
        contradiction_id,
        payload,
        db=db,
        current_user=current_user,
    )

    contradiction = result["contradiction"]
    assert result["status"] == "resolved"
    assert contradiction["status"] == "resolved"
    assert contradiction["resolution"]["type"] == "explanation"
    assert contradiction["resolution"]["action_taken"] == "Clarified resurrection."
    assert contradiction["resolution"]["bible_update"] == "Bob returned after the ritual."
    assert contradiction["resolution"]["resolved_by"] == str(current_user.id)
    assert project.project_metadata["story_bible"]["established_facts"][0]["fact"] == "Bob returned after the ritual."
    assert (
        project.project_metadata["story_bible"]["established_facts"][0]["resolution_of_contradiction"]
        == contradiction_id
    )
    assert project.project_metadata["story_bible"]["established_facts"][0]["established_chapter"] == 3
    assert db.commits == 1


@pytest.mark.asyncio
async def test_mark_contradiction_intentional_updates_story_bible(monkeypatch):
    project_id = uuid4()
    contradiction_id = "c2"
    project = SimpleNamespace(
        id=project_id,
        project_metadata={
            "tracked_contradictions": [
                {"id": contradiction_id, "status": "pending", "detected_in_chapter": 1}
            ]
        },
    )
    current_user = SimpleNamespace(id=uuid4())
    db = DummyDB()

    class DummyProjectService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, pid, uid):
            if pid == project_id:
                return project
            return None

    monkeypatch.setattr(projects_module, "ProjectService", DummyProjectService)

    payload = ContradictionIntentionalRequest(
        explanation="Time loop revealed later.",
        bible_update="Bob returned via time loop.",
    )
    result = await projects_module.mark_contradiction_intentional(
        project_id,
        contradiction_id,
        payload,
        db=db,
        current_user=current_user,
    )

    contradiction = result["contradiction"]
    assert result["status"] == "intentional"
    assert contradiction["status"] == "intentional"
    assert contradiction["resolution"]["type"] == "intentional"
    assert contradiction["resolution"]["action_taken"] == "Time loop revealed later."
    assert contradiction["resolution"]["bible_update"] == "Bob returned via time loop."
    assert contradiction["resolution"]["resolved_by"] == str(current_user.id)
    assert project.project_metadata["story_bible"]["established_facts"][0]["fact"] == "Bob returned via time loop."
    assert (
        project.project_metadata["story_bible"]["established_facts"][0]["resolution_of_contradiction"]
        == contradiction_id
    )
    assert db.commits == 1
