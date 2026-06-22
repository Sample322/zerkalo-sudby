"""Reading contracts — the interface-first Wave-0 surface every later Phase-4 plan imports.

Three contract families live here:

1. **LLM single-call output** (`ReadingOutput` / `CardInterpretation` / `ReadingSummary`) —
   the fused TZ §17 (per-card) + §18 (summary) object passed to
   ``client.messages.parse(output_format=ReadingOutput)``. Constrained decoding guarantees a
   schema-valid instance on a clean ``end_turn``; ``ReadingOutput.model_validate_json`` raises
   ``pydantic.ValidationError`` on a bad shape — the seam Plan 03's corrective-retry trigger
   depends on (T-04-11).

   **Pitfall 1 (RESEARCH):** the Anthropic SDK *strips* ``minLength``/``maxLength`` from the
   schema before sending, so constrained decoding cannot enforce the §17 "≤140 chars" limit.
   The length target therefore lives in each field's ``description`` (load-bearing — it is how
   the model learns the shape) and is enforced later by a post-validation guard, **never** by a
   ``max_length`` constraint on these models. Do not add ``max_length`` to any LLM-output field.

2. **Classify output** (`SafetyCategory` / `SafetyVerdict`) — the tiny enum-only object the
   pre-generation safety gate returns (SAFE-01, TZ §20.4). The 7 categories map 1:1 onto a
   ``StrEnum`` mirroring ``app.models.enums`` style (lowercase slug values).

3. **Request / response** (`ReadingCreate` / `ReadingOut`) — the ``POST /api/readings`` contract
   (TZ §14.5). ``ReadingCreate.question`` carries the server-side HOME-01 (10–500 chars) /
   HOME-02 (empty allowed → general reading) validation. ``ReadingOut`` deliberately names its
   per-card + summary fields to mirror the frontend ``MockReading`` shape
   (``frontend/src/reading/types.ts``) so Plan 06's data-source swap is mechanical.
"""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Question length bounds (HOME-01). An empty / whitespace-only question is allowed
# (HOME-02 → general reading); a NON-empty question must be 10–500 chars.
QUESTION_MIN_LEN = 10
QUESTION_MAX_LEN = 500


# ---------------------------------------------------------------------------------------
# 1. LLM single-call output contract (fused TZ §17 + §18).
#    Field descriptions are the ONLY place the length/shape target lives (Pitfall 1).
# ---------------------------------------------------------------------------------------
class CardInterpretation(BaseModel):
    """One drawn card's interpretation (TZ §17). Maps onto ``reading_cards`` columns.

    Card name/orientation are authoritative server-side (the persisted ``reading_cards`` row);
    the model is given ``position_index`` only and must echo it back so persistence matches on
    the index, not on list order (RESEARCH Pitfall 3).
    """

    position_index: int = Field(
        description="0-based индекс позиции; ДОЛЖЕН совпадать с порядком выпавших карт",
    )
    short_meaning: str = Field(
        description="короткое значение карты: 1 короткое предложение, до 140 символов",
    )  # → reading_cards.short_meaning
    interpretation: str = Field(
        description="глубокая интерпретация под вопрос: 2–3 коротких предложения",
    )  # → reading_cards.interpretation
    mystical_accent: str = Field(
        description=(
            "1 атмосферная фраза в стиле колоды — обязательная сигнатура колоды (D-02), "
            "до 140 символов"
        ),
    )  # → reading_cards.mystical_accent
    soft_advice: str = Field(
        description="1 мягкий совет без давления и без категоричных предсказаний",
    )  # → folded into reading_cards.interpretation (no dedicated column)


