"""``GET /api/decks`` + ``GET /api/decks/{slug}`` — the deck catalog (DECK-01/02/03).

Thin router: delegates to ``CatalogService``, gated by ``get_current_user`` (Bearer JWT).
An unknown slug returns a clean ``404`` with no internal detail (T-02-03 InfoDisclosure).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.catalog import DeckDetailOut, DeckOut
from app.services import catalog

router = APIRouter(tags=["decks"])


@router.get("/decks", response_model=list[DeckOut])
async def list_decks(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DeckOut]:
    decks = await catalog.list_decks(session)
    return [DeckOut.model_validate(d) for d in decks]


@router.get("/decks/{slug}", response_model=DeckDetailOut)
async def get_deck(
    slug: str,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DeckDetailOut:
    deck = await catalog.get_deck(session, slug)
    if deck is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "deck not found")
    return DeckDetailOut.model_validate(deck)


__all__ = ["router"]
