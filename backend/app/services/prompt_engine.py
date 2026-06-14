"""``PromptEngine`` — the fused single-call prompt assembler (READ-03/05/06/11, D-01/02/10/11/14).

This is where the Core Value ("один и тот же вопрос ощущается по-разному в разных колодах")
is engineered. The engine composes ONE ``messages.parse`` prompt from the active, admin-editable
``prompt_templates`` rows + the live deck / spread / card data, so the §17 per-card task and the
§18 summary task are merged into a single call that elicits the whole ``ReadingOutput``:

  * **System block** = the ``system`` template (§16 — the 10 principles + allow/ban formulations)
    + the chosen deck's ``deck_modifier_<deck_slug>`` row (§19 tone AND the mandatory D-02
    signature instruction authored in the seed). Tone + focus diverge per deck; the signature
    guarantees a deck-specific device in *every* reading (D-02); structure stays uniform (D-11).
  * **User block** = the fused §17 + §18 task. For EACH drawn card it emits a ``position_index``-
    anchored context (position title/description/instruction, card title, universal
    ``meaning_*``/``keywords_*`` from ``cards``, the deck-specific modifiers from ``deck_cards``,
    orientation), then the §18 summary instruction. When the question is sensitive
    (``safety_action == SAFETY_MODIFIER``) the ``safety`` fragment (§20.3) is appended for silent
    softening (D-05 / SAFE-02). The task restates "ответ на русском" (D-14) and the §17 length
    targets (≤140 chars short_meaning — D-10) because constrained decoding strips length
    constraints (RESEARCH Pitfall 1), and requires exactly one ``CardInterpretation`` per
    ``position_index`` in order (RESEARCH Pitfall 3 — names/orientations stay authoritative
    server-side).
  * **prompt_version** = composed from the resolved templates' ``version`` fields, e.g.
    ``system@v1+deck_modifier@v2+single_card@v1+final_summary@v1`` (+``safety@vN`` when appended).
    This string is persisted to ``readings.prompt_version`` + ``generation_logs.prompt_template_version``
    so a bad generation is traceable and the admin version toggle is the Phase-8 safety valve
    (ANALYTICS-02 / T-04-22).

The string assembly lives in **pure helpers** (given already-loaded rows + records) so the
behaviour is unit-testable without Postgres or the network. ``PromptEngine.build`` is the thin
async wrapper that reads the ACTIVE rows (mirroring ``catalog.py`` — ``select()``, no f-string
SQL, no implicit lazy load) and delegates to those helpers. ``refusal`` / ``redirect`` copy is
resolved from the seeded rows for the crisis / abusive branches Plan 05 returns *before* any draw
(D-03 / D-04 / D-06) — the question is interpolated as labelled DATA inside the fixed §16 frame,
never as an instruction (T-04-19).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deck, DeckCard, PromptTemplate, SpreadType
from app.models.enums import Orientation
from app.services.card_draw import DrawnCard
from app.services.safety import SafetyAction

# Template slugs the engine composes. The deck modifier is resolved per-deck (below). These are
# the stable seed keys (``prompt_templates.slug``) — admin edits the rows, never the code.
SYSTEM_SLUG = "system"
SINGLE_CARD_SLUG = "single_card"
FINAL_SUMMARY_SLUG = "final_summary"
SAFETY_SLUG = "safety"
REFUSAL_SLUG = "refusal"
REDIRECT_SLUG = "redirect"

# §17 length target (D-10) — restated in the task text because constrained decoding strips
# min/maxLength (RESEARCH Pitfall 1); the model only learns the limit from the prompt + the
# field description, never from a schema constraint.
SHORT_MEANING_MAX_CHARS = 140

# D-14 — the reading is always Russian, regardless of the question's language. Stated verbatim
# in the user task so the instruction is impossible to miss.
RUSSIAN_INSTRUCTION = "Пиши ответ всегда на русском языке, независимо от языка вопроса."


def deck_modifier_slug(deck_slug: str) -> str:
    """The ``prompt_templates`` slug for a deck's §19 modifier row (``deck_modifier_<slug>``)."""
    return f"deck_modifier_{deck_slug}"


@dataclass(frozen=True)
class DeckCardStyle:
    """The deck-specific style layer for one drawn card (from ``deck_cards``), or empty.

    Kept separate from ``DrawnCard`` (which carries only the *universal* meaning) so the pure
    user-block builder receives the deck-specific modifiers without itself touching the DB. An
    absent row (no override for this (deck, card) pair) is represented by all-empty fields.
    """

    keywords: Sequence[str] = ()
    upright_modifier: str | None = None
    reversed_modifier: str | None = None


