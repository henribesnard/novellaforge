import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.responses import Response

from app.core.config import settings
from app import main


class DummyURL:
    def __init__(self, path: str):
        self.path = path

    def __str__(self) -> str:
        return self.path


@pytest.mark.asyncio
async def test_health_check_returns_status():
    result = await main.health_check()
    assert result["status"] == "healthy"
    assert result["version"] == settings.VERSION
    assert result["environment"] == settings.APP_ENV


@pytest.mark.asyncio
async def test_root_returns_message():
    result = await main.root()
    assert "NovellaForge API" in result["message"]
    expected_docs = "/api/docs" if settings.DEBUG else None
    assert result["docs"] == expected_docs


@pytest.mark.asyncio
async def test_http_exception_handler_returns_json():
    response = await main.http_exception_handler(
        request=SimpleNamespace(),
        exc=HTTPException(status_code=418, detail="teapot"),
    )
    payload = json.loads(response.body.decode("utf-8"))
    assert response.status_code == 418
    assert payload["detail"] == "teapot"


@pytest.mark.asyncio
async def test_global_exception_handler_returns_json():
    request = SimpleNamespace(
        method="GET",
        url=DummyURL("/path"),
        client=SimpleNamespace(host="127.0.0.1"),
    )
    response = await main.global_exception_handler(request, Exception("boom"))
    payload = json.loads(response.body.decode("utf-8"))
    assert response.status_code == 500
    assert payload["detail"] == "Une erreur interne est survenue"
    if settings.DEBUG:
        assert payload["error"] == "boom"
        assert payload["type"] == "Exception"


@pytest.mark.asyncio
async def test_add_process_time_header_sets_header():
    async def call_next(request):
        return Response("ok")

    response = await main.add_process_time_header(SimpleNamespace(), call_next)
    assert "X-Process-Time" in response.headers
