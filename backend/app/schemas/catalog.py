"""Catalog response schemas (TZ §14.3 ``/api/decks``, §14.4 ``/api/spreads``).

Pydantic v2 ``from_attributes`` projections built straight from the ORM rows. The
DECK-04 IP boundary is enforced here by omission: deck/spread responses expose only
catalog/style fields — the universal ``cards.meaning_*`` / ``advice_*`` never appear in
any schema below, so base card meaning cannot leak through the catalog surface.

``prompt_modifier`` IS exposed (DECK-02 requires each deck to surface it); it is a
deck-level steering field, not base card meaning, so it does not cross the DECK-04 line.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DeckOut(BaseModel):
    """Public deck projection for the catalog list + carousel (DECK-01/02/03)."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    atmosphere: str | None = None
    tone: str | None = None
    prompt_modifier: str | None = None
    visual_style: dict = {}
    recommended_topics: list[str] = []
    access_type: str
    sort_order: int


class DeckDetailOut(DeckOut):
    """Deck detail (``GET /api/decks/{slug}``) — same fields as the list projection.

    Phase 2 detail needs NO cards array (DECK-04: card style/meaning is not served here).
    """


class SpreadPositionOut(BaseModel):
    """One slot of a spread (SPREAD-02) with its interpreter instruction."""

    model_config = ConfigDict(from_attributes=True)

    position_index: int
    title: str
    description: str | None = None
    prompt_instruction: str | None = None


class SpreadOut(BaseModel):
    """Spread projection with its ordered positions nested (SPREAD-01/02/03)."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    description: str | None = None
    card_count: int
    recommended_topics: list[str] = []
    positions: list[SpreadPositionOut] = []


class RecommendationOut(BaseModel):
    """Topic-aware recommendation (SPREAD-04): one spread + a human, in-character reason."""

    recommended_spread: SpreadOut
    reason: str


__all__ = [
    "DeckOut",
    "DeckDetailOut",
    "SpreadPositionOut",
    "SpreadOut",
    "RecommendationOut",
]
