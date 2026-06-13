"""READ-03/04/05/06 — the reading flow: success / honest-fail / corrective-retry (mocked LLM).

Implemented in Plan 04-05 (ReadingService orchestration). All paths inject ``fake_llm`` /
``fake_safety`` (never a real Anthropic call) and run against ``seeded_catalog`` in the
transaction-isolated ``auth_session``. The service is exercised directly (the orchestration seam)
so the locked gate→draw→generate→consume order is asserted end-to-end against the real DB:

  * **success** — mocked LLM → ``readings`` + ``reading_cards`` persisted, ``status=completed``,
    response carries every per-card field + all five summary fields (READ-03/05/06);
  * **honest-fail** — ``ValidationError`` on every attempt → ``reading=failed``, soft §9.8 body,
    limit NOT consumed, NO templated stand-in reading (READ-04 / D-09);
  * **corrective-retry** — invalid once then valid → the retry escalates Haiku→Sonnet and the
    reading completes (READ-04 / D-12).

Everything skips cleanly (via ``seeded_catalog`` → ``auth_session`` → ``_db_ready``) when
Postgres is unreachable, so the suite stays green + collectable without ``docker compose up``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Reading, ReadingCard, SpreadType, User, UserLimits
from app.models.enums import ReadingStatus
from app.schemas.reading import (
    CardInterpretation,
    ReadingCreate,
    ReadingOutput,
    ReadingSummary,
)
from app.services.llm import LLMService
from app.services.reading import SOFT_FAILURE_COPY, ReadingService
from tests.integration.conftest import FakeLLM, FakeSafety

# A normal, schema-valid request against the seeded three-card spread.
_REQ = ReadingCreate(
    question="Что мне поможет принять важное решение на этой неделе?",
    topic="choice",
    deck_slug="classic_arcana",
    spread_slug="three_keys",
)


async def _spread_position_indices(session: AsyncSession, slug: str) -> list[int]:
    """The actual seeded ``position_index`` values for a spread (the seed is 1-based, not 0-based).

    The model must echo back exactly the drawn position indices (Pitfall 3), which come from the
    spread's seeded positions — so the fake LLM output is built to match these, not a hardcoded
    0-based range.
    """
    spread = (
        await session.execute(
            select(SpreadType)
            .where(SpreadType.slug == slug)
            .options(selectinload(SpreadType.positions))
        )
    ).scalar_one()
    return sorted(p.position_index for p in spread.positions)


def _output_for_indices(indices: list[int]) -> ReadingOutput:
    """A brand-safe ``ReadingOutput`` with one card per given ``position_index`` (matches the draw)."""
    return ReadingOutput(
        cards=[
            CardInterpretation(
                position_index=idx,
                short_meaning=f"Карта в позиции {idx} говорит о тихом движении.",
                interpretation=(
                    "Сейчас ситуация только складывается. Дай ей немного времени."
                ),
                mystical_accent="Колода произносит это мягко, своим языком.",
                soft_advice="Двигайся без спешки — у этой темы есть свой ритм.",
            )
            for idx in indices
        ],
        summary=ReadingSummary(
            summary_short="Расклад о спокойном внимании к тому, что уже происходит.",
            connection="Карты складываются в общий узор о едином движении.",
            main_factor="Готовность мягко принять перемены.",
            attention_point="На чувства, которые проявляются постепенно.",
            advice="Прислушайся к себе и не торопи решения.",
            closing_phrase="Колода остаётся рядом: выбор всегда остаётся за тобой.",
        ),
    )


async def _make_user(session: AsyncSession, *, free_used: int = 0) -> User:
    """Insert a fresh user + a ``user_limits`` row (3 free/week) and return the user."""
    user = User(telegram_id=int(uuid.uuid4().int % 1_000_000_000))
    session.add(user)
    await session.flush()
    session.add(
        UserLimits(
            user_id=user.id,
            free_weekly_limit=3,
            free_used_this_week=free_used,
        )
    )
    await session.flush()
    return user


async def _limits(session: AsyncSession, user: User) -> UserLimits:
    return (
        await session.execute(select(UserLimits).where(UserLimits.user_id == user.id))
    ).scalar_one()


async def test_success(
    auth_session: AsyncSession,
    fake_safety: FakeSafety,
    seeded_catalog: dict,
) -> None:
    """READ-03/05/06: mocked LLM success → completed reading with all fields persisted."""
    user = await _make_user(auth_session)
    indices = await _spread_position_indices(auth_session, _REQ.spread_slug)
    fake_llm = FakeLLM(_output_for_indices(indices))
    service = ReadingService(safety=fake_safety, llm=fake_llm)

    result = await service.create_reading(auth_session, user, _REQ)

    # Response shape: completed, every per-card field + all five summary fields present.
    assert result.status == ReadingStatus.COMPLETED.value
    assert result.reading_id
    assert len(result.cards) == 3
    for card in result.cards:
        assert card.name  # authoritative card title from the draw
        assert card.position_title  # authoritative position title from the spread
        assert card.orientation in ("upright", "reversed")
        assert card.short_meaning
        assert card.interpretation
        assert card.deck_accent
    assert result.summary is not None
    assert result.summary.linkage
    assert result.summary.main_factor
    assert result.summary.attention
    assert result.summary.soft_advice
    assert result.summary.closing_phrase
    assert result.remaining_limits == 2  # 3 free - 1 consumed

    # Persisted state: readings completed + summary_full holds the full JSON; 3 reading_cards.
    reading = await auth_session.get(Reading, uuid.UUID(result.reading_id))
    assert reading is not None
    assert reading.status is ReadingStatus.COMPLETED
    assert reading.summary_short
    assert reading.main_factor
    assert reading.advice
    assert reading.summary_full and "connection" in reading.summary_full
    assert reading.completed_at is not None

    card_count = await auth_session.scalar(
        select(func.count())
        .select_from(ReadingCard)
        .where(ReadingCard.reading_id == reading.id)
    )
    assert card_count == 3

    # Limit consumed exactly once.
    limits = await _limits(auth_session, user)
    assert limits.free_used_this_week == 1

    # The single generation call happened once (no retry on the clean success).
    assert fake_llm.calls == 1


async def test_honest_fail(
    auth_session: AsyncSession,
    fake_safety: FakeSafety,
    seeded_catalog: dict,
) -> None:
    """READ-04/D-09: invalid JSON twice → failed, soft §9.8 body, limit NOT consumed, no stand-in."""
    user = await _make_user(auth_session)
    # Wrap the FakeLLM in the REAL LLMService retry contract so two ValidationErrors exhaust the
    # one corrective retry and surface as LLMGenerationError (the honest-fail seam).
    failing = _AlwaysInvalidClient()
    llm = LLMService(client=failing)
    service = ReadingService(safety=fake_safety, llm=llm)

    result = await service.create_reading(auth_session, user, _REQ)

    # Soft §9.8 body, status failed, NO summary content beyond the soft message.
    assert result.status == ReadingStatus.FAILED.value
    assert result.reading_id
    assert result.summary is not None
    assert result.summary.soft_advice == SOFT_FAILURE_COPY
    assert result.cards == []

    # Persisted reading is FAILED with a server-side error; NO templated reading assembled.
    reading = await auth_session.get(Reading, uuid.UUID(result.reading_id))
    assert reading is not None
    assert reading.status is ReadingStatus.FAILED
    assert reading.generation_error  # truncated server-side detail
    assert reading.summary_short is None  # no stand-in summary
    assert reading.summary_full is None

    # No interpretation text was written onto the (pending-drawn) cards — honest fail, not templated.
    rows = (
        await auth_session.execute(
            select(ReadingCard).where(ReadingCard.reading_id == reading.id)
        )
    ).scalars().all()
    assert all(row.interpretation is None for row in rows)

    # Limit UNCHANGED — retry is free (READ-10/D-09).
    limits = await _limits(auth_session, user)
    assert limits.free_used_this_week == 0
    # The model was called twice (attempt 1 Haiku + the one corrective Sonnet retry).
    assert failing.calls == 2


async def test_corrective_retry(
    auth_session: AsyncSession,
    fake_safety: FakeSafety,
    seeded_catalog: dict,
) -> None:
    """READ-04/D-12: invalid once then valid → Sonnet-escalated retry succeeds, limit consumed once."""
    user = await _make_user(auth_session)
    indices = await _spread_position_indices(auth_session, _REQ.spread_slug)
    # Real LLMService retry contract: fail once (Haiku), succeed on the Sonnet retry.
    client = _InvalidThenValidClient(_output_for_indices(indices))
    llm = LLMService(client=client)
    service = ReadingService(safety=fake_safety, llm=llm)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.COMPLETED.value
    assert len(result.cards) == 3

    reading = await auth_session.get(Reading, uuid.UUID(result.reading_id))
    assert reading is not None
    assert reading.status is ReadingStatus.COMPLETED
    # The retry escalated to Sonnet (D-12) — that resolved model is what got persisted/logged.
    assert reading.model_name == "claude-sonnet-4-6"

    # Two attempts (Haiku then the Sonnet corrective retry).
    assert client.calls == 2
    # Limit consumed exactly once on the eventual success.
    limits = await _limits(auth_session, user)
    assert limits.free_used_this_week == 1


# ---------------------------------------------------------------------------------------
# Minimal fake AsyncAnthropic clients driving the REAL LLMService retry contract.
# These let the honest-fail / corrective-retry tests exercise the genuine tenacity escalation
# (Haiku→Sonnet) + LLMGenerationError seam, with no network. A success returns a tiny stub
# carrying parsed_output / stop_reason / usage / model that LLMService unpacks.
# ---------------------------------------------------------------------------------------


class _StubUsage:
    input_tokens = 11
    output_tokens = 22


class _StubResponse:
    def __init__(self, output, model: str) -> None:
        self.parsed_output = output
        self.stop_reason = "end_turn"
        self.usage = _StubUsage()
        self.model = model


class _StubMessages:
    def __init__(self, parent: object) -> None:
        self._parent = parent

    async def parse(self, *, model: str, **_: object) -> object:
        return await self._parent._parse(model)


class _BaseFakeClient:
    """Records the resolved model per attempt so tests can assert the Haiku→Sonnet escalation."""

    def __init__(self) -> None:
        self.calls = 0
        self.models: list[str] = []
        self.messages = _StubMessages(self)

    async def _parse(self, model: str) -> object:  # pragma: no cover - overridden
        raise NotImplementedError


class _AlwaysInvalidClient(_BaseFakeClient):
    """Raise ``ValidationError`` on every attempt → exhausts the retry → ``LLMGenerationError``."""

    async def _parse(self, model: str) -> object:
        from pydantic import ValidationError

        self.calls += 1
        self.models.append(model)
        raise ValidationError.from_exception_data("ReadingOutput", [])


class _InvalidThenValidClient(_BaseFakeClient):
    """Raise once (attempt 1, Haiku) then return a valid response (attempt 2, Sonnet)."""

    def __init__(self, output) -> None:
        super().__init__()
        self._output = output

    async def _parse(self, model: str) -> object:
        from pydantic import ValidationError

        self.calls += 1
        self.models.append(model)
        if self.calls == 1:
            raise ValidationError.from_exception_data("ReadingOutput", [])
        return _StubResponse(self._output, model)
