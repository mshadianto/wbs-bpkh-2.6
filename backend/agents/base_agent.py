"""
WBS BPKH AI - Base Agent
========================
Shared base class for all analysis agents.
"""

from groq import Groq
from typing import Dict, Any, List
import asyncio
import json
from loguru import logger


class BaseAgent:
    """Base class for all analysis agents with shared LLM call logic."""

    def __init__(self, client: Groq, model: str, name: str = "BaseAgent"):
        self.client = client
        self.model = model
        self.name = name

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.1
    ) -> str:
        """Call the LLM and return raw response content.

        Raises on API errors so retry_llm_call can handle retries.
        """
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    async def _call_llm_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """Call LLM and parse JSON response.

        Returns parsed dict. Raises json.JSONDecodeError on parse failure.
        """
        content = await self._call_llm(
            system_prompt, user_prompt, max_tokens, temperature
        )
        return json.loads(content)
