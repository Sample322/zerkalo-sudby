"""``ReadingService`` — the keystone orchestration (READ-01/03/04/05/06/10/11, SAFE-01/02/03, ANALYTICS-02).

This is the moment the Core Value goes live end-to-end on the backend. ``create_reading`` owns
the ``AsyncSession`` transaction and composes every Wave-0/Wave-1 piece in the EXACT locked order
the product invariants require (RESEARCH "System Architecture Diagram"). The Phase-6 order inverts
the Phase-4 "consume last": the free slot is now consumed AS THE GATE (atomically, before the
draw), so the only post-consume non-success exit (honest-fail) must REFUND (Pitfall 2):

  1. **SAFETY GATE — BEFORE the consume-gate** (constraint 3 / D-03, the most important ordering
     invariant in the phase) — ``SafetyService.classify`` + ``route``. Running safety FIRST keeps
     the counter untouched on a safety exit (zero consume → zero refund):
       * crisis → persist a parent ``readings`` row (status=FAILED) FIRST so the NOT-NULL
         ``generation_logs.reading_id`` FK holds, write the classify log row IF a real classify
         call was made, then return the seeded refusal copy — NO consume, NO draw, limit kept;
       * abusive → same, returning the seeded redirect copy — NO consume, NO draw, limit kept;
       * ``*_sensitive`` → set a ``SAFETY_MODIFIER`` flag and continue (silent softening, D-05);
       * normal → continue;
  2. **ATOMIC FREE CONSUME-GATE** (LIMIT-02/03/04, RESEARCH Pattern 1/2/4) — ``determine_access``
     picks the bucket (free→sub→paid; only FREE populated this phase); the conditional
     ``UPDATE … WHERE … RETURNING`` (with the lazy rolling-7d reset folded in via ``case()``) is
     the indivisible check+decrement. A returned row ⇒ the slot is consumed (``remaining`` from
     the RETURNING); NO row ⇒ exhausted within a fresh window ⇒ soft §9.8 paywall body carrying
     ``reason="paywall"`` + ``reset_at`` (week_start + 7d), NO draw;
  3. **CSPRNG draw** (``CardDrawService.draw``) → persist ``readings`` (status=PENDING) + the
     immutable ``reading_cards`` rows; write the classify log row (if a call was made) against
     the now-existing reading;
  4. **PromptEngine.build** → ``(system, user, prompt_version)``; set ``readings.prompt_version``;
  5. status=GENERATING; ONE ``LLMService.generate`` call. Each attempt's audit lands in
     ``generation_logs``. On ``LLMGenerationError`` (exhausted after the corrective retry) →
     HONEST FAIL (D-09): status=FAILED, truncated ``generation_error`` (server-side only), a final
     failed log row, **REFUND the gate's consume** (``free_used_this_week -= 1``, Pitfall 2 — keeps
     READ-10), NO templated stand-in reading, return the soft §9.8 body;
  6. **brand guard** (SAFE-06) over the generated text → LOG+FLAG only (never fails the reading);
  7. **persist the mapping** (RESEARCH Pattern 3): each ``CardInterpretation`` matched BY
     ``position_index`` onto ``reading_cards.short_meaning/interpretation/mystical_accent``
     (``soft_advice`` appended into ``interpretation``); ``readings.summary_short/main_factor/
     advice`` + the full ``ReadingSummary`` JSON into ``readings.summary_full``; ``model_name``/
     ``completed_at``; status=COMPLETED;
  8. commit; build and return ``ReadingOut`` (per-card names/orientations authoritative from the
     persisted ``reading_cards``, NOT echoed by the model; all five §18 summary fields;
     ``remaining_limits`` from the consume-gate). NO consume here — the slot was already taken by
     the gate in step 2.

The collaborators (CardDrawService / SafetyService / PromptEngine / LLMService) are injected via
constructor params defaulting to the real ones — the same seam Plan 03/04 used so tests pass fakes
(``FakeLLM`` / ``FakeSafety`` via ``app.dependency_overrides``) and no real Anthropic call is ever
made. Domain errors (unknown/inactive deck or spread) raise ``ReadingInputError`` for the router to
map to 404; the soft paywall / refusal / redirect / honest-fail responses are deliberate 200
bodies carrying a ``status`` field — the global handler (``core/errors.py``) stays the last-resort
500 path (RESEARCH "Don't Hand-Roll").
"""

from __future__ import annotations

import enum
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import and_, case, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.brand_guard import contains_banned_brand_token
from app.core.config import settings
from app.models import (
    Card,
    Deck,
    DeckCard,
    GenerationLog,
    Reading,
    ReadingCard,
    SpreadPosition,
    SpreadType,
    Subscription,
    User,
    UserLimits,
)
from app.models.enums import ReadingStatus, SubscriptionStatus
from app.schemas.reading import (
    ClassifyResult,
    ReadingCardOut,
    ReadingCreate,
    ReadingListItemOut,
    ReadingOut,
    ReadingOutput,
    ReadingSummary,
    ReadingSummaryOut,
    SafetyVerdict,
)
from app.services.answer_style import normalize_answer_style
from app.services.card_draw import CardDrawService, DrawnCard
from app.services.llm import LLMGenerationError, LLMService
from app.services.prompt_engine import PromptEngine
from app.services.safety import SafetyAction, SafetyService, route

logger = logging.getLogger("app.reading")

# §9.8 — the EXACT soft failure / paywall copy ("Колода замолчала на мгновение…"). Returned as a
# deliberate 200 body (status='failed'), NEVER a stack trace — the frontend renders «Колода
# замолчала…» with Повторить + Сменить колоду (D-08).
SOFT_FAILURE_COPY = (
    "Колода замолчала на мгновение. Попробуй открыть расклад ещё раз — "
    "вопрос уже сохранён."
)

# In-character soft paywall body when the weekly free quota is exhausted (no draw, no charge).
SOFT_PAYWALL_COPY = (
    "На этой неделе бесплатные расклады закончились. Колода отдохнёт и вернётся "
    "к тебе позже."
)

# generation_logs.status values this service writes (one row per ACTUAL LLM call).
LOG_STATUS_CLASSIFY = "classify"
LOG_STATUS_COMPLETED = "completed"
LOG_STATUS_FAILED = "failed"

# Server-side cap for the stored generation_error detail (never leaked to the client).
GENERATION_ERROR_MAX_CHARS = 500

# HIST-06 history display-cap. The free tier surfaces at most the last 10 readings; this is a
# DISPLAY bound on the list query, NOT a prune — older rows stay in the DB and remain fetchable by
# id (D-04). Phase 6/7 swaps this single constant for a tier-derived limit (subscription reveals
# the full history); no tier plumbing lives here. The effective page window is bounded by
# ``min(limit, FREE_HISTORY_CAP - offset)`` so load-more (offset) can never page past the cap.
FREE_HISTORY_CAP = 10

# Per-user rolling free-limit window (D-01). The reset fires lazily-on-read when
# ``now - week_start >= WINDOW``; the same constant computes ``reset_at = week_start + WINDOW``
# for the FE countdown (D-04). One source of truth, reused by the atomic consume and the helper.
WINDOW = timedelta(days=7)


class Bucket(enum.StrEnum):
    """Which access bucket the next reading should spend (LIMIT-04, D-06, D-11).

    Order is **free → subscription → paid** (spend expiring buckets first, preserve the permanent
    ``paid_spreads_balance`` last). Phase 6 populated only ``FREE``/``NONE``; **Phase 7 fills the
    ``SUBSCRIPTION`` and ``PAID`` arms** behind the same enum (the atomic consume/refund per bucket)
    so a ЮKassa-granted pack or subscription is spendable through the exact same gate — no
    re-architecture, just the seams the module was built to accept.
    """

    FREE = "free"
    SUBSCRIPTION = "subscription"
    PAID = "paid"
    NONE = "none"


