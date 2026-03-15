"""LLM client wrapper for DeepSeek API."""
from typing import List, Dict, Optional, Any, AsyncIterator
import json
import httpx
from httpx import ReadTimeout

from app.core.config import settings


class DeepSeekClient:
    """Async client for DeepSeek chat completions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = (base_url or settings.DEEPSEEK_API_BASE).rstrip("/")
        self.model = model or settings.DEEPSEEK_MODEL
        self.timeout = timeout or settings.DEEPSEEK_TIMEOUT
        self._client = client

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        return_full: bool = False,
    ) -> Any:
        """Call DeepSeek chat completions and return the assistant content."""
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        try:
            if self._client is None:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
            else:
                response = await self._client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
            if response.status_code != 200:
                raise RuntimeError(f"DeepSeek API error: {response.text}")
        except ReadTimeout:
            raise
        except httpx.HTTPError as exc:
            raise RuntimeError(
                "DeepSeek connection error. Please retry in a moment."
            ) from exc

        result = response.json()
        message = result["choices"][0]["message"]
        if return_full:
            return message
        return message.get("content", "")

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream DeepSeek chat completions token by token."""
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        try:
            if self._client is None:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            raise RuntimeError(f"DeepSeek API error: {error_text.decode()}")

                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
            else:
                async with self._client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise RuntimeError(f"DeepSeek API error: {error_text.decode()}")

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
        except ReadTimeout:
            raise
        except httpx.HTTPError as exc:
            raise RuntimeError(
                "DeepSeek connection error. Please retry in a moment."
            ) from exc

    def chat_stream_full(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None,
    ) -> "StreamCollector":
        """
        Stream chat and collect full response.

        Returns a StreamCollector: iterate with ``async for chunk in collector``,
        then access ``collector.full_content`` after iteration completes.
        """
        return StreamCollector(self, messages, temperature, max_tokens, model)


class StreamCollector:
    """Async iterator that collects streamed chunks and exposes full_content."""

    def __init__(
        self,
        client: DeepSeekClient,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        model: Optional[str],
    ) -> None:
        self._client = client
        self._messages = messages
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._model = model
        self._collected: List[str] = []

    @property
    def full_content(self) -> str:
        return "".join(self._collected)

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[str]:
        async for chunk in self._client.chat_stream(
            messages=self._messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            model=self._model,
        ):
            self._collected.append(chunk)
            yield chunk
