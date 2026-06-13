"""Integration-test fixtures for the auth slice (Plan 04).

These tests exercise the real ``POST /api/auth/telegram`` -> upsert -> JWT -> Bearer round
trip against a live test database. To keep each test isolated even though the service code
calls ``session.commit()``, we use SQLAlchemy's documented "join an external transaction"
recipe: open one outer transaction on a dedicated connection, bind the session to it, and
restart a SAVEPOINT after every inner ``commit()``. At teardown the outer transaction is
rolled back, so nothing persists between tests.

The app's ``get_session`` dependency is overridden to yield this same transaction-scoped
session, so the endpoint and the test assertions see one consistent view.

Everything skips cleanly (via the shared ``_db_ready`` fixture in the root conftest) when
Postgres is unreachable, so the suite stays green + collectable without ``docker compose up``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.db import engine
from app.main import app
from app.schemas.reading import (
    CardInterpretation,
    ReadingOutput,
    ReadingSummary,
    SafetyCategory,
    SafetyVerdict,
)


@pytest.fixture
async def auth_session(_db_ready: bool) -> AsyncIterator[AsyncSession]:
    """A transaction-isolated ``AsyncSession`` that survives inner ``commit()`` calls.

    Outer transaction on one connection + auto-restarting SAVEPOINT; rolled back at teardown.
    """
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")

        try:
            yield session
        finally:
            await session.close()
            if outer.is_active:
                await outer.rollback()


@pytest.fixture
async def auth_client(auth_session: AsyncSession) -> AsyncIterator[object]:
    """In-process client with ``get_session`` overridden to the isolated test session."""
    from httpx import ASGITransport, AsyncClient

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield auth_session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------------------
# Wave-0 LLM/safety/catalog fixtures — the deterministic substrate Plans 02-06 run against.
#
# NONE of these touch Anthropic or the network. ``fake_llm`` / ``fake_safety`` are injectable
# stand-ins for the (future) ``LLMService`` / ``SafetyService`` so a later plan substitutes
# them via ``app.dependency_overrides`` and asserts status transitions / generation_logs /
# limit behaviour without a real API call. ``seeded_catalog`` reuses the real seed loader so
# the flow has genuine deck/spread/cards rows to draw from.
# ---------------------------------------------------------------------------------------


@pytest.fixture
def fake_reading_output() -> ReadingOutput:
    """A fully-populated, brand-safe ``ReadingOutput`` (one card per a 3-card spread).

    RU placeholder copy that obeys the SAFE-06 ban-list (no AI/ИИ/нейросеть/модель) and the
    non-fatalistic voice. Used as the default success payload for ``fake_llm`` and as a literal
    in flow/limit/log tests. ``position_index`` values 0..2 mirror a three-position spread.
    """
    cards = [
        CardInterpretation(
            position_index=i,
            short_meaning=f"Карта {i + 1} говорит о тихом, но важном движении.",
            interpretation=(
                "Сейчас ситуация только складывается. Дай ей немного времени и наблюдай "
                "за тем, что проявляется не сразу."
            ),
            mystical_accent="Колода произносит это мягко, своим языком.",
            soft_advice="Двигайся без спешки — у этой темы есть свой ритм.",
        )
        for i in range(3)
    ]
    return ReadingOutput(
        cards=cards,
        summary=ReadingSummary(
            summary_short="Расклад о спокойном внимании к тому, что уже происходит.",
            connection="Карты складываются в общий узор — вместе они говорят об одном движении.",
            main_factor="Готовность мягко принять перемены.",
            attention_point="На чувства, которые проявляются постепенно.",
            advice="Прислушайся к себе и не торопи решения.",
            closing_phrase="Колода остаётся рядом: выбор всегда остаётся за тобой.",
        ),
    )


class FakeLLM:
    """Injectable stand-in for the future ``LLMService`` — never calls Anthropic.

    ``generate(...)`` returns the configured ``ReadingOutput`` by default. Parametrize the
    failure modes for the honest-fail / corrective-retry paths:
      * ``raise_times=N`` — raise ``ValidationError`` on the first N calls (then succeed);
      * ``raise_times`` ≥ the retry budget models a total failure (honest fail, D-09).
    ``calls`` records how many times ``generate`` was invoked (assert no call on crisis short-circuit).
    """

    def __init__(self, output: ReadingOutput, raise_times: int = 0) -> None:
        self._output = output
        self._raise_times = raise_times
        self.calls = 0

    async def generate(self, *args: object, **kwargs: object) -> ReadingOutput:
        self.calls += 1
        if self.calls <= self._raise_times:
            # Mirror the real validation-failure surface (the corrective-retry trigger).
            from pydantic import ValidationError

            raise ValidationError.from_exception_data("ReadingOutput", [])
        return self._output


@pytest.fixture
def fake_llm(fake_reading_output: ReadingOutput) -> FakeLLM:
    """Default success ``FakeLLM``. Tests rebuild ``FakeLLM(output, raise_times=...)`` as needed."""
    return FakeLLM(fake_reading_output)


class FakeSafety:
    """Injectable stand-in for the future ``SafetyService`` — never calls Anthropic.

    ``classify(...)`` returns a ``SafetyVerdict`` with the configured category (default
    ``normal``). Parametrize to ``crisis_sensitive`` / ``abusive_or_manipulative`` / any
    ``*_sensitive`` member to exercise the gate routing (D-03/04/05/06). ``calls`` records
    invocations so a test can assert the gate ran BEFORE the draw.
    """

    def __init__(self, category: SafetyCategory = SafetyCategory.NORMAL) -> None:
        self._category = category
        self.calls = 0

    async def classify(self, *args: object, **kwargs: object) -> SafetyVerdict:
        self.calls += 1
        return SafetyVerdict(category=self._category)


@pytest.fixture
def fake_safety() -> FakeSafety:
    """Default ``normal`` ``FakeSafety``. Tests rebuild ``FakeSafety(category=...)`` as needed."""
    return FakeSafety()


async def _ensure_deck_cards(session: AsyncSession) -> int:
    """Synthesize the ``deck_cards`` style layer for every (active deck, card) pair.

    The seed JSON deliberately omits ``deck_cards`` — per ``app/seed/data/_gen_cards.py`` the
    deck imagery / style rows are a later content task, so ``run_seed`` writes only the 78
    universal ``cards``. But the backend-only draw (``CardDrawService``) selects from the active
    deck's ``deck_cards``, so the reading flow + the READ-02 draw tests need at least one active
    ``deck_cards`` row per (deck, card). This builds the minimal, style-free set (placeholder
    imagery, no deck-specific meaning — the universal meaning stays on ``cards``) so the draw has
    a real pool to shuffle. Idempotent within a test: it only inserts pairs that do not yet exist.
    """
    from sqlalchemy import select

    from app.models import Card, Deck, DeckCard

    decks = (
        await session.execute(select(Deck).where(Deck.is_active.is_(True)))
    ).scalars().all()
    cards = (await session.execute(select(Card))).scalars().all()
    existing = {
        (deck_id, card_id)
        for deck_id, card_id in (
            await session.execute(select(DeckCard.deck_id, DeckCard.card_id))
        ).all()
    }
    written = 0
    for deck in decks:
        for card in cards:
            if (deck.id, card.id) in existing:
                continue
            session.add(
                DeckCard(
                    deck_id=deck.id,
                    card_id=card.id,
                    image_url=f"https://assets.local/{deck.slug}/{card.slug}.webp",
                    thumbnail_url=f"https://assets.local/{deck.slug}/{card.slug}.thumb.webp",
                    is_active=True,
                )
            )
            written += 1
    await session.flush()
    return written


@pytest.fixture
async def seeded_catalog(auth_session: AsyncSession) -> dict[str, int]:
    """Seed the real MVP catalog into the transaction-isolated session (skips if PG is down).

    Reuses ``app.seed.loader.run_seed`` so the reading flow has genuine deck/spread/cards/
    prompt-template rows to draw from — no hand-built fixtures, one source of truth. Then
    synthesizes the ``deck_cards`` style layer (which the seed JSON omits — see
    ``_ensure_deck_cards``) so the backend-only draw has an active pool. Runs inside the
    ``auth_session`` savepoint transaction, so it is rolled back at teardown (nothing persists
    between tests). ``_db_ready`` (transitively, via ``auth_session``) skips the whole thing when
    Postgres is unreachable, mirroring the rest of the integration suite.
    """
    from app.seed.loader import run_seed

    counts = await run_seed(auth_session)
    counts["deck_cards"] = await _ensure_deck_cards(auth_session)
    await auth_session.flush()
    return counts