def determine_access(limits: UserLimits, now: datetime | None = None) -> Bucket:
    """Pure policy: pick the bucket the next reading spends, free → subscription → paid (D-06).

    ``FREE`` whenever the free bucket has a slot — either ``free_left > 0`` OR the window is
    **stale** (``week_start`` is set and ``<= now - WINDOW``), because a stale window resets inside
    the atomic UPDATE and therefore genuinely has a slot (RESEARCH Pattern 4 "treat stale-window as
    FREE-available"; the atomic consume is the final arbiter). A NULL ``week_start`` is NOT treated
    as a free slot here — a brand-new user has ``free_used == 0`` so ``free_left > 0`` already
    selects FREE; only the impossible NULL-with-exhausted combination would differ, and the unit
    contract (``test_none_when_exhausted`` / ``test_bucket_order``) requires NONE/SUBSCRIPTION there.

    Falls through to ``SUBSCRIPTION`` (sub units left), then ``PAID`` (paid balance), then ``NONE``.
    Pure: no session, no ``await``, no I/O. ``now`` defaults to a tz-aware ``datetime.now(UTC)`` so
    the stale comparison never subtracts a naive from an aware datetime (Pitfall 1).
    """
    moment = now if now is not None else datetime.now(UTC)
    free_left = (limits.free_weekly_limit or 0) - (limits.free_used_this_week or 0)
    window_stale = limits.week_start is not None and limits.week_start <= moment - WINDOW
    if free_left > 0 or window_stale:
        return Bucket.FREE
    subscription_left = (limits.subscription_spreads_limit or 0) - (
        limits.subscription_spreads_used or 0
    )
    if subscription_left > 0:
        return Bucket.SUBSCRIPTION
    if (limits.paid_spreads_balance or 0) > 0:
        return Bucket.PAID
    return Bucket.NONE


class ReadingInputError(Exception):
    """Unknown / inactive deck or spread — the router maps this to a clean 404 (T-02-03).

    Carries no internal detail beyond the safe ``message`` so nothing leaks across the error
    boundary; the router uses ``str(exc)`` as the public 404 detail.
    """


class _Classifier(Protocol):
    """The minimal safety-gate seam ``ReadingService`` depends on.

    The real ``SafetyService.classify`` returns a ``ClassifyResult`` (verdict + call meta); the
    test ``FakeSafety.classify`` returns a bare ``SafetyVerdict``. ``_normalize_classify`` adapts
    both, so either can be injected through the same constructor seam.
    """

    async def classify(self, question: str | None) -> object: ...


class _Generator(Protocol):
    """The minimal generation seam ``ReadingService`` depends on (``LLMService`` / ``FakeLLM``)."""

    async def generate(self, *, system: str, user_prompt: str) -> object: ...


def _normalize_classify(result: object) -> ClassifyResult:
    """Adapt either a ``ClassifyResult`` (real service) or a bare ``SafetyVerdict`` (fake) uniformly.

    A bare ``SafetyVerdict`` is treated as a regex-style decision (``via_regex=True``, ``meta=None``
    → no classify call to log), mirroring how the test fake stands in without an API call.
    """
    if isinstance(result, ClassifyResult):
        return result
    if isinstance(result, SafetyVerdict):
        return ClassifyResult(verdict=result, via_regex=True, meta=None)
    raise TypeError(f"unexpected classify result type: {type(result)!r}")


