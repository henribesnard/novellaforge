from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core import security


class DummyDB:
    def __init__(self, user=None):
        self.user = user

    async def get(self, model, user_id):
        return self.user


def test_password_hash_and_verify_long_password():
    long_password = "a" * 120
    hashed = security.get_password_hash(long_password)
    assert security.verify_password(long_password, hashed) is True
    assert security.verify_password("different", hashed) is False


def test_create_and_decode_token_round_trip():
    user_id = uuid4()
    token = security.create_access_token(user_id)
    payload = security.decode_token(token)

    assert payload is not None
    assert payload.sub == user_id


def test_decode_token_invalid_returns_none():
    assert security.decode_token("not-a-token") is None


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token():
    db = DummyDB(user=None)
    with pytest.raises(HTTPException) as excinfo:
        await security.get_current_user(db=db, token="bad-token")

    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_user():
    user_id = uuid4()
    token = security.create_access_token(user_id)
    db = DummyDB(user=None)

    with pytest.raises(HTTPException) as excinfo:
        await security.get_current_user(db=db, token=token)

    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_returns_user():
    user = SimpleNamespace(id=uuid4(), is_active=True)
    token = security.create_access_token(user.id)
    db = DummyDB(user=user)

    result = await security.get_current_user(db=db, token=token)

    assert result is user


@pytest.mark.asyncio
async def test_get_current_active_user_rejects_inactive():
    user = SimpleNamespace(is_active=False)
    with pytest.raises(HTTPException) as excinfo:
        await security.get_current_active_user(current_user=user)

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_get_current_active_user_returns_user():
    user = SimpleNamespace(is_active=True)
    result = await security.get_current_active_user(current_user=user)
    assert result is user


@pytest.mark.asyncio
async def test_get_current_superuser_rejects_non_superuser():
    user = SimpleNamespace(is_superuser=False)
    with pytest.raises(HTTPException) as excinfo:
        await security.get_current_superuser(current_user=user)

    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_superuser_returns_user():
    user = SimpleNamespace(is_superuser=True)
    result = await security.get_current_superuser(current_user=user)
    assert result is user
