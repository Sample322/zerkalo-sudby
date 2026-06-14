"""``ReadingService`` — the keystone orchestration (READ-01/03/04/05/06/10/11, SAFE-01/02/03, ANALYTICS-02).

This is the moment the Core Value goes live end-to-end on the backend. ``create_reading`` owns
the ``AsyncSession`` transaction and composes every Wave-0/Wave-1 piece in the EXACT locked order
the product invariants require (RESEARCH "System Architecture Diagram"):

  1. **limit check** — read the user's ``user_limits``; no quota → soft §9.8 paywall body,
     NO draw (Phase-4 scope is "has quota?" + "consume on success"; weekly reset/buckets are
     Phase 6);
  2. **SAFETY GATE — BEFORE any draw/charge** (D-03, the most important ordering invariant in
     the phase) — ``SafetyService.classify`` + ``route``:
       * crisis → persist a parent ``readings`` row (status=FAILED) FIRST so the NOT-NULL
         ``generation_logs.reading_id`` FK holds, write the classify log row IF a real classify
         call was made, then return the seeded refusal copy — NO draw, NO generation, limit kept;
       * abusive → same, returning the seeded redirect copy — NO draw, limit kept;
       * ``*_sensitive`` → set a ``SAFETY_MODIFIER`` flag and continue (silent softening, D-05);
       * normal → continue;
  3. **CSPRNG draw** (``CardDrawService.draw``) → persist ``readings`` (status=PENDING) + the
     immutable ``reading_cards`` rows; write the classify log row (if a call was made) against
     the now-existing reading;
  4. **PromptEngine.build** → ``(system, user, prompt_version)``; set ``readings.prompt_version``;
  5. status=GENERATING; ONE ``LLMService.generate`` call. Each attempt's audit lands in
     ``generation_logs``. On ``LLMGenerationError`` (exhausted after the corrective retry) →
     HONEST FAIL (D-09): status=FAILED, truncated ``generation_error`` (server-side only), a final
     failed log row, NO consume, NO templated stand-in reading, return the soft §9.8 body;
  6. **brand guard** (SAFE-06) over the generated text → LOG+FLAG only (never fails the reading);
  7. **persist the mapping** (RESEARCH Pattern 1): each ``CardInterpretation`` matched BY
     ``position_index`` (Pitfall 3) onto ``reading_cards.short_meaning/interpretation/
     mystical_accent`` (``soft_advice`` appended into ``interpretation``); ``readings.summary_short/
     main_factor/advice`` + the full ``ReadingSummary`` JSON into ``readings.summary_full``;
     ``model_name``/``completed_at``; status=COMPLETED;
  8. **consume the limit in EXACTLY this one place** — ``free_used_this_week += 1`` (Pitfall 4),
     AFTER persist, BEFORE commit;
  9. commit; build and return ``ReadingOut`` (per-card names/orientations authoritative from the
     persisted ``reading_cards``, NOT echoed by the model; all five §18 summary fields;
     remaining_limits).

The collaborators (CardDrawService / SafetyService / PromptEngine / LLMService) are injected via
constructor params defaulting to the real ones — the same seam Plan 03/04 used so tests pass fakes
(``FakeLLM`` / ``FakeSafety`` via ``app.dependency_overrides``) and no real Anthropic call is ever
made. Domain errors (unknown/inactive deck or spread) raise ``ReadingInputError`` for the router to
map to 404; the soft paywall / refusal / redirect / honest-fail responses are deliberate 200
bodies carrying a ``status`` field — the global handler (``core/errors.py``) stays the last-resort
500 path (RESEARCH "Don't Hand-Roll").
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.brand_guard import contains_banned_brand_token
from app.models import (
    Deck,
    DeckCard,
    GenerationLog,
    Reading,
    ReadingCard,
    SpreadType,
    User,
    UserLimits,
)
from app.models.enums import ReadingStatus
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

        # 1. Limit check (Phase-4 scope: has-quota? + consume-on-success). No quota → soft body.
        limits = await self._get_limits(session, user.id)
        if limits is not None and not self._has_quota(limits):
            return self._soft_body(
                reading_id=None,
                message=SOFT_PAYWALL_COPY,
                remaining=0,
            )

        # 2. SAFETY GATE — BEFORE any draw/charge (D-03).
        classify_result = _normalize_classify(await self._safety.classify(req.question))
        action = route(classify_result.verdict)

        if not action.continues_to_draw:
            # crisis → refusal, abusive → redirect. Both short-circuit with NO draw, limit kept.
            return await self._short_circuit(
                session, user, limits, action, classify_result, req, deck, spread
            )

        safety_action = (
            SafetyAction.SAFETY_MODIFIER
            if action is SafetyAction.SAFETY_MODIFIER
            else SafetyAction.GENERATE
        )

        # 3. CSPRNG draw + persist pending + immutable reading_cards.
        draw_records = await self._card_draw.draw(
            session,
            deck_id=deck.id,
            spread=spread,
            reversals_enabled=req.reversals_enabled,
        )
        reading = await self._persist_pending(session, user, req, deck, spread, draw_records)

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
            # HONEST FAIL (D-09): no consume, no templated stand-in, soft §9.8 body.
            return await self._honest_fail(session, reading, limits, exc)

        # 6. Brand guard — LOG + FLAG only (never fail the reading; RESEARCH Open Question 2).
        self._brand_guard(reading.id, output)

        # 7. Persist the single-call output onto reading_cards (by position_index) + readings.
        cards = await self._persist_output(
            session, reading, spread, draw_records, output, model_name
        )

        # 8. Consume the limit in EXACTLY this one place (Pitfall 4).
        remaining = self._consume_limit(limits)

        # 9. Commit + return the real reading (authoritative names/orientations from the rows).
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
    def _has_quota(limits: UserLimits) -> bool:
        """Phase-4 quota check: a free unit remains, OR a paid / subscription balance is available.

        Weekly reset / atomic decrement / Redis throttle are Phase 6 — out of scope here.
        """
        free_left = (limits.free_weekly_limit or 0) - (limits.free_used_this_week or 0)
        subscription_left = (limits.subscription_spreads_limit or 0) - (
            limits.subscription_spreads_used or 0
        )
        return free_left > 0 or (limits.paid_spreads_balance or 0) > 0 or subscription_left > 0

    @staticmethod
    def _remaining(limits: UserLimits | None) -> int | None:
        """Remaining free units for the §14.5 ``remaining_limits`` field (None if no row)."""
        if limits is None:
            return None
        return max(0, (limits.free_weekly_limit or 0) - (limits.free_used_this_week or 0))

    # ------------------------------------------------------------------ persistence

    @staticmethod
    async def _persist_pending(
        session: AsyncSession,
        user: User,
        req: ReadingCreate,
        deck: Deck,
        spread: SpreadType,
        draw_records: list[DrawnCard],
    ) -> Reading:
        """Create the ``readings`` row (PENDING) + the immutable ``reading_cards`` from the draw.

        ``len(draw_records)`` MUST equal the spread's ``card_count`` (Pitfall 3 — validate the
        count before persisting). The interpretation columns are left NULL here; they are filled
        from the single-call output in ``_persist_output`` (Pattern 3 — cards persisted before
        generation).
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
            reversals_enabled=req.reversals_enabled,
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
        reading.completed_at = datetime.now(UTC)
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

    @staticmethod
    def _consume_limit(limits: UserLimits | None) -> int | None:
        """Consume EXACTLY one unit on success (Pitfall 4) and return the remaining free count.

        Decrements the free weekly counter when one is available; otherwise draws from the paid
        balance, then the subscription allotment (the order the quota check accepts them). This is
        the ONLY place the limit is mutated — every non-success exit leaves it untouched (READ-10).
        """
        if limits is None:
            return None
        free_left = (limits.free_weekly_limit or 0) - (limits.free_used_this_week or 0)
        if free_left > 0:
            limits.free_used_this_week = (limits.free_used_this_week or 0) + 1
        elif (limits.paid_spreads_balance or 0) > 0:
            limits.paid_spreads_balance = limits.paid_spreads_balance - 1
        else:
            limits.subscription_spreads_used = (limits.subscription_spreads_used or 0) + 1
        return max(0, (limits.free_weekly_limit or 0) - (limits.free_used_this_week or 0))

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
            reversals_enabled=req.reversals_enabled,
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
        limits: UserLimits | None,
        exc: LLMGenerationError,
    ) -> ReadingOut:
        """Honest fail (D-09): status=FAILED, truncated error server-side, final log row, soft body.

        Does NOT consume the limit (READ-04/10 — retry is free) and does NOT assemble any templated
        stand-in reading from base meanings (D-09). The truncated ``generation_error`` is stored
        server-side for debugging and never crosses the response boundary (T-04-27).
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
        await session.commit()
        logger.warning(
            "reading_honest_fail",
            extra={"event": "reading.honest_fail", "reading_id": str(reading.id)},
        )
        return self._soft_body(
            reading_id=str(reading.id),
            message=SOFT_FAILURE_COPY,
            remaining=self._remaining(limits),
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
        *, reading_id: str | None, message: str, remaining: int | None
    ) -> ReadingOut:
        """A deliberate 200 soft body (paywall / refusal / redirect / honest fail), never a 500.

        ``status='failed'`` + ``summary=None`` + empty ``cards``; the human copy rides in
        ``summary_short`` so the existing frontend surfaces it (the result screen reads the soft
        message there). ``reading_id`` is the empty string for the pre-draw paywall (no row).
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
    "ReadingInputError",
    "ReadingService",
]