class ReadingService:
    """Compose the locked gate→draw→generate→consume order into one real persisted reading."""

    def __init__(
        self,
        *,
        card_draw: CardDrawService | None = None,
        safety: _Classifier | None = None,
        prompt_engine: PromptEngine | None = None,
        llm: _Generator | None = None,
    ) -> None:
        """Inject the collaborators (default = the real services).

        Tests substitute ``FakeSafety`` / ``FakeLLM`` here (via the router's
        ``app.dependency_overrides`` seam) so no real Anthropic call is made. The
        ``PromptEngine`` is still exercised against the seeded templates even with fakes wired,
        so the prompt-assembly + ``prompt_version`` path stays covered.
        """
        self._card_draw = card_draw or CardDrawService()
        self._safety: _Classifier = safety or SafetyService()
        self._prompt_engine = prompt_engine or PromptEngine()
        self._llm: _Generator = llm or LLMService()

    async def create_reading(
        self, session: AsyncSession, user: User, req: ReadingCreate
    ) -> ReadingOut:
        """Run the locked order and return the real ``ReadingOut`` (or a soft 200 body).

        Owns the transaction. See the module docstring for the numbered ordering. Raises
        ``ReadingInputError`` for an unknown/inactive deck or spread (router → 404); every other
        non-success exit (no quota / crisis / abusive / honest fail) returns a soft 200 body with
        ``status`` set and the limit left untouched.
        """
        deck = await self._resolve_deck(session, req.deck_slug)
        spread = await self._resolve_spread(session, req.spread_slug)
        now = datetime.now(UTC)

        # Load the user's limits row (D-02 guarantees one exists from auth; a missing row is
        # treated as "no free quota" rather than unlimited — fail-closed, see the consume gate).
        limits = await self._get_limits(session, user.id)

        # 1. SAFETY GATE — BEFORE the consume-gate (constraint 3). Running safety first keeps the
        #    counter UNTOUCHED on a crisis/abusive exit (zero consume → zero refund), so the
        #    Phase-4 test_limit_untouched_on_crisis/_abusive invariants hold under the new order.
        classify_result = _normalize_classify(await self._safety.classify(req.question))
        action = route(classify_result.verdict)

        if not action.continues_to_draw:
            # crisis → refusal, abusive → redirect. Both short-circuit with NO consume, limit kept.
            return await self._short_circuit(
                session, user, limits, action, classify_result, req, deck, spread
            )

        safety_action = (
            SafetyAction.SAFETY_MODIFIER
            if action is SafetyAction.SAFETY_MODIFIER
            else SafetyAction.GENERATE
        )

        # 2. ATOMIC FREE CONSUME-GATE (LIMIT-02/03/04) — BYPASSED for the unlimited allowlist
        #    (admin + invited testers, UNLIMITED_TELEGRAM_IDS): no decrement, no paywall, uncapped.
        #    Otherwise the conditional UPDATE…RETURNING atomically decides "got a slot?" (lazy reset
        #    folded in) BEFORE any draw; None ⇒ exhausted within a fresh window ⇒ soft paywall, NO draw.
        unlimited = settings.is_unlimited(user.telegram_id)
        remaining: int | None
        # The bucket actually consumed by the gate — threaded to the honest-fail refund so a
        # sub/paid failure refunds THAT bucket, never free (D-11, T-07-REFUND-WRONG-BUCKET). None
        # for the unlimited allowlist (nothing consumed → nothing to refund).
        consumed_bucket: Bucket | None = None
        if unlimited:
            remaining = None
        else:
            gate = await self._consume_free_gate(session, user, limits, now)
            if gate is None:
                return self._soft_body(
                    reading_id=None,
                    message=SOFT_PAYWALL_COPY,
                    remaining=0,
                    reason="paywall",
                    reset_at=self._compute_reset_at(limits.week_start if limits else None),
                )
            consumed_bucket, remaining = gate

        # 3. CSPRNG draw + persist pending + immutable reading_cards.
        # D-09 / PROF-02: the draw's reversals come from the PERSISTED user flag (default ON,
        # Phase-4 D-13), NOT the request body. ``ReadingCreate.reversals_enabled`` is still an
        # accepted field for backward compatibility, but the persisted ``user.reversals_enabled``
        # (set via PATCH /api/me/settings, 05-03) is authoritative — after opting out, every new
        # reading is upright-only. The same value is recorded onto ``readings.reversals_enabled``.
        reversals_enabled = user.reversals_enabled
        draw_records = await self._card_draw.draw(
            session,
            deck_id=deck.id,
            spread=spread,
            reversals_enabled=reversals_enabled,
        )
        reading = await self._persist_pending(
            session, user, req, deck, spread, draw_records, reversals_enabled
        )
        # Record the chosen answer style for the admin stats (normalized — unknown → default).
        reading.answer_style = normalize_answer_style(req.answer_style)

        # The classify call (if a real one happened) is now logged against the existing reading.
        await self._log_classify(session, reading.id, classify_result)

        # 4. Build the fused single-call prompt + resolve prompt_version.
        bundle = await self._prompt_engine.build(
            session,
            deck=deck,
            spread=spread,
            draw_records=draw_records,
            question=req.question,
            topic=req.topic,
            safety_action=safety_action,
            answer_style=req.answer_style,
        )
        reading.prompt_version = bundle.prompt_version

        # 5. status=GENERATING; ONE generation call (with the locked retry inside LLMService).
        reading.status = ReadingStatus.GENERATING
        await session.flush()
        try:
            output, model_name = await self._generate(
                session, reading, bundle.system, bundle.user, bundle.prompt_version
            )
        except LLMGenerationError as exc:
            # HONEST FAIL (D-09): the slot was already consumed by the gate, so REFUND it here
            # (Pitfall 2 — keeps READ-10 "limit never consumed on failure"); no templated
            # stand-in, soft §9.8 body. The refund runs in-transaction inside _honest_fail and is
            # routed to the bucket ACTUALLY consumed (free/sub/paid, D-11) via ``consumed_bucket``.
            return await self._honest_fail(
                session,
                reading,
                user,
                limits,
                exc,
                refund=not unlimited,
                consumed_bucket=consumed_bucket,
            )

        # 6. Brand guard — LOG + FLAG only (never fail the reading; RESEARCH Open Question 2).
        self._brand_guard(reading.id, output)

        # 7. Persist the single-call output onto reading_cards (by position_index) + readings.
        cards = await self._persist_output(
            session, reading, spread, draw_records, output, model_name
        )

        # 8. Commit + return the real reading (authoritative names/orientations from the rows).
        #    NO consume here — the free slot was already taken atomically by the consume-gate
        #    (step 2); ``remaining`` came from that gate's RETURNING. (Pattern 1 inverts the
        #    Phase-4 "consume last" order; only the failure paths refund.)
        await session.commit()
        return self._build_response(reading, cards, remaining)

    # ------------------------------------------------------------------ history (read-only)

    async def list_readings(
        self,
        session: AsyncSession,
        user: User,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> list[ReadingListItemOut]:
        """The user's reading history — light, newest-first, capped to the last 10 (HIST-01/02/06).

        Pure read (no writes, no commit). Scoped to ``user.id`` (the JWT identity, NEVER a body or
        query ``user_id`` — T-05-01), excluding soft-deleted rows (``deleted_at IS NULL`` — T-05-02)
        and non-``COMPLETED`` rows (failed/crisis short-circuits have no cards/summary to show, A5),
        ordered newest-first (D-01). The free tier sees at most ``FREE_HISTORY_CAP`` items: the
        effective page is bounded by ``min(limit, FREE_HISTORY_CAP - offset)`` and ``offset`` past
        the cap returns ``[]`` (T-05-05 / Pitfall 3) — the older rows are RETAINED in the DB, this
        is a display bound only.

        Two queries, no lazy loads: (1) the page of readings joined to ``Deck.title`` /
        ``SpreadType.title`` for the human deck/spread names; (2) one explicit ``select(ReadingCard)``
        joined to ``DeckCard`` to gather each reading's thumbnail URLs in ``position_index`` order
        (the established explicit-select style — no ``Reading.cards`` relationship is added, Pitfall
        1). Returns the light ``ReadingListItemOut`` items (no per-card interpretation).
        """
        # HIST-06 effective window: never page past the free cap (Pitfall 3). ``offset >= cap`` → [].
        eff = min(limit, FREE_HISTORY_CAP - offset)
        if eff <= 0:
            return []

        # (1) The page of readings + their human deck/spread names (one join query, no lazy load).
        rows = (
            await session.execute(
                select(Reading, Deck.title, SpreadType.title)
                .join(Deck, Deck.id == Reading.deck_id)
                .join(SpreadType, SpreadType.id == Reading.spread_type_id)
                .where(
                    Reading.user_id == user.id,
                    Reading.deleted_at.is_(None),
                    Reading.status == ReadingStatus.COMPLETED,
                )
                .order_by(Reading.created_at.desc())
                .offset(offset)
                .limit(eff)
            )
        ).all()
        if not rows:
            return []

        readings = [row[0] for row in rows]
        deck_names = {row[0].id: row[1] for row in rows}
        spread_names = {row[0].id: row[2] for row in rows}

        # (2) Thumbnails for exactly this page, grouped per reading in position order. Explicit
        # select(ReadingCard) joined to DeckCard — the codebase's established style (no relationship).
        thumbnails = await self._thumbnails_by_reading(
            session, [reading.id for reading in readings]
        )

        return [
            ReadingListItemOut(
                reading_id=str(reading.id),
                created_at=reading.created_at,
                question=reading.question or None,
                deck_name=deck_names.get(reading.id, ""),
                spread_name=spread_names.get(reading.id, ""),
                card_thumbnails=thumbnails.get(reading.id, []),
                summary_short=reading.summary_short,
            )
            for reading in readings
        ]

    @staticmethod
    async def _thumbnails_by_reading(
        session: AsyncSession, reading_ids: list[object]
    ) -> dict[object, list[str]]:
        """Map ``reading_id`` → its drawn-card thumbnail URLs in ``position_index`` order.

        One explicit ``select(ReadingCard)`` joined to ``DeckCard`` for the whole page (no per-row
        query, no lazy relationship — Pitfall 1). Rows are grouped in Python and each reading's
        thumbnails are emitted in ``position_index`` order so the miniatures line up with the spread.
        """
        if not reading_ids:
            return {}
        card_rows = (
            await session.execute(
                select(
                    ReadingCard.reading_id,
                    ReadingCard.position_index,
                    DeckCard.thumbnail_url,
                )
                .join(DeckCard, DeckCard.id == ReadingCard.deck_card_id)
                .where(ReadingCard.reading_id.in_(reading_ids))
                .order_by(ReadingCard.reading_id, ReadingCard.position_index)
            )
        ).all()
        grouped: dict[object, list[str]] = {}
        for reading_id, _position_index, thumbnail_url in card_rows:
            grouped.setdefault(reading_id, []).append(thumbnail_url)
        return grouped

    # ------------------------------------------------------------------ detail / delete / restore

    async def get_reading_detail(
        self, session: AsyncSession, user: User, reading_id: object
    ) -> ReadingOut:
        """Return the IMMUTABLE stored reading by id (HIST-03) — reused, never regenerated.

        The reading is read back exactly as it was originally generated: the persisted
        ``reading_cards`` (short_meaning/interpretation/mystical_accent) + the ``summary_full``
        JSON, mapped through the SAME ``_build_response`` the create path uses, so two GETs return
        an identical body and ``ResultScreen`` renders it via the same ``ReadingOut`` contract.
        There is NO LLM call and NO re-draw here.

        Scoped to ``user.id`` (the JWT identity, NEVER a body — T-05-IDOR) and excluding
        soft-deleted rows (``deleted_at IS NULL`` — Pitfall 4): a reading owned by another user OR
        an already-deleted one raises ``ReadingInputError`` → the router maps it to a 404 (not 403
        — a non-owned id must be indistinguishable from a non-existent one, no existence leak).
        """
        reading = (
            await session.execute(
                select(Reading).where(
                    Reading.id == reading_id,
                    Reading.user_id == user.id,
                    Reading.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if reading is None:
            raise ReadingInputError("reading not found")

        # The reading's immutable cards, in position order (explicit select — no lazy relationship,
        # Pitfall 1; the established style mirrors ``_persist_output``/``list_readings``).
        cards = (
            await session.execute(
                select(ReadingCard)
                .where(ReadingCard.reading_id == reading.id)
                .order_by(ReadingCard.position_index)
            )
        ).scalars().all()

        # Reconstruct the authoritative transient labels ``_build_response`` reads: card titles
        # from ``cards.title`` (by ``reading_cards.card_id``) and position titles from
        # ``spread_positions.title`` (by ``reading_cards.position_id``). Both via one explicit
        # ``select`` each — never a fresh draw, never a lazy load.
        card_titles = await self._titles_by_id(
            session, Card, [card.card_id for card in cards]
        )
        position_titles = await self._titles_by_id(
            session, SpreadPosition, [card.position_id for card in cards]
        )
        for card in cards:
            card._card_title = card_titles.get(card.card_id, "")  # noqa: SLF001 - transient label
            card._position_title = position_titles.get(  # noqa: SLF001 - transient label
                card.position_id, ""
            )

        # Detail does not consume a quota (remaining=None) — it is a pure read of a frozen reading.
        return self._build_response(reading, list(cards), remaining=None)

    @staticmethod
    async def _titles_by_id(
        session: AsyncSession, model: type, ids: list[object]
    ) -> dict[object, str]:
        """Map ``id`` → ``title`` for ``Card``/``SpreadPosition`` over the detail's drawn rows.

        One explicit ``select(model.id, model.title)`` for the whole reading (no per-row query, no
        lazy relationship). Used to rebuild the authoritative card/position labels the immutable
        ``_build_response`` mapper expects, sourced from the persisted joins (not a fresh draw).
        """
        if not ids:
            return {}
        rows = (
            await session.execute(
                select(model.id, model.title).where(model.id.in_(ids))
            )
        ).all()
        return {row[0]: row[1] for row in rows}

    async def soft_delete(
        self, session: AsyncSession, user: User, reading_id: object
    ) -> None:
        """Soft-delete the user's reading (HIST-04) — set ``deleted_at``, never a hard delete.

        Scoped to ``user.id`` (T-05-IDOR): a non-owned OR already-deleted id raises
        ``ReadingInputError`` → 404, so one user can neither delete nor probe another's reading,
        and a double-delete is a clean 404. The row is RETAINED with a timestamp (D-04) so it can
        be restored within the undo window; it simply disappears from the list and detail 404s.
        """
        reading = (
            await session.execute(
                select(Reading).where(
                    Reading.id == reading_id,
                    Reading.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if reading is None or reading.deleted_at is not None:
            raise ReadingInputError("reading not found")
        # deleted_at is TIMESTAMP WITHOUT TIME ZONE (naive) — asyncpg rejects a tz-aware value.
        reading.deleted_at = datetime.now(UTC).replace(tzinfo=None)
        await session.commit()

    async def restore(
        self, session: AsyncSession, user: User, reading_id: object
    ) -> None:
        """Restore a soft-deleted reading (D-03 undo) — null ``deleted_at`` on the user's row.

        Scoped to ``user.id`` (T-05-IDOR): a non-owned id raises ``ReadingInputError`` → 404, so a
        user can never restore another's reading. Restoring an already-active reading is a no-op
        (``deleted_at`` is set back to None either way); the reading reappears in the list.
        """
        reading = (
            await session.execute(
                select(Reading).where(
                    Reading.id == reading_id,
                    Reading.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if reading is None:
            raise ReadingInputError("reading not found")
        reading.deleted_at = None
        await session.commit()

    # ------------------------------------------------------------------ resolution / quota

    async def _resolve_deck(self, session: AsyncSession, slug: str) -> Deck:
        """One active deck by slug (Pitfall 5: plain ``select()``); unknown/inactive → 404 seam."""
        deck = (
            await session.execute(
                select(Deck).where(Deck.slug == slug, Deck.is_active.is_(True))
            )
        ).scalar_one_or_none()
        if deck is None:
            raise ReadingInputError("deck not found")
        return deck

    async def _resolve_spread(self, session: AsyncSession, slug: str) -> SpreadType:
        """One active spread by slug with positions eager-loaded (Pitfall 5 — no lazy load)."""
        spread = (
            await session.execute(
                select(SpreadType)
                .where(SpreadType.slug == slug, SpreadType.is_active.is_(True))
                .options(selectinload(SpreadType.positions))
            )
        ).scalar_one_or_none()
        if spread is None:
            raise ReadingInputError("spread not found")
        return spread

    @staticmethod
    async def _get_limits(session: AsyncSession, user_id: object) -> UserLimits | None:
        """Read the user's ``user_limits`` row (None for a user without one — treated as quota)."""
        return (
            await session.execute(
                select(UserLimits).where(UserLimits.user_id == user_id)
            )
        ).scalar_one_or_none()

    @staticmethod
    def _remaining(limits: UserLimits | None) -> int | None:
        """Remaining free units for the §14.5 ``remaining_limits`` field (None if no row)."""
        if limits is None:
            return None
        return max(0, (limits.free_weekly_limit or 0) - (limits.free_used_this_week or 0))

    @staticmethod
    async def _consume_free_atomic(
        session: AsyncSession, user_id: object, now: datetime
    ) -> tuple[int, int] | None:
        """One indivisible reset+check+increment+re-anchor for the FREE bucket (LIMIT-02/03).

        THE atomicity control for success-criterion 3 (RESEARCH Pattern 1). A single conditional
        ``UPDATE user_limits … WHERE … RETURNING`` folds the lazy rolling-7d reset (Pattern 2) into
        the same statement via ``case()`` — PostgreSQL holds a row lock for the statement, so two
        concurrent calls at the boundary serialize: one increments to the limit, the other matches
        zero rows. The four states collapse:

          * **stale** (``week_start`` set and ``<= now - WINDOW``) → ``free_used=1`` + re-anchor
            ``week_start=now`` (reset and immediately count this reading);
          * **first_ever** (``week_start IS NULL``, D-02) → ``free_used=1`` + anchor ``week_start=now``;
          * **fresh_has_room** (within window and ``free_used < limit``) → ``free_used += 1``,
            ``week_start`` unchanged;
          * **fresh, no room** → no WHERE arm matches → 0 rows → ``None`` (the paywall trigger).

        Returns ``(used, limit)`` on a consumed slot, ``None`` when no row matched. "No slot" is
        detected via the RETURNING row being absent (``.first() is None``), never via the cursor
        row-count (unreliable with RETURNING on asyncpg — Pattern 1 caveat). No pessimistic
        row-lock SELECT and no application lock: the conditional UPDATE's own row lock IS the
        serialization across connections.

        The ``stale`` / ``fresh_has_room`` / ``first_ever`` predicate objects are defined ONCE and
        reused in BOTH the WHERE ``or_()`` and the SET ``case()`` so the boundary logic cannot drift
        (Pitfall 5). ``now`` must be tz-aware (``datetime.now(UTC)``) — ``week_start`` is TIMESTAMP
        with tz after migration 0002, so a naive ``now`` would raise on the subtraction (Pitfall 1).
        """
        stale = and_(
            UserLimits.week_start.is_not(None),
            UserLimits.week_start <= now - WINDOW,
        )
        fresh_has_room = and_(
            UserLimits.week_start.is_not(None),
            UserLimits.week_start > now - WINDOW,
            UserLimits.free_used_this_week < UserLimits.free_weekly_limit,
        )
        first_ever = UserLimits.week_start.is_(None)

        stmt = (
            update(UserLimits)
            .where(UserLimits.user_id == user_id)
            .where(or_(stale, first_ever, fresh_has_room))
            .values(
                free_used_this_week=case(
                    (stale, 1),
                    (first_ever, 1),
                    else_=UserLimits.free_used_this_week + 1,
                ),
                week_start=case(
                    (stale, now),
                    (first_ever, now),
                    else_=UserLimits.week_start,
                ),
            )
            .returning(UserLimits.free_used_this_week, UserLimits.free_weekly_limit)
        )
        row = (await session.execute(stmt)).first()  # None ⇒ no slot ⇒ paywall
        return (row[0], row[1]) if row is not None else None

    @staticmethod
    async def _consume_subscription_atomic(
        session: AsyncSession, user_id: object, now: datetime
    ) -> bool:
        """Atomically consume one SUBSCRIPTION unit — window-gated per the Plan-03 D-09 contract.

        A subscription is **WINDOW-GATED, NOT count-gated**: the real bound is the 30-day window
        (``Subscription.current_period_end``, selected by ``determine_access`` before we get here),
        and Plan 03's grant sets ``subscription_spreads_limit = SUBSCRIPTION_WINDOW_UNLIMITED`` +
        resets ``subscription_spreads_used = 0`` each period. This count-atomic conditional
        ``UPDATE … WHERE subscription_spreads_used < subscription_spreads_limit … RETURNING`` exists
        ONLY so the PostgreSQL row lock serializes concurrent reads (the same exactly-once discipline
        the free bucket uses) — inside a live window the ``_used < _limit`` invariant the grant
        guarantees is always satisfiable, so this never blocks a real subscriber. Mirrors
        ``_consume_free_atomic``: "no slot" is the RETURNING row being absent (``.first() is None``),
        never a rowcount.

        Does NOT re-import or re-define ``SUBSCRIPTION_WINDOW_UNLIMITED`` (owned by
        ``services/payments.py``, D-09); the gate relies solely on the ``_used < _limit`` invariant
        the grant writes. Returns ``True`` when a unit was consumed, ``False`` when none was available.
        """
        row = (
            await session.execute(
                update(UserLimits)
                .where(
                    UserLimits.user_id == user_id,
                    UserLimits.subscription_spreads_used
                    < UserLimits.subscription_spreads_limit,
                )
                .values(
                    subscription_spreads_used=UserLimits.subscription_spreads_used + 1
                )
                .returning(
                    UserLimits.subscription_spreads_used,
                    UserLimits.subscription_spreads_limit,
                )
            )
        ).first()
        return row is not None

    @staticmethod
    async def _consume_paid_atomic(
        session: AsyncSession, user_id: object, now: datetime
    ) -> int | None:
        """Atomically decrement one PAID spread — the permanent balance spent LAST (D-11).

        A single conditional ``UPDATE … WHERE paid_spreads_balance > 0 … RETURNING`` (mirrors
        ``_consume_free_atomic``): the PG row lock serializes concurrent reads so the balance can
        never over-spend at the boundary (T-07-OVERSPEND). "No slot" is the absent RETURNING row
        (``.first() is None``), never a rowcount. Returns the **post-decrement** balance on a
        consumed spread (so the caller can surface it as ``remaining_limits``), ``None`` when the
        balance was already 0.
        """
        row = (
            await session.execute(
                update(UserLimits)
                .where(
                    UserLimits.user_id == user_id,
                    UserLimits.paid_spreads_balance > 0,
                )
                .values(paid_spreads_balance=UserLimits.paid_spreads_balance - 1)
                .returning(UserLimits.paid_spreads_balance)
            )
        ).first()
        return row[0] if row is not None else None

    async def _consume_free_gate(
        self,
        session: AsyncSession,
        user: User,
        limits: UserLimits | None,
        now: datetime,
    ) -> tuple[Bucket, int | None] | None:
        """Pick the bucket (``determine_access``) and run its atomic consume — the create-path gate.

        Routes each bucket to its own atomic consume, in the D-11 order **free → subscription →
        paid** (``determine_access`` already returns them in that priority):

          * ``Bucket.FREE`` → ``_consume_free_atomic`` (self-handles stale/first-ever/exhausted) →
            ``(FREE, remaining)`` where ``remaining = max(0, limit - used)`` (the free display value);
          * ``Bucket.SUBSCRIPTION`` → ``_consume_subscription_atomic`` (window-gated per the Plan-03
            D-09 contract) → ``(SUBSCRIPTION, None)`` (a count is meaningless — the window, not a
            number, is the bound; the FE shows «безлимит», so no remaining count is surfaced);
          * ``Bucket.PAID`` → ``_consume_paid_atomic`` → ``(PAID, new_balance)`` (the post-decrement
            paid balance as the remaining value);
          * ``Bucket.NONE`` → ``None`` (paywall).

        Each arm is an atomic conditional ``UPDATE … RETURNING`` — never a ``SELECT``-then-``UPDATE``
        and never a rowcount ("no slot" is always the absent RETURNING row); the PG row lock is the
        cross-connection serialization (T-07-OVERSPEND, the verified Phase-6 free-quota control). The
        returned ``Bucket`` tag is threaded out so ``create_reading`` can route the honest-fail refund
        to the bucket that was ACTUALLY consumed (Task 2 / T-07-REFUND-WRONG-BUCKET).

        A MISSING ``user_limits`` row (``limits is None``) is **fail-closed** → ``None`` (paywall):
        D-02 guarantees a row at auth, so a missing row is anomalous, and granting a free reading on
        a missing row would re-open the Phase-4 "no row → unlimited" gap. Returns ``None`` when the
        selected bucket had no slot (a lost race at the boundary falls through to paywall).
        """
        if limits is None:
            return None
        bucket = determine_access(limits, now)
        # CR-01: ``determine_access`` sees only ``UserLimits`` (no window column), so it picks
        # SUBSCRIPTION on the count bucket alone — which the grant pins at ``SUBSCRIPTION_WINDOW_
        # UNLIMITED``. The REAL bound is ``Subscription.current_period_end``, and NOTHING zeroes the
        # bucket on natural expiry / failed renewal / cancel-then-lapse. Without this guard a lapsed
        # subscriber would read forever. When the count bucket is picked but no live ACTIVE+unexpired
        # window exists, lazily zero the bucket (mirrors the free lazy-reset — idempotent) and re-pick
        # the bucket WITHOUT the expired subscription (→ PAID if any paid balance, else NONE/paywall).
        if bucket is Bucket.SUBSCRIPTION and not await self._subscription_window_live(
            session, user.id, now
        ):
            await self._expire_subscription_bucket(session, user.id)
            bucket = (
                Bucket.PAID if (limits.paid_spreads_balance or 0) > 0 else Bucket.NONE
            )
        if bucket is Bucket.FREE:
            consumed = await self._consume_free_atomic(session, user.id, now)
            if consumed is None:
                return None
            used, limit = consumed
            return (Bucket.FREE, max(0, limit - used))
        if bucket is Bucket.SUBSCRIPTION:
            if await self._consume_subscription_atomic(session, user.id, now):
                # Window-gated: no meaningful count to surface (the window is the bound, D-09).
                return (Bucket.SUBSCRIPTION, None)
            return None
        if bucket is Bucket.PAID:
            new_balance = await self._consume_paid_atomic(session, user.id, now)
            if new_balance is None:
                return None
            return (Bucket.PAID, new_balance)
        # Bucket.NONE → exhausted across every bucket → soft paywall (no draw).
        return None

    @staticmethod
    async def _subscription_window_live(
        session: AsyncSession, user_id: object, now: datetime
    ) -> bool:
        """True iff the user has an ACTIVE subscription whose window has NOT lapsed (D-09 real bound).

        The subscription entitlement is window-gated (``Subscription.current_period_end``), NOT
        count-gated — but ``UserLimits`` carries no window column, so the gate must consult the
        ``subscriptions`` row here. ``current_period_end`` is tz-aware (``TIMESTAMP(timezone=True)``)
        and ``now`` is tz-aware (``datetime.now(UTC)``), so the compare never mixes naive/aware.
        """
        return (
            await session.execute(
                select(Subscription.id).where(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.current_period_end > now,
                )
            )
        ).first() is not None

    @staticmethod
    async def _expire_subscription_bucket(
        session: AsyncSession, user_id: object
    ) -> None:
        """Zero the D-09 subscription bucket once its window has lapsed (CR-01, idempotent).

        Natural expiry, a failed renewal (→ PAYMENT_FAILED), and a cancel-then-lapse all leave
        ``subscription_spreads_limit`` at ``SUBSCRIPTION_WINDOW_UNLIMITED`` — only a refund ever zeroed
        it. This lazy-zero (mirrors the free lazy-reset) fires the first time the gate sees the count
        bucket without a live window, so the lapsed entitlement is never spent AND ``/api/me`` stops
        reporting it as spendable. Idempotent: a re-run on an already-zero bucket is a no-op UPDATE.
        """
        await session.execute(
            update(UserLimits)
            .where(UserLimits.user_id == user_id)
            .values(subscription_spreads_limit=0, subscription_spreads_used=0)
        )

    @staticmethod
    async def _refund_free(session: AsyncSession, user_id: object) -> None:
        """Compensating refund of one FREE unit after a post-consume non-success exit (Pitfall 2).

        Because ``_consume_free_atomic`` consumes the slot AS THE GATE (before the draw), every
        post-consume early exit (honest-fail) MUST refund so the net counter is unchanged and
        READ-10 ("limit never consumed on failure") holds. Runs in the SAME transaction as the
        consume, before the soft-body return. Phase 7 refunds sub/paid analogously behind ``Bucket``.
        """
        await session.execute(
            update(UserLimits)
            .where(UserLimits.user_id == user_id)
            .values(free_used_this_week=UserLimits.free_used_this_week - 1)
        )

    @staticmethod
    async def _refund_subscription(session: AsyncSession, user_id: object) -> None:
        """Compensating refund of one SUBSCRIPTION unit after a post-consume honest fail (D-11).

        Mirrors ``_refund_free``: an atomic ``UPDATE … subscription_spreads_used -= 1`` in the SAME
        transaction as the consume, before the soft-body return, so the net counter is unchanged and
        READ-10 holds for a subscription-paid attempt that honest-fails. (Because the subscription is
        window-gated, this is bookkeeping symmetry — the window still bounds access — but it keeps
        the count consistent so the gate's concurrency invariant never drifts.)
        """
        await session.execute(
            update(UserLimits)
            .where(UserLimits.user_id == user_id)
            .values(
                subscription_spreads_used=UserLimits.subscription_spreads_used - 1
            )
        )

    @staticmethod
    async def _refund_paid(session: AsyncSession, user_id: object) -> None:
        """Compensating refund of one PAID spread after a post-consume honest fail (D-11, READ-10).

        Mirrors ``_refund_free``: an atomic ``UPDATE … paid_spreads_balance += 1`` in the SAME
        transaction as the consume, before the soft-body return, so a paid-paid attempt that
        honest-fails gives the permanent spread back (net unchanged) — refunding the paid bucket, NOT
        free (T-07-REFUND-WRONG-BUCKET). The gate only decrements a positive balance, so the give-back
        is always to a balance that was just spent.
        """
        await session.execute(
            update(UserLimits)
            .where(UserLimits.user_id == user_id)
            .values(paid_spreads_balance=UserLimits.paid_spreads_balance + 1)
        )

    async def _refund_consumed_bucket(
        self, session: AsyncSession, user_id: object, bucket: Bucket | None
    ) -> None:
        """Route a compensating refund to the bucket that was ACTUALLY consumed (D-11, Task 2).

        FREE → ``_refund_free``, SUBSCRIPTION → ``_refund_subscription``, PAID → ``_refund_paid``.
        ``None`` (unlimited allowlist — nothing was consumed) and ``Bucket.NONE`` (paywall — never
        reaches an honest fail) are a no-op: refunding a bucket that was not spent is exactly the bug
        this routing guards (T-07-REFUND-WRONG-BUCKET).
        """
        if bucket is Bucket.FREE:
            await self._refund_free(session, user_id)
        elif bucket is Bucket.SUBSCRIPTION:
            await self._refund_subscription(session, user_id)
        elif bucket is Bucket.PAID:
            await self._refund_paid(session, user_id)
        # None / Bucket.NONE → nothing consumed → nothing to refund.

    @staticmethod
    def _compute_reset_at(week_start: datetime | None) -> datetime | None:
        """The per-user free-limit reopen moment = ``week_start + WINDOW`` (None → None).

        Surfaced on the paywall body so the FE renders the D-04 countdown («вернутся через N»). A
        NULL ``week_start`` (no window anchored yet) returns None — but the paywall only fires within
        a fresh exhausted window, where ``week_start`` is always set.
        """
        return (week_start + WINDOW) if week_start is not None else None

    # ------------------------------------------------------------------ persistence

    @staticmethod
    async def _persist_pending(
        session: AsyncSession,
        user: User,
        req: ReadingCreate,
        deck: Deck,
        spread: SpreadType,
        draw_records: list[DrawnCard],
        reversals_enabled: bool,
    ) -> Reading:
        """Create the ``readings`` row (PENDING) + the immutable ``reading_cards`` from the draw.

        ``len(draw_records)`` MUST equal the spread's ``card_count`` (Pitfall 3 — validate the
        count before persisting). The interpretation columns are left NULL here; they are filled
        from the single-call output in ``_persist_output`` (Pattern 3 — cards persisted before
        generation). ``reversals_enabled`` is the value ACTUALLY used for the draw (the persisted
        ``user.reversals_enabled`` per D-09), recorded so ``readings.reversals_enabled`` reflects
        what was drawn, not the request body.
        """
        if len(draw_records) != spread.card_count:
            raise ReadingInputError("draw did not match the spread card count")

        reading = Reading(
            user_id=user.id,
            question=req.question or "",
            topic=req.topic,
            deck_id=deck.id,
            spread_type_id=spread.id,
            status=ReadingStatus.PENDING,
            reversals_enabled=reversals_enabled,
        )
        session.add(reading)
        await session.flush()  # assign reading.id for the FK + the classify log row

        for record in draw_records:
            session.add(
                ReadingCard(
                    reading_id=reading.id,
                    card_id=record.card_id,
                    deck_card_id=record.deck_card_id,
                    position_id=record.position_id,
                    position_index=record.position_index,
                    orientation=record.orientation,
                )
            )
        await session.flush()
        return reading

    async def _persist_output(
        self,
        session: AsyncSession,
        reading: Reading,
        spread: SpreadType,
        draw_records: list[DrawnCard],
        output: ReadingOutput,
        model_name: str | None,
    ) -> list[ReadingCard]:
        """Map the single ``ReadingOutput`` onto the persisted rows BY ``position_index`` (Pitfall 3).

        Validates exactly one ``CardInterpretation`` per drawn ``position_index`` (no list-order
        reliance), folds ``soft_advice`` into ``reading_cards.interpretation``, denormalizes
        ``summary_short``/``main_factor``/``advice`` onto ``readings`` and serializes the FULL
        ``ReadingSummary`` JSON losslessly into ``readings.summary_full``. Sets ``model_name`` /
        ``completed_at`` and flips status to COMPLETED. Returns the persisted ``reading_cards`` in
        ``position_index`` order (the authoritative response source — card names from the draw and
        position titles from the spread, NOT the model echo).
        """
        by_index = {card.position_index: card for card in output.cards}
        expected = {record.position_index for record in draw_records}
        if by_index.keys() != expected:
            # The model returned the wrong set/count of position indices — treat as a bad shape.
            raise LLMGenerationError(
                f"model returned indices {sorted(by_index)} != drawn {sorted(expected)}"
            )

        rows = (
            await session.execute(
                select(ReadingCard).where(ReadingCard.reading_id == reading.id)
            )
        ).scalars().all()
        rows_by_index = {row.position_index: row for row in rows}
        # Authoritative labels: card titles from the immutable draw, position titles from the
        # spread — never the model output (T-04: names/orientations are server-side).
        titles = {record.position_index: record.card_title for record in draw_records}
        position_titles = {p.position_index: p.title for p in spread.positions}

        for index, interp in by_index.items():
            row = rows_by_index[index]
            row.short_meaning = interp.short_meaning
            row.interpretation = self._fold_soft_advice(
                interp.interpretation, interp.soft_advice
            )
            row.mystical_accent = interp.mystical_accent

        summary = output.summary
        reading.summary_short = summary.summary_short
        reading.main_factor = summary.main_factor
        reading.advice = summary.advice
        reading.summary_full = self._serialize_summary(summary)
        reading.model_name = model_name
        reading.status = ReadingStatus.COMPLETED
        # completed_at is TIMESTAMP WITHOUT TIME ZONE (naive) — asyncpg rejects a tz-aware value.
        reading.completed_at = datetime.now(UTC).replace(tzinfo=None)
        await session.flush()

        ordered = sorted(rows, key=lambda r: r.position_index)
        # Attach the authoritative labels for the response (transient, not DB columns).
        for row in ordered:
            row._card_title = titles.get(row.position_index, "")  # noqa: SLF001 - transient label
            row._position_title = position_titles.get(  # noqa: SLF001 - transient label
                row.position_index, ""
            )
        return ordered

    @staticmethod
    def _fold_soft_advice(interpretation: str, soft_advice: str) -> str:
        """Append ``soft_advice`` as a final sentence of the interpretation (Pattern 1 mapping).

        ``reading_cards`` has no dedicated ``soft_advice`` column, so the advice is kept visible on
        the result screen by folding it into ``interpretation`` (RESEARCH-recommended, zero schema
        change). An empty advice leaves the interpretation untouched.
        """
        advice = (soft_advice or "").strip()
        if not advice:
            return interpretation
        return f"{interpretation.rstrip()} {advice}"

    @staticmethod
    def _serialize_summary(summary: ReadingSummary) -> str:
        """Serialize the full ``ReadingSummary`` to a JSON string for lossless ``summary_full``.

        Preserves every §18 field (incl. ``connection`` / ``attention_point`` / ``closing_phrase``
        that have no dedicated column) so the result screen + future history are complete.
        """
        return json.dumps(summary.model_dump(), ensure_ascii=False)

    # ------------------------------------------------------------------ generation + logs

    async def _generate(
        self,
        session: AsyncSession,
        reading: Reading,
        system: str,
        user_prompt: str,
        prompt_version: str,
    ) -> tuple[ReadingOutput, str | None]:
        """Run the one generation call, log the attempt, and return ``(output, model_name)``.

        ``LLMService.generate`` owns the corrective retry internally and either returns a
        ``GenerationResult`` (real) / ``ReadingOutput`` (fake) or raises ``LLMGenerationError`` on
        exhaustion. A success writes one ``generation_logs`` row (status ``completed``) with the
        call's model/tokens/latency; the honest-fail log row is written by ``_honest_fail``.
        """
        result = await self._llm.generate(system=system, user_prompt=user_prompt)
        output, meta = self._unpack_generation(result)
        session.add(
            GenerationLog(
                reading_id=reading.id,
                prompt_template_version=prompt_version,
                model_name=meta.get("model_name"),
                input_tokens=meta.get("input_tokens"),
                output_tokens=meta.get("output_tokens"),
                latency_ms=meta.get("latency_ms"),
                status=LOG_STATUS_COMPLETED,
            )
        )
        await session.flush()
        return output, meta.get("model_name")

    @staticmethod
    def _unpack_generation(result: object) -> tuple[ReadingOutput, dict]:
        """Adapt a real ``GenerationResult`` or a bare ``ReadingOutput`` (fake) to ``(output, meta)``.

        The real ``LLMService`` returns a ``GenerationResult`` carrying the audit metadata; the
        test ``FakeLLM`` returns the ``ReadingOutput`` directly (no meta → zeros logged).
        """
        if isinstance(result, ReadingOutput):
            return result, {}
        output = getattr(result, "output", None)
        if not isinstance(output, ReadingOutput):
            raise TypeError(f"unexpected generation result type: {type(result)!r}")
        return output, {
            "model_name": getattr(result, "model_name", None),
            "input_tokens": getattr(result, "input_tokens", None),
            "output_tokens": getattr(result, "output_tokens", None),
            "latency_ms": getattr(result, "latency_ms", None),
        }

    async def _log_classify(
        self, session: AsyncSession, reading_id: object, result: ClassifyResult
    ) -> None:
        """Write the classify ``generation_logs`` row ONLY when an actual classify call was made.

        ``meta is None`` (regex / empty short-circuit) → no LLM call happened → nothing to log
        (ANALYTICS-02 counts ACTUAL calls). When a call was made, log its model/tokens/latency
        with status ``classify`` against the (already-persisted) reading.
        """
        meta = result.meta
        if meta is None:
            return
        session.add(
            GenerationLog(
                reading_id=reading_id,
                model_name=meta.model_name,
                input_tokens=meta.input_tokens,
                output_tokens=meta.output_tokens,
                latency_ms=meta.latency_ms,
                status=LOG_STATUS_CLASSIFY,
            )
        )
        await session.flush()

    @staticmethod
    def _brand_guard(reading_id: object, output: ReadingOutput) -> None:
        """SAFE-06 LOG+FLAG guard over the generated text — never fails the reading (Open Q2).

        Scans every per-card field + every summary field for a banned brand token
        (AI/нейросеть/модель/ИИ); a hit is logged + flagged for observability, and the completed
        reading is still delivered (a brand slip is rare and far less bad than an honest fail).
        """
        fragments: list[str] = []
        for card in output.cards:
            fragments += [
                card.short_meaning,
                card.interpretation,
                card.mystical_accent,
                card.soft_advice,
            ]
        summary = output.summary
        fragments += [
            summary.summary_short,
            summary.connection,
            summary.main_factor,
            summary.attention_point,
            summary.advice,
            summary.closing_phrase,
        ]
        if any(contains_banned_brand_token(fragment) for fragment in fragments):
            logger.warning(
                "brand_guard_flag",
                extra={"event": "reading.brand_flag", "reading_id": str(reading_id)},
            )

    # ------------------------------------------------------------------ non-success exits

    async def _short_circuit(
        self,
        session: AsyncSession,
        user: User,
        limits: UserLimits | None,
        action: SafetyAction,
        classify_result: ClassifyResult,
        req: ReadingCreate,
        deck: Deck,
        spread: SpreadType,
    ) -> ReadingOut:
        """Crisis/abusive exit: persist a FAILED parent reading, log classify, return refusal/redirect.

        The parent ``readings`` row is persisted FIRST (status=FAILED) because
        ``generation_logs.reading_id`` is a NOT-NULL FK — the classify log row (written only when a
        real classify call was made) needs a valid ``reading_id``, and it gives the refusal/redirect
        a ``reading_id`` to return. NO draw (zero ``reading_cards``), NO generation, limit kept
        (D-03/D-06/SAFE-03). The reading is committed so the row + any classify log persist.
        """
        reading = Reading(
            user_id=user.id,
            question=req.question or "",
            topic=req.topic,
            deck_id=deck.id,
            spread_type_id=spread.id,
            status=ReadingStatus.FAILED,
            # D-09: even on a no-draw short-circuit, record the persisted user flag (the request
            # body is never authoritative for reversals), keeping the column consistent.
            reversals_enabled=user.reversals_enabled,
        )
        session.add(reading)
        await session.flush()

        await self._log_classify(session, reading.id, classify_result)

        if action is SafetyAction.REFUSAL:
            message = await self._prompt_engine.refusal_copy(session)
        else:
            message = await self._prompt_engine.redirect_copy(session)

        await session.commit()
        return self._soft_body(
            reading_id=str(reading.id),
            message=message,
            remaining=self._remaining(limits),
        )

    async def _honest_fail(
        self,
        session: AsyncSession,
        reading: Reading,
        user: User,
        limits: UserLimits | None,
        exc: LLMGenerationError,
        *,
        refund: bool = True,
        consumed_bucket: Bucket | None = None,
    ) -> ReadingOut:
        """Honest fail (D-09): status=FAILED, REFUND the consumed bucket, log row, soft body.

        The gate consumed a slot from ``consumed_bucket`` BEFORE the draw (Pattern 1), so this
        REFUNDS THAT bucket (free → ``free_used -= 1``, subscription → ``subscription_used -= 1``,
        paid → ``paid_balance += 1``) in the same transaction (Pitfall 2) to keep the net counter
        unchanged — READ-04/10 "retry is free / limit never consumed on failure" — and, crucially,
        to refund the bucket that was actually spent, never free by default (D-11,
        T-07-REFUND-WRONG-BUCKET). Does NOT assemble any templated stand-in reading from base
        meanings (D-09). The truncated ``generation_error`` is stored server-side for debugging and
        never crosses the response boundary (T-04-27).
        """
        reading.status = ReadingStatus.FAILED
        reading.generation_error = self._truncate_error(exc)
        session.add(
            GenerationLog(
                reading_id=reading.id,
                prompt_template_version=reading.prompt_version,
                model_name=reading.model_name,
                status=LOG_STATUS_FAILED,
                error=self._truncate_error(exc),
            )
        )
        # Compensating refund of the gate's consume, routed to the bucket ACTUALLY consumed —
        # skipped for the unlimited allowlist (``refund=False``), whose gate never consumed, so
        # there is nothing to give back.
        if refund and limits is not None:
            await self._refund_consumed_bucket(session, user.id, consumed_bucket)
            await session.refresh(limits)  # reflect the refunded counter in the returned remaining
        await session.commit()
        logger.warning(
            "reading_honest_fail",
            extra={"event": "reading.honest_fail", "reading_id": str(reading.id)},
        )
        return self._soft_body(
            reading_id=str(reading.id),
            message=SOFT_FAILURE_COPY,
            remaining=self._remaining(limits) if refund else None,
        )

    @staticmethod
    def _truncate_error(exc: BaseException) -> str:
        """The server-side error detail, truncated — includes the underlying cause when present."""
        cause = exc.__cause__
        detail = f"{exc}" if cause is None else f"{exc}: {cause!r}"
        return detail[:GENERATION_ERROR_MAX_CHARS]

    # ------------------------------------------------------------------ response builders

    @staticmethod
    def _soft_body(
        *,
        reading_id: str | None,
        message: str,
        remaining: int | None,
        reason: str | None = None,
        reset_at: datetime | None = None,
    ) -> ReadingOut:
        """A deliberate 200 soft body (paywall / refusal / redirect / honest fail), never a 500.

        ``status='failed'`` + ``summary=None`` + empty ``cards``; the human copy rides in
        ``summary_short`` so the existing frontend surfaces it (the result screen reads the soft
        message there). ``reading_id`` is the empty string for the pre-draw paywall (no row).

        ``reason`` is the machine-readable discriminant the FE branches on (``"paywall"`` for the
        limit block); ``reset_at`` is the per-user reopen moment fuelling the D-04 countdown. Both
        default to None so refusal / redirect / honest-fail bodies stay unchanged (Plan 04 only
        keys the paywall sheet off ``reason == "paywall"``).
        """
        return ReadingOut(
            reading_id=reading_id or "",
            status=ReadingStatus.FAILED.value,
            cards=[],
            summary=ReadingSummaryOut(
                linkage="",
                main_factor="",
                attention="",
                soft_advice=message,
                closing_phrase="",
            ),
            remaining_limits=remaining,
            reason=reason,
            reset_at=reset_at,
        )

    @staticmethod
    def _build_response(
        reading: Reading, cards: list[ReadingCard], remaining: int | None
    ) -> ReadingOut:
        """Build the completed ``ReadingOut`` from the authoritative persisted rows (§14.5).

        Card ``name``/``orientation``/``position_title`` come from the persisted ``reading_cards``
        (names attached from the immutable draw), NOT from the model echo. All five §18 summary
        fields are read back from ``summary_full`` so every field the result UI renders is present.
        """
        summary_data = json.loads(reading.summary_full) if reading.summary_full else {}
        card_out = [
            ReadingCardOut(
                name=getattr(card, "_card_title", "") or "",
                position_title=getattr(card, "_position_title", "") or "",
                orientation=card.orientation.value,
                short_meaning=card.short_meaning or "",
                interpretation=card.interpretation or "",
                deck_accent=card.mystical_accent or "",
            )
            for card in cards
        ]
        summary = ReadingSummaryOut(
            linkage=summary_data.get("connection", ""),
            main_factor=summary_data.get("main_factor", reading.main_factor or ""),
            attention=summary_data.get("attention_point", ""),
            soft_advice=summary_data.get("advice", reading.advice or ""),
            closing_phrase=summary_data.get("closing_phrase", ""),
        )
        return ReadingOut(
            reading_id=str(reading.id),
            status=reading.status.value,
            cards=card_out,
            summary=summary,
            remaining_limits=remaining,
        )


__all__ = [
    "FREE_HISTORY_CAP",
    "SOFT_FAILURE_COPY",
    "SOFT_PAYWALL_COPY",
    "WINDOW",
    "Bucket",
    "ReadingInputError",
    "ReadingService",
    "determine_access",
]
