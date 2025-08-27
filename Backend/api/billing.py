from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_session
from ..database.models import User, UserSubscription, TokenUsage, ModelProvider

router = APIRouter(prefix="/api/billing", tags=["billing"])


# --------- Schemas ---------
class SubscriptionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    tier: str
    is_active: bool
    period_start: datetime
    period_end: Optional[datetime] = None
    monthly_token_limit: Optional[int] = None
    hard_limit_tokens: Optional[int] = None
    soft_limit_tokens: Optional[int] = None

    class Config:
        from_attributes = True


class SubscriptionUpdate(BaseModel):
    tier: Optional[str] = None
    is_active: Optional[bool] = None
    monthly_token_limit: Optional[int] = None
    hard_limit_tokens: Optional[int] = None
    soft_limit_tokens: Optional[int] = None


class UsageItem(BaseModel):
    period: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class UsageSummary(BaseModel):
    total_tokens: int
    total_cost_usd: float
    items: List[UsageItem]


class ModelInfoOut(BaseModel):
    provider: str
    model: str
    display_name: str
    is_free_tier: bool
    is_active: bool
    context_window: Optional[int] = None
    input_token_cost_usd: Optional[float] = None
    output_token_cost_usd: Optional[float] = None

    class Config:
        from_attributes = True


# --------- Helpers (temporary auth stub) ---------
async def get_or_create_demo_user(session: AsyncSession) -> User:
    res = await session.execute(select(User).where(User.email == "demo@weev.local"))
    user = res.scalar_one_or_none()
    if user:
        return user
    user = User(email="demo@weev.local", username="demo", password_hash="!demo!")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# --------- Endpoints ---------
@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(session: AsyncSession = Depends(get_session)):
    user = await get_or_create_demo_user(session)
    res = await session.execute(select(UserSubscription).where(UserSubscription.user_id == user.id))
    sub = res.scalar_one_or_none()
    if not sub:
        sub = UserSubscription(user_id=user.id, tier="free", is_active=True)
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
    return sub


@router.post("/subscription", response_model=SubscriptionOut)
async def update_subscription(payload: SubscriptionUpdate, session: AsyncSession = Depends(get_session)):
    user = await get_or_create_demo_user(session)
    res = await session.execute(select(UserSubscription).where(UserSubscription.user_id == user.id))
    sub = res.scalar_one_or_none()
    if not sub:
        sub = UserSubscription(user_id=user.id, tier="free", is_active=True)
        session.add(sub)
        await session.flush()
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(sub, k, v)
    await session.commit()
    await session.refresh(sub)
    return sub


@router.get("/usage", response_model=UsageSummary)
async def get_usage(period: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    user = await get_or_create_demo_user(session)
    if not period:
        # current YYYY-MM
        period = datetime.utcnow().strftime("%Y-%m")

    rows = (
        await session.execute(
            select(
                TokenUsage.period,
                TokenUsage.provider,
                TokenUsage.model,
                func.sum(TokenUsage.input_tokens),
                func.sum(TokenUsage.output_tokens),
                func.sum(TokenUsage.total_tokens),
                func.sum(TokenUsage.estimated_cost_usd),
            )
            .where(TokenUsage.user_id == user.id, TokenUsage.period == period)
            .group_by(TokenUsage.period, TokenUsage.provider, TokenUsage.model)
        )
    ).all()

    items: List[UsageItem] = []
    total_tokens = 0
    total_cost = 0.0
    for r in rows:
        it = UsageItem(
            period=r[0],
            provider=r[1],
            model=r[2],
            input_tokens=int(r[3] or 0),
            output_tokens=int(r[4] or 0),
            total_tokens=int(r[5] or 0),
            estimated_cost_usd=float(r[6] or 0.0),
        )
        items.append(it)
        total_tokens += it.total_tokens
        total_cost += it.estimated_cost_usd

    return UsageSummary(total_tokens=total_tokens, total_cost_usd=round(total_cost, 6), items=items)


@router.get("/models", response_model=List[ModelInfoOut])
async def list_models(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(select(ModelProvider).where(ModelProvider.is_active == True))  # noqa: E712
    ).scalars().all()
    return rows
