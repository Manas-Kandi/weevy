from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from ..base import BaseLLMProvider, ModelInfo, GenerationResult


class NvidiaProvider:
    """Uses OpenAI-compatible endpoint for NVIDIA NIM via integrate.api.nvidia.com."""

    def __init__(self, models: Optional[List[ModelInfo]] = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self._api_key = api_key or os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NGC_API_KEY") or ""
        self._base_url = base_url or os.getenv("NVIDIA_OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url) if self._api_key else None
        # Default free-tier or sample models; can be overridden by DB ModelProvider entries
        self._models = models or [
            ModelInfo(provider="nvidia", model="meta/llama-3.1-8b-instruct", display_name="Llama 3.1 8B Instruct", is_free_tier=True),
            ModelInfo(provider="nvidia", model="mistralai/mixtral-8x7b-instruct-v0.1", display_name="Mixtral 8x7B Instruct", is_free_tier=True),
        ]

    @property
    def provider_key(self) -> str:
        return "nvidia"

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
            raise RuntimeError("NVIDIA API key not configured")

        params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        if stream:
            # Non-streaming for MVP
            stream = False

        resp = await self._client.chat.completions.create(**params)
        content = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
        out_tok = getattr(usage, "completion_tokens", 0) if usage else 0
        return GenerationResult(content=content, input_tokens=in_tok, output_tokens=out_tok, raw=resp)
