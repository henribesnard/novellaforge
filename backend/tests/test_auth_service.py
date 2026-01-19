from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.services.auth_service as auth_service_module
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService


class DummyResult:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class DummyDB:
    def __init__(self, user=None):
        self.user = user
        self.added = None
        self.commits = 0
        self.refreshes = 0

    async def execute(self, *args, **kwargs):
        return DummyResult(self.user)

    def add(self, user):
        self.added = user

    async def commit(self):
        self.commits += 1

    async def refresh(self, user):
        self.refreshes += 1


@pytest.mark.asyncio
async def test_register_user_rejects_existing():
    db = DummyDB(user=SimpleNamespace(email="user@example.com"))
    service = AuthService(db)

    with pytest.raises(HTTPException) as excinfo:
        await service.register_user(
            UserCreate(email="user@example.com", password="password123")
        )

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_register_user_creates_user(monkeypatch):
    db = DummyDB(user=None)
    service = AuthService(db)

    monkeypatch.setattr(auth_service_module, "get_password_hash", lambda _: "hashed")

    user = await service.register_user(
        UserCreate(email="user@example.com", password="password123", full_name="User")
    )

    assert db.added is user
    assert user.email == "user@example.com"
    assert user.full_name == "User"
    assert user.hashed_password == "hashed"
    assert db.commits == 1
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_authenticate_user_returns_none_if_missing():
    db = DummyDB(user=None)
    service = AuthService(db)

    result = await service.authenticate_user("user@example.com", "password123")

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_rejects_invalid_password(monkeypatch):
    user = SimpleNamespace(hashed_password="hashed", last_login_at=None)
    db = DummyDB(user=user)
    service = AuthService(db)

    monkeypatch.setattr(auth_service_module, "verify_password", lambda *_: False)

    result = await service.authenticate_user("user@example.com", "password123")

    assert result is None
    assert db.commits == 0


@pytest.mark.asyncio
async def test_authenticate_user_updates_last_login(monkeypatch):
    user = SimpleNamespace(hashed_password="hashed", last_login_at=None)
    db = DummyDB(user=user)
    service = AuthService(db)

    monkeypatch.setattr(auth_service_module, "verify_password", lambda *_: True)

    result = await service.authenticate_user("user@example.com", "password123")

    assert result is user
    assert user.last_login_at is not None
    assert db.commits == 1
