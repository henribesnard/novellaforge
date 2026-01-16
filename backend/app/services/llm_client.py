"""LLM client wrapper for DeepSeek API."""
from typing import List, Dict, Optional, Any
import httpx
from httpx import ReadTimeout

from app.core.config import settings


class DeepSeekClient:
    """Async client for DeepSeek chat completions."""

    def __init__(self) -> None:
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_API_BASE.rstrip("/")
        self.model = settings.DEEPSEEK_MODEL

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

        timeout = httpx.Timeout(settings.DEEPSEEK_TIMEOUT, read=settings.DEEPSEEK_TIMEOUT)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
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
