from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.services.user_service as user_service_module
from app.schemas.user import UserUpdate
from app.services.user_service import UserService


class DummyResult:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class DummyDB:
    def __init__(self, user=None, email_user=None):
        self.user = user
        self.email_user = email_user
        self.deleted = None
        self.commits = 0
        self.refreshes = 0

    async def get(self, model, user_id):
        return self.user

    async def execute(self, *args, **kwargs):
        return DummyResult(self.email_user)

    async def delete(self, user):
        self.deleted = user

    async def commit(self):
        self.commits += 1

    async def refresh(self, user):
        self.refreshes += 1


@pytest.mark.asyncio
async def test_get_by_id_returns_user():
    user = SimpleNamespace(id=uuid4())
    db = DummyDB(user=user)
    service = UserService(db)

    result = await service.get_by_id(user.id)

    assert result is user


@pytest.mark.asyncio
async def test_get_by_email_returns_user():
    user = SimpleNamespace(email="user@example.com")
    db = DummyDB(email_user=user)
    service = UserService(db)

    result = await service.get_by_email("user@example.com")

    assert result is user


@pytest.mark.asyncio
async def test_update_rejects_missing_user():
    db = DummyDB(user=None)
    service = UserService(db)

    with pytest.raises(HTTPException) as excinfo:
        await service.update(uuid4(), UserUpdate(full_name="Name"))

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_update_rejects_existing_email():
    user = SimpleNamespace(id=uuid4(), email="old@example.com", full_name="Old", hashed_password="x")
    existing = SimpleNamespace(email="new@example.com")
    db = DummyDB(user=user, email_user=existing)
    service = UserService(db)

    with pytest.raises(HTTPException) as excinfo:
        await service.update(user.id, UserUpdate(email="new@example.com"))

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_update_sets_fields_and_hash(monkeypatch):
    user = SimpleNamespace(
        id=uuid4(),
        email="old@example.com",
        full_name="Old",
        hashed_password="old",
    )
    db = DummyDB(user=user, email_user=None)
    service = UserService(db)

    monkeypatch.setattr(user_service_module, "get_password_hash", lambda _: "hashed")

    result = await service.update(
        user.id,
        UserUpdate(email="new@example.com", full_name="New", password="password123"),
    )

    assert result is user
    assert user.email == "new@example.com"
    assert user.full_name == "New"
    assert user.hashed_password == "hashed"
    assert db.commits == 1
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_delete_returns_false_when_missing():
    db = DummyDB(user=None)
    service = UserService(db)

    assert await service.delete(uuid4()) is False
    assert db.deleted is None


@pytest.mark.asyncio
async def test_delete_removes_user():
    user = SimpleNamespace(id=uuid4())
    db = DummyDB(user=user)
    service = UserService(db)

    assert await service.delete(user.id) is True
    assert db.deleted is user
    assert db.commits == 1
