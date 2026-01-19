from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import auth as auth_module
from app.schemas.user import UserCreate, UserLogin


class DummyAuthService:
    def __init__(self, db):
        self.db = db
        self.user = None

    async def register_user(self, user_data):
        return self.user

    async def authenticate_user(self, email, password):
        return self.user


@pytest.mark.asyncio
async def test_register_returns_token(monkeypatch):
    user = SimpleNamespace(id=uuid4(), email="user@example.com")
    service = DummyAuthService(db=None)
    service.user = user

    monkeypatch.setattr(auth_module, "AuthService", lambda db: service)
    monkeypatch.setattr(auth_module, "create_access_token", lambda user_id: "token")

    result = await auth_module.register(
        request=SimpleNamespace(),
        user_data=UserCreate(email="user@example.com", password="password123"),
        db=None,
    )

    assert result["access_token"] == "token"
    assert result["user"] == user


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(monkeypatch):
    service = DummyAuthService(db=None)
    service.user = None
    monkeypatch.setattr(auth_module, "AuthService", lambda db: service)

    form = SimpleNamespace(username="user@example.com", password="password123")
    with pytest.raises(HTTPException):
        await auth_module.login(request=SimpleNamespace(), form_data=form, db=None)


@pytest.mark.asyncio
async def test_login_rejects_inactive_user(monkeypatch):
    user = SimpleNamespace(id=uuid4(), is_active=False)
    service = DummyAuthService(db=None)
    service.user = user
    monkeypatch.setattr(auth_module, "AuthService", lambda db: service)

    form = SimpleNamespace(username="user@example.com", password="password123")
    with pytest.raises(HTTPException):
        await auth_module.login(request=SimpleNamespace(), form_data=form, db=None)


@pytest.mark.asyncio
async def test_login_success(monkeypatch):
    user = SimpleNamespace(id=uuid4(), is_active=True)
    service = DummyAuthService(db=None)
    service.user = user
    monkeypatch.setattr(auth_module, "AuthService", lambda db: service)
    monkeypatch.setattr(auth_module, "create_access_token", lambda user_id: "token")

    form = SimpleNamespace(username="user@example.com", password="password123")
    result = await auth_module.login(request=SimpleNamespace(), form_data=form, db=None)

    assert result["access_token"] == "token"


@pytest.mark.asyncio
async def test_login_json_rejects_invalid(monkeypatch):
    service = DummyAuthService(db=None)
    service.user = None
    monkeypatch.setattr(auth_module, "AuthService", lambda db: service)

    with pytest.raises(HTTPException):
        await auth_module.login_json(
            request=SimpleNamespace(),
            credentials=UserLogin(email="user@example.com", password="password123"),
            db=None,
        )


@pytest.mark.asyncio
async def test_login_json_rejects_inactive(monkeypatch):
    user = SimpleNamespace(id=uuid4(), is_active=False)
    service = DummyAuthService(db=None)
    service.user = user
    monkeypatch.setattr(auth_module, "AuthService", lambda db: service)

    with pytest.raises(HTTPException):
        await auth_module.login_json(
            request=SimpleNamespace(),
            credentials=UserLogin(email="user@example.com", password="password123"),
            db=None,
        )


@pytest.mark.asyncio
async def test_login_json_success(monkeypatch):
    user = SimpleNamespace(id=uuid4(), is_active=True)
    service = DummyAuthService(db=None)
    service.user = user
    monkeypatch.setattr(auth_module, "AuthService", lambda db: service)
    monkeypatch.setattr(auth_module, "create_access_token", lambda user_id: "token")

    result = await auth_module.login_json(
        request=SimpleNamespace(),
        credentials=UserLogin(email="user@example.com", password="password123"),
        db=None,
    )

    assert result["access_token"] == "token"


@pytest.mark.asyncio
async def test_get_current_user_info_returns_user():
    user = SimpleNamespace(email="user@example.com")
    result = await auth_module.get_current_user_info(current_user=user)
    assert result == user


@pytest.mark.asyncio
async def test_logout_returns_message():
    result = await auth_module.logout()
    assert result["message"] == "Successfully logged out"