@dataclass(frozen=True)
class PromptBundle:
    """The assembled single-call prompt + its versioned audit string.

    ``system`` / ``user`` go straight to ``LLMService.generate(system=..., user_prompt=...)``;
    ``prompt_version`` is persisted to ``readings.prompt_version`` and the ``generation_logs`` row
    (ANALYTICS-02).
    """

    system: str
    user: str
    prompt_version: str


def _orientation_label(orientation: Orientation) -> str:
    """RU label for a card's orientation (matches the frontend ORIENTATION_LABELS, D-07)."""
    return "перевёрнутое" if orientation is Orientation.REVERSED else "прямое"


def _active_meaning(card: DrawnCard) -> str:
    """The universal meaning that applies given the drawn orientation (upright vs reversed)."""
    return card.meaning_reversed if card.orientation is Orientation.REVERSED else card.meaning_upright


def _active_keywords(card: DrawnCard) -> Sequence[str]:
    """The universal keywords that apply given the drawn orientation."""
    return (
        card.keywords_reversed
        if card.orientation is Orientation.REVERSED
        else card.keywords_upright
    )


def _deck_specific_modifier(style: DeckCardStyle, orientation: Orientation) -> str | None:
    """The deck-specific modifier for the drawn orientation (``deck_cards``), or None."""
    return (
        style.reversed_modifier
        if orientation is Orientation.REVERSED
        else style.upright_modifier
    )


def build_system_block(*, system_text: str, deck_modifier_text: str) -> str:
    """Compose the SYSTEM block: §16 principles + the deck's §19 modifier + D-02 signature.

    Pure. ``deck_modifier_text`` already carries BOTH the §19 tone and the mandatory
    "Обязательная подпись колоды…" signature sentence (authored in the seed, Task 1), so the
    guaranteed per-deck device is part of the system frame the model is bound to (D-01/D-02).
    """
    return f"{system_text.strip()}\n\n{deck_modifier_text.strip()}"


def _build_card_context(
    card: DrawnCard,
    *,
    spread: SpreadType,
    style: DeckCardStyle,
) -> str:
    """One ``position_index``-anchored context block for a single drawn card (pure).

    Anchors the block with an explicit ``position_index`` and requires the same index back so
    persistence matches on the index, not list order (RESEARCH Pitfall 3). Card name + orientation
    are given as DATA (authoritative server-side) — the model interprets, it does not invent them.
    """
    position = next(
        (p for p in spread.positions if p.position_index == card.position_index),
        None,
    )
    position_title = position.title if position is not None else f"Позиция {card.position_index}"
    position_description = (position.description if position is not None else None) or "—"
    position_instruction = (
        (position.prompt_instruction if position is not None else None)
        or "Прочитай карту в смысле этой позиции расклада."
    )

    keywords = ", ".join(_active_keywords(card)) or "—"
    deck_keywords = ", ".join(style.keywords) or "—"
    deck_modifier = _deck_specific_modifier(style, card.orientation) or "—"

    lines = [
        f"Карта в позиции position_index={card.position_index}:",
        f"- Заголовок позиции: {position_title}",
        f"- Смысл позиции: {position_description}",
        f"- Инструкция позиции: {position_instruction}",
        f"- Карта: {card.card_title}",
        f"- Положение карты: {_orientation_label(card.orientation)}",
        f"- Универсальное значение карты: {_active_meaning(card)}",
        f"- Универсальные ключевые слова: {keywords}",
        f"- Ключевые слова карты в этой колоде: {deck_keywords}",
        f"- Модификатор карты для этой колоды: {deck_modifier}",
    ]
    return "\n".join(lines)