class ReadingSummary(BaseModel):
    """The reading's overall summary (TZ §18). Maps onto ``readings`` columns + JSON overflow."""

    summary_short: str = Field(
        description="короткий итог расклада в 1–2 предложения",
    )  # → readings.summary_short
    connection: str = Field(
        description="как выпавшие карты связаны между собой в общий узор",
    )  # → readings.summary_full (JSON-serialized full summary)
    main_factor: str = Field(
        description="главный фактор ситуации",
    )  # → readings.main_factor
    attention_point: str = Field(
        description="на что стоит обратить внимание",
    )  # → readings.summary_full (JSON-serialized full summary)
    advice: str = Field(
        description="мягкий совет без давления и без фатализма",
    )  # → readings.advice
    closing_phrase: str = Field(
        description="атмосферная завершающая фраза в стиле колоды",
    )  # → readings.summary_full (JSON-serialized full summary)


class ReadingOutput(BaseModel):
    """The single ``messages.parse`` output: every card + the summary in ONE validated object.

    Zero optional fields and zero unions → comfortably inside the Structured-Outputs budget
    (≤24 optional / ≤16 union params). A clean ``end_turn`` is guaranteed schema-valid.
    """

    cards: list[CardInterpretation] = Field(
        description="ровно по одной интерпретации на каждую выпавшую карту, в порядке позиций",
    )
    summary: ReadingSummary


# ---------------------------------------------------------------------------------------
# 2. Classify output contract (SAFE-01, TZ §20.4).
#    StrEnum mirrors app.models.enums style: lowercase slug values, member-value persisted.
# ---------------------------------------------------------------------------------------
class SafetyCategory(enum.StrEnum):
    """The exact TZ §20.4 classifier categories (7 members).

    Used as the enum-only output of the pre-generation classify call; constrained decoding
    guarantees the model returns a valid member. Routing (D-03/04/05/06):
      * ``normal`` → normal generation;
      * ``*_sensitive`` → silent softening (safety_modifier appended to the prompt, no UI badge);
      * ``crisis_sensitive`` → refusal, no draw, no generation, limit kept (short-circuits BEFORE draw);
      * ``abusive_or_manipulative`` → gentle in-character redirect, no draw, limit kept.
    """

    NORMAL = "normal"
    RELATIONSHIP_SENSITIVE = "relationship_sensitive"
    FINANCIAL_SENSITIVE = "financial_sensitive"
    HEALTH_SENSITIVE = "health_sensitive"
    LEGAL_SENSITIVE = "legal_sensitive"
    CRISIS_SENSITIVE = "crisis_sensitive"
    ABUSIVE_OR_MANIPULATIVE = "abusive_or_manipulative"


class SafetyVerdict(BaseModel):
    """The classify call's structured output — a single constrained-decoding enum member."""

    category: SafetyCategory = Field(
        description="одна из 7 категорий безопасности вопроса (TZ §20.4)",
    )


# ---------------------------------------------------------------------------------------
# Internal service-layer helpers for the classify call (not LLM-output, not request/response).
# Kept here so the whole classify contract is in one module the gate + logs import from.
# ---------------------------------------------------------------------------------------
class ClassifyCallMeta(BaseModel):
    """Metadata from one classify LLM call, for the ``generation_logs`` row (ANALYTICS-02).

    ``model_config`` disables the ``model_``-prefix protected-namespace warning so a plain
    ``model_name`` field (mirroring ``generation_logs.model_name``) is allowed.
    """

    model_config = ConfigDict(protected_namespaces=())

    model_name: str = Field(description="resolved model alias used for the classify call")
    input_tokens: int = Field(default=0, description="prompt tokens consumed by the classify call")
    output_tokens: int = Field(default=0, description="completion tokens from the classify call")
    latency_ms: int = Field(default=0, description="wall-clock latency of the classify call")


