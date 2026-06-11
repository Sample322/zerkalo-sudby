"""``GET /api/spreads`` + ``GET /api/spreads/recommend`` — spreads & recommendation.

Thin router: delegates to ``CatalogService``, gated by ``get_current_user`` (Bearer JWT).
``/spreads`` lists all active spreads (optionally filtered by ``topic`` / ``deck_slug``),
each with nested positions; ``/spreads/recommend`` returns one topic-aware spread plus an
in-character ``reason`` honoring ``deck_spread_compatibility`` with a deterministic fallback
(SPREAD-03/04). Both are static paths — no ``{param}`` shadowing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.catalog import RecommendationOut, SpreadOut
from app.services import catalog

router = APIRouter(tags=["spreads"])


@router.get("/spreads", response_model=list[SpreadOut])
async def list_spreads(
    topic: str | None = None,
    deck_slug: str | None = None,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SpreadOut]:
    spreads = await catalog.list_spreads(session, topic=topic, deck_slug=deck_slug)
    return [SpreadOut.model_validate(s) for s in spreads]


@router.get("/spreads/recommend", response_model=RecommendationOut)
async def recommend_spread(
    topic: str,
    deck_slug: str | None = None,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RecommendationOut:
    spread, reason = await catalog.recommend_spread(
        session, topic=topic, deck_slug=deck_slug
    )
    if spread is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no spread available")
    return RecommendationOut(
        recommended_spread=SpreadOut.model_validate(spread), reason=reason
    )


__all__ = ["router"]
