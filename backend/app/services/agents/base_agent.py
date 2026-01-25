"""Base agent class for all AI agents"""
import os
import asyncio
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all NovellaForge AI agents"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.model = "deepseek-chat"

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description"""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for the agent"""
        pass

    async def _call_api(
        self,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Call DeepSeek API"""
        if not self.api_key:
            raise Exception(f"Error calling API for {self.name}: missing DEEPSEEK_API_KEY")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build context string if provided
        context_str = ""
        if context:
            context_str = "\n\nCONTEXTE:\n"
            for key, value in context.items():
                if value:
                    context_str += f"{key}: {value}\n"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt + context_str},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        max_retries = max(int(settings.DEEPSEEK_MAX_RETRIES), 0)
        backoff = max(float(settings.DEEPSEEK_RETRY_BACKOFF), 0.0)
        timeout = httpx.Timeout(settings.DEEPSEEK_TIMEOUT, read=settings.DEEPSEEK_TIMEOUT)
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                if response.status_code != 200:
                    error_text = response.text
                    status_code = response.status_code
                    if status_code >= 500 and attempt < max_retries:
                        await asyncio.sleep(backoff * (2 ** attempt))
                        continue
                    error_text = (error_text or "").strip()
                    if len(error_text) > 2000:
                        error_text = f"{error_text[:2000]}..."
                    raise Exception(f"API error ({status_code}): {error_text}")

                result = response.json()
                return result["choices"][0]["message"]["content"]

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < max_retries:
                    await asyncio.sleep(backoff * (2 ** attempt))
                    continue
            except Exception as exc:
                last_error = exc
                break

        logger.error("Error calling API for %s: %s", self.name, last_error, exc_info=True)
        raise Exception(f"Error calling API for {self.name}: {last_error}")

    @abstractmethod
    async def execute(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the agent's task"""
        pass