class ClassifyResult(BaseModel):
    """The full result of ``SafetyService.classify`` — the verdict + how it was reached.

    ``via_regex`` is True when the regex pre-filter resolved the category without any API call
    (instant crisis short-circuit or fast-path normal); in that case ``meta`` is None (no call,
    nothing to log as an LLM generation).
    """

    verdict: SafetyVerdict
    via_regex: bool = Field(
        default=False,
        description="True if the regex pre-filter decided without a classify API call",
    )
    meta: ClassifyCallMeta | None = Field(
        default=None,
        description="classify-call metadata when an API call was made (None for regex fast-path)",
    )


# ---------------------------------------------------------------------------------------
# 3. Request / response contract (TZ §14.5).
# ---------------------------------------------------------------------------------------
class ReadingCreate(BaseModel):
    """``POST /api/readings`` request body (TZ §14.5).

    ``question`` is ``str | None``: ``None`` / empty / whitespace-only → general reading
    (HOME-02, normalized to ``None``); a non-empty question must be 10–500 chars (HOME-01),
    else a ``ValidationError`` (server-side request validation — distinct from the LLM
    output_format, where length must NOT be a constraint).
    """

    question: str | None = Field(
        default=None,
        description="вопрос пользователя; пусто/None → общий расклад (HOME-02)",
    )
    topic: str = Field(description="slug выбранной темы")
    deck_slug: str = Field(description="slug выбранной колоды")
    spread_slug: str = Field(description="slug выбранного расклада")
    reversals_enabled: bool = Field(
        default=True,
        description="включены ли перевёрнутые карты (D-13: по умолчанию on, 70/30)",
    )
    answer_style: str = Field(
        default="berezhny",
        description="стиль ответа: yasny | berezhny | tainstvenny (нормализуется на сервере)",
    )

    @field_validator("question", mode="before")
    @classmethod
    def _validate_question(cls, value: object) -> str | None:
        """Empty/whitespace → None (general reading); non-empty must be 10–500 chars (HOME-01)."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("question must be a string or null")
        stripped = value.strip()
        if not stripped:
            # HOME-02: empty question is allowed and means a general reading.
            return None
        if not (QUESTION_MIN_LEN <= len(stripped) <= QUESTION_MAX_LEN):
            raise ValueError(
                f"question must be between {QUESTION_MIN_LEN} and {QUESTION_MAX_LEN} characters"
            )
        return stripped


class ReadingCardOut(BaseModel):
    """One drawn card in the response (TZ §14.5 ``selected_cards`` / ``interpretations``).

    Field names mirror ``frontend/src/reading/types.ts`` ``MockReadingCard`` so Plan 06's
    seam mapping (``ReadingOut`` → ``MockReading``) is mechanical. ``name`` / ``orientation`` /
    ``position_title`` come from the authoritative persisted ``reading_cards`` join, NOT from
    the model output.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description="READ-05 название карты (authoritative, server-side)")
    position_title: str = Field(description="READ-05 заголовок позиции из выбранного расклада")
    orientation: str = Field(description="READ-05 положение: upright / reversed")
    short_meaning: str = Field(description="READ-05 короткое значение")
    interpretation: str = Field(description="READ-05 глубокая интерпретация под вопрос")
    deck_accent: str = Field(description="READ-05 мистический акцент колоды (deck signature)")


class ReadingSummaryOut(BaseModel):
    """The response summary (TZ §14.5 ``summary``).

    Field names mirror ``MockReadingSummary``: ``linkage`` / ``main_factor`` / ``attention`` /
    ``soft_advice`` / ``closing_phrase`` (camelCase'd on the frontend) so the mapping is
    mechanical. Carries all five §18 fields the result screen already renders.
    """

    linkage: str = Field(description="READ-06 связка карт — как карты связаны")
    main_factor: str = Field(description="READ-06 главный фактор")
    attention: str = Field(description="READ-06 на что обратить внимание")
    soft_advice: str = Field(description="READ-06 мягкий совет")
    closing_phrase: str = Field(description="READ-06 завершающая фраза в стиле колоды")


