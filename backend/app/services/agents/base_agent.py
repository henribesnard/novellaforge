"""Base agent class for all AI agents"""
import os
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import httpx


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
        try:
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

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0,
                )

                if response.status_code != 200:
                    raise Exception(f"API error: {response.text}")

                result = response.json()
                return result["choices"][0]["message"]["content"]

        except Exception as e:
            raise Exception(f"Error calling API for {self.name}: {str(e)}")

    @abstractmethod
    async def execute(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the agent's task"""
        pass
