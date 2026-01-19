from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.character import CharacterCreate, CharacterUpdate
from app.services.character_service import CharacterService


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
async def test_get_all_by_project_returns_characters():
    project_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(id=project_id, owner_id=user_id)
    char_one = SimpleNamespace(id=uuid4())
    char_two = SimpleNamespace(id=uuid4())
    db = DummyDB(
        results=[
            DummyResult(scalar=project),
            DummyResult(scalar=2),
            DummyResult(scalars=[char_one, char_two]),
        ]
    )
    service = CharacterService(db)

    characters, total = await service.get_all_by_project(project_id, user_id, skip=0, limit=10)

    assert total == 2
    assert characters == [char_one, char_two]


@pytest.mark.asyncio
async def test_get_all_by_project_requires_ownership():
    db = DummyDB(results=[DummyResult(scalar=None)])
    service = CharacterService(db)

    with pytest.raises(HTTPException):
        await service.get_all_by_project(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_create_sets_metadata_defaults():
    project_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(id=project_id, owner_id=user_id)
    db = DummyDB(results=[DummyResult(scalar=project)])
    service = CharacterService(db)
    payload = CharacterCreate(
        name="Alice",
        description="Desc",
        physical_description=None,
        personality=None,
        backstory=None,
        project_id=project_id,
        metadata=None,
    )

    character = await service.create(payload, user_id)

    assert character.name == "Alice"
    assert character.character_metadata == {}
    assert db.commits == 1
    assert db.refreshes == 1
    assert db.added


@pytest.mark.asyncio
async def test_update_updates_fields():
    user_id = uuid4()
    character = SimpleNamespace(
        id=uuid4(),
        name="Alice",
        description="Old",
        physical_description="Old",
        personality="Old",
        backstory="Old",
        character_metadata={},
    )
    db = DummyDB(results=[DummyResult(scalar=character)])
    service = CharacterService(db)
    update_payload = CharacterUpdate(description="New", personality="New")

    updated = await service.update(character.id, update_payload, user_id)

    assert updated.description == "New"
    assert updated.personality == "New"
    assert db.commits == 1
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_update_missing_character_raises():
    db = DummyDB(results=[DummyResult(scalar=None)])
    service = CharacterService(db)

    with pytest.raises(HTTPException):
        await service.update(uuid4(), CharacterUpdate(description="New"), uuid4())


@pytest.mark.asyncio
async def test_delete_removes_character():
    user_id = uuid4()
    character = SimpleNamespace(id=uuid4())
    db = DummyDB(results=[DummyResult(scalar=character)])
    service = CharacterService(db)

    deleted = await service.delete(character.id, user_id)

    assert deleted is True
    assert db.deleted == [character]
    assert db.commits == 1


@pytest.mark.asyncio
async def test_delete_missing_character_returns_false():
    db = DummyDB(results=[DummyResult(scalar=None)])
    service = CharacterService(db)

    deleted = await service.delete(uuid4(), uuid4())

    assert deleted is False