class ReadingOut(BaseModel):
    """``POST /api/readings`` response (TZ §14.5).

    Carries ``reading_id`` + ``status`` + the full per-card list + all five summary fields +
    ``remaining_limits`` so the (already-built) frontend result screen gets everything it
    renders. On the safety-block / honest-fail paths ``status`` is ``failed`` (or a soft
    in-flow status) and ``cards``/``summary`` may be empty — the router returns a 200 with the
    soft §9.8 body, never a 500 (RESEARCH "Don't Hand-Roll").
    """

    model_config = ConfigDict(from_attributes=True)

    reading_id: str = Field(description="UUID созданного расклада (TZ §14.5 reading_id)")
    status: str = Field(description="статус генерации: pending/generating/completed/failed")
    cards: list[ReadingCardOut] = Field(
        default_factory=list,
        description="TZ §14.5 selected_cards + interpretations, по позициям",
    )
    summary: ReadingSummaryOut | None = Field(
        default=None,
        description="TZ §14.5 summary — None пока расклад не completed",
    )
    remaining_limits: int | None = Field(
        default=None,
        description="TZ §14.5 remaining_limits — сколько раскладов осталось",
    )
    reason: str | None = Field(
        default=None,
        description=(
            "machine-readable outcome discriminant for the FE catch: "
            "paywall / throttle / failure / null on success (D-04 / 06-UI-SPEC)"
        ),
    )
    reset_at: datetime | None = Field(
        default=None,
        description=(
            "per-user free-limit reopen moment (week_start + 7d); fuels the FE countdown, D-04"
        ),
    )


class ReadingListItemOut(BaseModel):
    """A LIGHT history list item (TZ §9.6 / HIST-02) — NOT the heavy ``ReadingOut``.

    ``GET /api/readings`` returns these: just enough to render a history card (дата / вопрос /
    колода / расклад / миниатюры / короткий итог). It deliberately omits the full per-card
    ``interpretation`` and the ``cards`` array (those belong to the detail endpoint ``GET
    /readings/{id}``, HIST-03) — sending the whole reading for every row would waste bandwidth and
    conflate list with detail. The §9.6 wording is "короткий итог", so only ``summary_short`` rides
    in the list, never the per-card text (RESEARCH anti-pattern: do not reuse ``ReadingOut`` here).

    ``card_thumbnails`` come from ``deck_cards.thumbnail_url`` for the reading's drawn cards (in
    position order); an empty list is fine (the frontend ``CardArtFallback`` covers missing art,
    A2). ``deck_name`` / ``spread_name`` are the human ``Deck.title`` / ``SpreadType.title``.
    """

    model_config = ConfigDict(from_attributes=True)

    reading_id: str = Field(description="UUID расклада (§9.6 — для повторного открытия)")
    created_at: datetime = Field(description="§9.6 дата создания расклада (newest-first)")
    question: str | None = Field(
        default=None,
        description="§9.6 вопрос пользователя; пусто/None → общий расклад",
    )
    deck_name: str = Field(description="§9.6 колода — человекочитаемое название (Deck.title)")
    spread_name: str = Field(
        description="§9.6 расклад — человекочитаемое название (SpreadType.title)"
    )
    card_thumbnails: list[str] = Field(
        default_factory=list,
        description="§9.6 миниатюры выпавших карт (deck_cards.thumbnail_url), по позициям",
    )
    summary_short: str | None = Field(
        default=None,
        description="§9.6 короткий итог расклада (readings.summary_short — НЕ полная интерпретация)",
    )


__all__ = [
    "QUESTION_MIN_LEN",
    "QUESTION_MAX_LEN",
    "CardInterpretation",
    "ReadingSummary",
    "ReadingOutput",
    "SafetyCategory",
    "SafetyVerdict",
    "ClassifyCallMeta",
    "ClassifyResult",
    "ReadingCreate",
    "ReadingCardOut",
    "ReadingSummaryOut",
    "ReadingOut",
    "ReadingListItemOut",
]