def build_user_block(
    *,
    single_card_text: str,
    final_summary_text: str,
    draw_records: Sequence[DrawnCard],
    spread: SpreadType,
    deck: Deck,
    question: str | None,
    topic: str,
    card_styles: Mapping[object, DeckCardStyle] | None = None,
    safety_text: str | None = None,
) -> str:
    """Compose the fused §17 + §18 USER task with one anchored block per drawn card (pure).

    ``question`` is interpolated as labelled DATA inside the fixed frame (T-04-19); an empty
    question becomes a general reading (HOME-02). ``card_styles`` maps ``deck_card_id`` → the
    deck-specific style; a missing entry falls back to an empty style. ``safety_text`` (the §20.3
    fragment) is appended ONLY when the question is sensitive (D-05 / SAFE-02). The task restates
    the Russian (D-14) and ≤140-char (D-10) requirements and demands exactly one card object per
    ``position_index`` (RESEARCH Pitfall 3).
    """
    styles = card_styles or {}
    ordered = sorted(draw_records, key=lambda c: c.position_index)
    card_count = len(ordered)

    question_line = (
        f"Вопрос пользователя: {question.strip()}"
        if question and question.strip()
        else "Вопрос пользователя: не задан — сделай общий расклад по выбранной теме."
    )

    parts: list[str] = [
        "Сформируй полный таро-расклад одним ответом: интерпретацию каждой выпавшей "
        "карты и общий итог.",
        "",
        question_line,
        f"Тема вопроса: {topic}",
        f"Колода: {deck.title}",
    ]
    if deck.atmosphere:
        parts.append(f"Атмосфера колоды: {deck.atmosphere}")
    if deck.tone:
        parts.append(f"Тон колоды: {deck.tone}")
    parts.append(f"Расклад: {spread.title}")
    parts.append(f"Количество карт: {card_count}")

    # Per-card §17 context, anchored by position_index (Pitfall 3).
    parts.append("")
    parts.append("Карты расклада:")
    for card in ordered:
        style = styles.get(card.deck_card_id, DeckCardStyle())
        parts.append("")
        parts.append(_build_card_context(card, spread=spread, style=style))

    # Per-card §17 task.
    parts.append("")
    parts.append(single_card_text.strip())

    # §18 summary task (fused into the same call).
    parts.append("")
    parts.append("Затем сформируй общий итог расклада:")
    parts.append(final_summary_text.strip())

    # D-05 / SAFE-02: silent softening for sensitive questions only.
    if safety_text:
        parts.append("")
        parts.append(safety_text.strip())

    # D-14 + D-10 + Pitfall 3 — restate the hard output rules in the task text.
    parts.append("")
    parts.append(RUSSIAN_INSTRUCTION)
    parts.append(
        f"Поле short_meaning каждой карты — одно короткое предложение до "
        f"{SHORT_MEANING_MAX_CHARS} символов."
    )
    parts.append(
        f"Верни ровно {card_count} интерпретаций карт — по одной на каждый "
        f"position_index, в том же порядке, что и карты выше; обязательно повтори "
        f"position_index в каждой интерпретации."
    )
    return "\n".join(parts)


def compose_prompt_version(templates: Sequence[PromptTemplate]) -> str:
    """Compose the audit ``prompt_version`` from the resolved templates' types + versions (pure).

    Format: ``<type>@<version>`` joined by ``+`` in a stable order (e.g.
    ``system@v1+deck_modifier@v2+single_card@v1+final_summary@v1``). Persisted to
    ``readings.prompt_version`` + ``generation_logs.prompt_template_version`` (ANALYTICS-02 /
    T-04-22) so a generation is always traceable to the exact admin-controlled template versions.
    """
    return "+".join(f"{t.type.value}@{t.version}" for t in templates)


@dataclass(frozen=True)
class _ActiveTemplates:
    """The active template rows the engine composed, in ``prompt_version`` order."""

    system: PromptTemplate
    deck_modifier: PromptTemplate
    single_card: PromptTemplate
    final_summary: PromptTemplate
    safety: PromptTemplate | None

    def ordered(self) -> list[PromptTemplate]:
        rows = [self.system, self.deck_modifier, self.single_card, self.final_summary]
        if self.safety is not None:
            rows.append(self.safety)
        return rows


