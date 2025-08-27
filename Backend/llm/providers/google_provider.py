from __future__ import annotations

import os
import asyncio
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from ..base import BaseLLMProvider, ModelInfo, GenerationResult


class GoogleProvider:
    def __init__(self, models: Optional[List[ModelInfo]] = None, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY") or ""
        if self._api_key:
            genai.configure(api_key=self._api_key)
        self._models = models or [
            ModelInfo(provider="google", model="gemini-1.5-flash", display_name="Gemini 1.5 Flash"),
            ModelInfo(provider="google", model="gemini-1.5-pro", display_name="Gemini 1.5 Pro"),
        ]

    @property
    def provider_key(self) -> str:
        return "google"

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
        if not self._api_key:
            raise RuntimeError("Google Generative AI API key not configured")

        # Convert messages into a single prompt with roles
        prompt_parts: List[str] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content") or ""
            prompt_parts.append(f"{role}: {content}")
        prompt = "\n\n".join(prompt_parts)

        def _run_sync() -> GenerationResult:
            mdl = genai.GenerativeModel(model)
            gen_cfg: Dict[str, Any] = {}
            if temperature is not None:
                gen_cfg["temperature"] = float(temperature)
            if max_tokens is not None:
                gen_cfg["max_output_tokens"] = int(max_tokens)

            resp = mdl.generate_content(prompt, generation_config=gen_cfg or None)
            text = resp.text or ""
            usage = getattr(resp, "usage_metadata", None)
            in_tok = getattr(usage, "prompt_token_count", 0) if usage else 0
            out_tok = getattr(usage, "candidates_token_count", 0) if usage else 0
            return GenerationResult(content=text, input_tokens=in_tok, output_tokens=out_tok, raw=resp)

        # google-generativeai is sync; run in thread
        return await asyncio.to_thread(_run_sync)
