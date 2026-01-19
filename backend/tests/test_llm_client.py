import pytest
import httpx

from app.services.llm_client import DeepSeekClient


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text="error"):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


class DummyClient:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.captured = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, headers=None, json=None):
        self.captured = {"url": url, "headers": headers, "json": json}
        if self.exc:
            raise self.exc
        return self.response


@pytest.mark.asyncio
async def test_llm_client_returns_message_content(monkeypatch):
    response = DummyResponse(
        status_code=200,
        json_data={"choices": [{"message": {"content": "Hello", "role": "assistant"}}]},
    )
    client = DummyClient(response=response)
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: client)

    llm = DeepSeekClient()
    result = await llm.chat(messages=[{"role": "user", "content": "hi"}])

    assert result == "Hello"


@pytest.mark.asyncio
async def test_llm_client_returns_full_message(monkeypatch):
    response = DummyResponse(
        status_code=200,
        json_data={"choices": [{"message": {"content": "Hello", "role": "assistant"}}]},
    )
    client = DummyClient(response=response)
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: client)

    llm = DeepSeekClient()
    result = await llm.chat(messages=[{"role": "user", "content": "hi"}], return_full=True)

    assert result["content"] == "Hello"


@pytest.mark.asyncio
async def test_llm_client_includes_response_format(monkeypatch):
    response = DummyResponse(
        status_code=200,
        json_data={"choices": [{"message": {"content": "{}", "role": "assistant"}}]},
    )
    client = DummyClient(response=response)
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: client)

    llm = DeepSeekClient()
    await llm.chat(
        messages=[{"role": "user", "content": "hi"}],
        response_format={"type": "json_object"},
    )

    assert client.captured["json"]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_llm_client_raises_on_bad_status(monkeypatch):
    response = DummyResponse(status_code=500, json_data={}, text="fail")
    client = DummyClient(response=response)
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: client)

    llm = DeepSeekClient()

    with pytest.raises(RuntimeError):
        await llm.chat(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_llm_client_raises_on_http_error(monkeypatch):
    client = DummyClient(exc=httpx.HTTPError("fail"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: client)

    llm = DeepSeekClient()

    with pytest.raises(RuntimeError):
        await llm.chat(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_llm_client_propagates_timeout(monkeypatch):
    client = DummyClient(exc=httpx.ReadTimeout("timeout"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: client)

    llm = DeepSeekClient()

    with pytest.raises(httpx.ReadTimeout):
        await llm.chat(messages=[{"role": "user", "content": "hi"}])
