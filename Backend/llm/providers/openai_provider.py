from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from ..base import BaseLLMProvider, ModelInfo, GenerationResult


class OpenAIProvider:
    def __init__(self, models: Optional[List[ModelInfo]] = None, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY") or ""
        self._client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None
        self._models = models or [
            ModelInfo(provider="openai", model="gpt-4o-mini", display_name="GPT-4o mini"),
            ModelInfo(provider="openai", model="gpt-4o", display_name="GPT-4o"),
        ]

    @property
    def provider_key(self) -> str:
        return "openai"

    def list_models(self) -> List[ModelInfo]:
        return list(self._models)

    def supports_model(self, model: str) -> bool:
        return any(m.model == model for m in self._models)

    def get_model_info(self, model: str) -> Optional[ModelInfo]:
        for m in self._models:
            if m.model == model:
                return m
        return None

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> GenerationResult:
        if not self._client:
            raise RuntimeError("OpenAI API key not configured")

        params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        if stream:
            # For now, non-streaming only; streaming can be added later
            stream = False

        resp = await self._client.chat.completions.create(**params)
        content = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
        out_tok = getattr(usage, "completion_tokens", 0) if usage else 0
        return GenerationResult(content=content, input_tokens=in_tok, output_tokens=out_tok, raw=resp)
