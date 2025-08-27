from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, List, Dict, Protocol


@dataclass
class ModelInfo:
    provider: str
    model: str
    display_name: str
    is_free_tier: bool = False
    context_window: Optional[int] = None
    input_token_cost_usd: Optional[float] = None
    output_token_cost_usd: Optional[float] = None
    endpoint_url: Optional[str] = None
    pricing_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class GenerationResult:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Any = None


class BaseLLMProvider(Protocol):
    """Abstract provider interface for LLM generation."""

    @property
    def provider_key(self) -> str:
        ...

    def list_models(self) -> List[ModelInfo]:
        ...

    def supports_model(self, model: str) -> bool:
        return any(m.model == model for m in self.list_models())

    def get_model_info(self, model: str) -> Optional[ModelInfo]:
        for m in self.list_models():
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
        ...

    @staticmethod
    def estimate_cost_usd(
        input_tokens: int,
        output_tokens: int,
        info: ModelInfo,
    ) -> float:
        in_cost = (info.input_token_cost_usd or 0.0) * (input_tokens / 1000.0)
        out_cost = (info.output_token_cost_usd or 0.0) * (output_tokens / 1000.0)
        return round(in_cost + out_cost, 6)