class PromptEngine:
    """Assemble the fused single-call prompt from active templates + live reading data."""

    @staticmethod
    async def _active_template(session: AsyncSession, slug: str) -> PromptTemplate:
        """Load one ACTIVE template by slug (mirrors catalog.py: ``select()``, no lazy load)."""
        row = (
            await session.execute(
                select(PromptTemplate).where(
                    PromptTemplate.slug == slug,
                    PromptTemplate.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise ValueError(f"active prompt_template '{slug}' not found")
        return row

    @staticmethod
    async def _card_styles(
        session: AsyncSession, draw_records: Sequence[DrawnCard]
    ) -> dict[object, DeckCardStyle]:
        """Eager-load the deck-specific style for every drawn ``deck_card`` (no lazy load).

        Returns a ``deck_card_id`` → ``DeckCardStyle`` map. A drawn card whose ``deck_cards`` row
        carries no overrides simply yields an empty style (handled by the builder's fallback).
        """
        deck_card_ids = [c.deck_card_id for c in draw_records]
        if not deck_card_ids:
            return {}
        rows = (
            await session.execute(
                select(DeckCard).where(DeckCard.id.in_(deck_card_ids))
            )
        ).scalars().all()
        return {
            row.id: DeckCardStyle(
                keywords=tuple(row.deck_specific_keywords or ()),
                upright_modifier=row.deck_specific_upright_modifier,
                reversed_modifier=row.deck_specific_reversed_modifier,
            )
            for row in rows
        }

    # ----------------------------------------------------------------------------------------
    # HIST-05 / D-06 — CLOSED CONSENT GATE (negative requirement; do NOT "fix" this away).
    #
    # History is INTENTIONALLY not a parameter of ``build`` and no prior reading is ever fetched
    # for the prompt. Phase 5 is consent-flag-and-gate ONLY: it persists the
    # ``allow_history_personalization`` flag (via ``PATCH /api/me/settings``) but feeds NOTHING
    # from a user's past readings into the §18 prompt — the gate is closed BY ABSENCE. Even with
    # ``allow_history_personalization=True`` the assembled prompt carries no prior-reading text,
    # which ``test_prompt_has_no_history_even_with_flag_on`` +
    # ``test_build_has_no_history_parameter`` lock as a regression fence.
    #
    # Do NOT add a ``history`` / ``history_context`` / ``prior_readings`` parameter, a prior-reading
    # fetch, or a history prompt branch here (or in ``ReadingService.create_reading``). The actual
    # history-personalization / "повторный анализ" feature is v2 (ENG-02); when it is built it MUST
    # reintroduce the consent gate (only inject history when the flag is ON) rather than wiring
    # history in unconditionally. Removing this absence silently re-opens a privacy boundary.
    # ----------------------------------------------------------------------------------------
    async def build(
        self,
        session: AsyncSession,
        *,
        deck: Deck,
        spread: SpreadType,
        draw_records: Sequence[DrawnCard],
        question: str | None,
        topic: str,
        safety_action: SafetyAction = SafetyAction.GENERATE,
    ) -> PromptBundle:
        """Build the fused ``PromptBundle`` (system + user + prompt_version) for one reading.

        Reads the ACTIVE ``system`` / deck modifier / ``single_card`` / ``final_summary`` rows
        (+ the ``safety`` row when ``safety_action == SAFETY_MODIFIER``, D-05/SAFE-02), eager-loads
        the per-card deck styles, and delegates the string assembly to the pure helpers. Raises
        ``ValueError`` if a required active template is missing (a seed/admin misconfiguration —
        surfaced, never silently degraded).
        """
        system_row = await self._active_template(session, SYSTEM_SLUG)
        deck_modifier_row = await self._active_template(
            session, deck_modifier_slug(deck.slug)
        )
        single_card_row = await self._active_template(session, SINGLE_CARD_SLUG)
        final_summary_row = await self._active_template(session, FINAL_SUMMARY_SLUG)
        safety_row = (
            await self._active_template(session, SAFETY_SLUG)
            if safety_action is SafetyAction.SAFETY_MODIFIER
            else None
        )

        card_styles = await self._card_styles(session, draw_records)

        templates = _ActiveTemplates(
            system=system_row,
            deck_modifier=deck_modifier_row,
            single_card=single_card_row,
            final_summary=final_summary_row,
            safety=safety_row,
        )

        system_block = build_system_block(
            system_text=system_row.template_text,
            deck_modifier_text=deck_modifier_row.template_text,
        )
        user_block = build_user_block(
            single_card_text=single_card_row.template_text,
            final_summary_text=final_summary_row.template_text,
            draw_records=draw_records,
            spread=spread,
            deck=deck,
            question=question,
            topic=topic,
            card_styles=card_styles,
            safety_text=safety_row.template_text if safety_row is not None else None,
        )
        return PromptBundle(
            system=system_block,
            user=user_block,
            prompt_version=compose_prompt_version(templates.ordered()),
        )

    async def refusal_copy(self, session: AsyncSession) -> str:
        """Resolve the active generic crisis-refusal copy (D-04) for the crisis branch (D-03)."""
        return (await self._active_template(session, REFUSAL_SLUG)).template_text

    async def redirect_copy(self, session: AsyncSession) -> str:
        """Resolve the active abusive/manipulative redirect copy (D-06) for that branch."""
        return (await self._active_template(session, REDIRECT_SLUG)).template_text


__all__ = [
    "SYSTEM_SLUG",
    "SINGLE_CARD_SLUG",
    "FINAL_SUMMARY_SLUG",
    "SAFETY_SLUG",
    "REFUSAL_SLUG",
    "REDIRECT_SLUG",
    "SHORT_MEANING_MAX_CHARS",
    "RUSSIAN_INSTRUCTION",
    "deck_modifier_slug",
    "DeckCardStyle",
    "PromptBundle",
    "build_system_block",
    "build_user_block",
    "compose_prompt_version",
    "PromptEngine",
]
