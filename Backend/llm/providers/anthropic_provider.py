from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from ..base import BaseLLMProvider, ModelInfo, GenerationResult


class AnthropicProvider:
    def __init__(self, models: Optional[List[ModelInfo]] = None, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or ""
        self._client = AsyncAnthropic(api_key=self._api_key) if self._api_key else None
        self._models = models or [
            ModelInfo(provider="anthropic", model="claude-3-5-sonnet-20240620", display_name="Claude 3.5 Sonnet"),
            ModelInfo(provider="anthropic", model="claude-3-opus-20240229", display_name="Claude 3 Opus"),
        ]

    @property
    def provider_key(self) -> str:
        return "anthropic"

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
            raise RuntimeError("Anthropic API key not configured")

        # Anthropic separates system prompt; convert messages
        system_text = None
        converted: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content") or ""
            if role == "system" and system_text is None:
                system_text = content
            elif role in ("user", "assistant"):
                converted.append({"role": role, "content": content})

        params: Dict[str, Any] = {
            "model": model,
            "messages": converted,
            "max_tokens": max_tokens or 1024,
        }
        if temperature is not None:
            params["temperature"] = temperature
        if system_text:
            params["system"] = system_text

        if stream:
            # Streaming not yet implemented
            pass

        resp = await self._client.messages.create(**params)
        # Extract text from first content block
        text = ""
        if resp.content and len(resp.content) > 0 and getattr(resp.content[0], "text", None):
            text = resp.content[0].text or ""
        usage = getattr(resp, "usage", None)
        in_tok = getattr(usage, "input_tokens", 0) if usage else 0
        out_tok = getattr(usage, "output_tokens", 0) if usage else 0
        return GenerationResult(content=text, input_tokens=in_tok, output_tokens=out_tok, raw=resp)
