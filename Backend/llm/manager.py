from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.llm.base import BaseLLMProvider, ModelInfo, GenerationResult
from Backend.database.models import TokenUsage, UserSubscription, ModelProvider


@dataclass
class UsageCheck:
    allowed: bool
    reason: Optional[str] = None
    soft_cap_reached: bool = False
    hard_cap_reached: bool = False
    current_tokens: int = 0
    monthly_limit: Optional[int] = None


def current_period(dt: Optional[datetime] = None) -> str:
    now = dt or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


class LLMManager:
    """Routes requests to providers, enforces usage limits, and records usage."""

    def __init__(self, providers: Sequence[BaseLLMProvider]):
        self._providers = list(providers)

    def _find_provider(self, model: str) -> Optional[BaseLLMProvider]:
        for p in self._providers:
            try:
                if p.supports_model(model):
                    return p
            except Exception:
                continue
        return None

    async def list_models(self, db: AsyncSession) -> List[ModelInfo]:
        rows = (await db.execute(select(ModelProvider))).scalars().all()
        infos: List[ModelInfo] = []
        for r in rows:
            infos.append(
                ModelInfo(
                    provider=r.provider,
                    model=r.model,
                    display_name=r.display_name,
                    is_free_tier=r.is_free_tier,
                    context_window=r.context_window,
                    input_token_cost_usd=r.input_token_cost_usd,
                    output_token_cost_usd=r.output_token_cost_usd,
                    endpoint_url=r.endpoint_url,
                    pricing_config=r.pricing_config,
                    metadata=r.meta,
                )
            )
        return infos

    async def get_model_info(self, db: AsyncSession, model: str) -> Optional[ModelInfo]:
        r = (
            await db.execute(
                select(ModelProvider).where(ModelProvider.model == model, ModelProvider.is_active == True)  # noqa: E712
            )
        ).scalar_one_or_none()
        if not r:
            return None
        return ModelInfo(
            provider=r.provider,
            model=r.model,
            display_name=r.display_name,
            is_free_tier=r.is_free_tier,
            context_window=r.context_window,
            input_token_cost_usd=r.input_token_cost_usd,
            output_token_cost_usd=r.output_token_cost_usd,
            endpoint_url=r.endpoint_url,
            pricing_config=r.pricing_config,
            metadata=r.meta,
        )

    async def _ensure_subscription(self, db: AsyncSession, user_id: uuid.UUID) -> UserSubscription:
        sub = (
            await db.execute(
                select(UserSubscription).where(UserSubscription.user_id == user_id)
            )
        ).scalar_one_or_none()
        if sub is None:
            sub = UserSubscription(user_id=user_id, tier="free", is_active=True)
            db.add(sub)
            await db.commit()
            await db.refresh(sub)
        return sub

    async def get_monthly_usage(self, db: AsyncSession, user_id: uuid.UUID, period: Optional[str] = None) -> int:
        per = period or current_period()
        total = (
            await db.execute(
                select(func.coalesce(func.sum(TokenUsage.total_tokens), 0)).where(
                    TokenUsage.user_id == user_id, TokenUsage.period == per
                )
            )
        ).scalar_one()
        return int(total or 0)

    async def can_use(self, db: AsyncSession, user_id: uuid.UUID, needed_tokens: int) -> UsageCheck:
        sub = await self._ensure_subscription(db, user_id)
        if not sub.is_active:
            return UsageCheck(allowed=False, reason="Subscription inactive")

        limit = sub.monthly_token_limit
        soft = sub.soft_limit_tokens
        hard = sub.hard_limit_tokens

        used = await self.get_monthly_usage(db, user_id)
        next_total = used + max(0, needed_tokens)

        # Hard cap check
        if hard is not None and next_total > hard:
            return UsageCheck(
                allowed=False,
                reason="Hard token limit exceeded",
                hard_cap_reached=True,
                current_tokens=used,
                monthly_limit=limit,
            )

        # Monthly limit as primary enforcement
        if limit is not None and next_total > limit:
            return UsageCheck(
                allowed=False,
                reason="Monthly token limit exceeded",
                current_tokens=used,
                monthly_limit=limit,
                soft_cap_reached=soft is not None and used >= soft,
            )

        # Soft cap warning only
        sc = soft is not None and next_total >= soft
        return UsageCheck(
            allowed=True,
            soft_cap_reached=sc,
            current_tokens=used,
            monthly_limit=limit,
        )

    async def generate(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[uuid.UUID],
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
        execution_id: Optional[uuid.UUID] = None,
    ) -> GenerationResult:
        # Resolve model info
        info = await self.get_model_info(db, model)
        if info is None:
            # Fallback: try provider self-reported lists
            prov = self._find_provider(model)
            if prov is None:
                raise ValueError(f"Model not found or inactive: {model}")
            mi = prov.get_model_info(model)
            if mi is None:
                raise ValueError(f"Provider does not support model: {model}")
            info = mi
        else:
            prov = self._find_provider(model)
            if prov is None:
                raise ValueError(f"No provider registered for model: {model}")

        # Optionally enforce pre-check using an estimate if max_tokens given
        if user_id is not None and max_tokens is not None:
            chk = await self.can_use(db, user_id, needed_tokens=max_tokens)
            if not chk.allowed:
                raise PermissionError(chk.reason or "Usage limit exceeded")

        # Perform generation
        result = await prov.generate(
            messages=messages,
            model=model,
            stream=stream,
            temperature=temperature,
            max_tokens=max_tokens,
            extra=extra,
        )

        # Record usage
        if user_id is not None:
            await self._record_usage(
                db,
                user_id=user_id,
                execution_id=execution_id,
                info=info,
                result=result,
            )
        return result

    async def _record_usage(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        execution_id: Optional[uuid.UUID],
        info: ModelInfo,
        result: GenerationResult,
    ) -> None:
        period = current_period()
        usage = TokenUsage(
            user_id=user_id,
            execution_id=execution_id,
            provider=info.provider,
            model=info.model,
            period=period,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=(result.input_tokens + result.output_tokens),
            estimated_cost_usd=BaseLLMProvider.estimate_cost_usd(
                result.input_tokens, result.output_tokens, info
            ),
        )
        db.add(usage)
        await db.commit()
