"""SAFE-01/02/04/05 — safety classification routing (regex pre-filter + Haiku classify).

Implemented in Plan 04-03 (``SafetyService``). The behaviours assert, against a MOCKED
``AsyncAnthropic`` client (no network, no API key):
  * the regex pre-filter resolves the highest-signal RU/EN crisis terms WITHOUT a classify call
    (instant ``crisis_sensitive``), and an empty/None question (HOME-02) → ``normal`` with no
    call (SAFE-01);
  * an undecided question makes ONE tiny Haiku ``messages.parse`` call returning a
    ``SafetyVerdict`` (structured output, not ``json.loads``);
  * ``route(verdict)`` maps crisis→REFUSAL, abusive→REDIRECT, any ``*_sensitive``→SAFETY_MODIFIER
    (continue), normal→GENERATE — the gate Plan 05 runs before the draw (SAFE-02/04/05);
  * ``classify()`` returns ``ClassifyResult`` whose ``meta`` is None on the regex/empty
    short-circuit and otherwise carries model/tokens/latency (ANALYTICS-02).

The classify contract (``SafetyCategory`` / ``SafetyVerdict``) is imported from Plan 01.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.reading import (
    ClassifyResult,
    SafetyCategory,
    SafetyVerdict,
)
from app.services.safety import (
    CLASSIFY_MODEL,
    SafetyAction,
    SafetyService,
    route,
)


# --- helpers ----------------------------------------------------------------------------
def _verdict_response(
    category: SafetyCategory, *, input_tokens: int = 210, output_tokens: int = 3
) -> SimpleNamespace:
    """A stand-in for the classify ``ParsedMessage``: ``.parsed_output`` is a ``SafetyVerdict``."""
    return SimpleNamespace(
        parsed_output=SafetyVerdict(category=category),
        model=CLASSIFY_MODEL,
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def _make_service(parse_mock: AsyncMock) -> SafetyService:
    """Wrap a scripted ``messages.parse`` AsyncMock in a fake AsyncAnthropic-shaped client."""
    fake_client = SimpleNamespace(messages=SimpleNamespace(parse=parse_mock))
    return SafetyService(client=fake_client)


# --- behaviours -------------------------------------------------------------------------
@pytest.mark.parametrize(
    "question",
    [
        "Я хочу покончить с собой, что делать?",
        "думаю о суициде каждый день",
        "I want to kill myself",
        "боюсь что он применит насилие ко мне",
    ],
)
async def test_regex_prefilter_catches_crisis_no_call(question: str) -> None:
    """SAFE-01: an obvious crisis question → crisis_sensitive via regex; NO classify call."""
    parse_mock = AsyncMock()  # must never be awaited
    service = _make_service(parse_mock)

    result = await service.classify(question)

    assert isinstance(result, ClassifyResult)
    assert result.verdict.category is SafetyCategory.CRISIS_SENSITIVE
    assert result.via_regex is True
    assert result.meta is None
    parse_mock.assert_not_awaited()


@pytest.mark.parametrize("question", [None, "", "   ", "\n\t  "])
async def test_empty_question_is_normal_no_call(question: str | None) -> None:
    """HOME-02 / SAFE-01: empty/None question → normal via pre-filter; NO classify call."""
    parse_mock = AsyncMock()
    service = _make_service(parse_mock)

    result = await service.classify(question)

    assert result.verdict.category is SafetyCategory.NORMAL
    assert result.via_regex is True
    assert result.meta is None
    parse_mock.assert_not_awaited()


async def test_undecided_calls_classify() -> None:
    """SAFE-01: an undecided question → ONE Haiku classify call; its category is returned."""
    parse_mock = AsyncMock(
        return_value=_verdict_response(SafetyCategory.RELATIONSHIP_SENSITIVE)
    )
    service = _make_service(parse_mock)

    result = await service.classify("Любит ли меня мой партнёр и что нас ждёт впереди?")

    assert parse_mock.await_count == 1
    assert parse_mock.await_args.kwargs["model"] == CLASSIFY_MODEL
    assert result.verdict.category is SafetyCategory.RELATIONSHIP_SENSITIVE
    assert result.via_regex is False
    assert result.meta is not None
    assert result.meta.model_name == CLASSIFY_MODEL
    assert result.meta.input_tokens == 210
    assert result.meta.output_tokens == 3
    assert result.meta.latency_ms >= 0


async def test_classify_uses_structured_output() -> None:
    """SAFE-01: the classify call uses output_format=SafetyVerdict (not prompt-and-parse)."""
    parse_mock = AsyncMock(return_value=_verdict_response(SafetyCategory.NORMAL))
    service = _make_service(parse_mock)

    await service.classify("Какой будет моя неделя на работе?")

    assert parse_mock.await_args.kwargs["output_format"] is SafetyVerdict


@pytest.mark.parametrize(
    ("category", "action"),
    [
        (SafetyCategory.CRISIS_SENSITIVE, SafetyAction.REFUSAL),
        (SafetyCategory.ABUSIVE_OR_MANIPULATIVE, SafetyAction.REDIRECT),
        (SafetyCategory.RELATIONSHIP_SENSITIVE, SafetyAction.SAFETY_MODIFIER),
        (SafetyCategory.FINANCIAL_SENSITIVE, SafetyAction.SAFETY_MODIFIER),
        (SafetyCategory.HEALTH_SENSITIVE, SafetyAction.SAFETY_MODIFIER),
        (SafetyCategory.LEGAL_SENSITIVE, SafetyAction.SAFETY_MODIFIER),
        (SafetyCategory.NORMAL, SafetyAction.GENERATE),
    ],
)
def test_routing_actions(category: SafetyCategory, action: SafetyAction) -> None:
    """SAFE-02/04/05: every category maps to its locked action (D-03/04/05/06)."""
    assert route(SafetyVerdict(category=category)) is action


def test_route_covers_every_category() -> None:
    """Every SafetyCategory member has a route (no silent fall-through)."""
    for member in SafetyCategory:
        assert isinstance(route(SafetyVerdict(category=member)), SafetyAction)


def test_normal_routes_to_plain_generation() -> None:
    """SAFE-01/02: a normal verdict routes to plain generation (no safety_modifier)."""
    assert route(SafetyVerdict(category=SafetyCategory.NORMAL)) is SafetyAction.GENERATE


def test_sensitive_action_is_continue_not_block() -> None:
    """SAFE-02 / D-05: *_sensitive continues generation (silent softening), not a hard block."""
    assert route(SafetyVerdict(category=SafetyCategory.HEALTH_SENSITIVE)) is (
        SafetyAction.SAFETY_MODIFIER
    )
    # SAFETY_MODIFIER and GENERATE both continue to a draw; REFUSAL/REDIRECT do not.
    assert SafetyAction.SAFETY_MODIFIER.continues_to_draw is True
    assert SafetyAction.GENERATE.continues_to_draw is True
    assert SafetyAction.REFUSAL.continues_to_draw is False
    assert SafetyAction.REDIRECT.continues_to_draw is False


def test_module_uses_structured_output_not_json_loads() -> None:
    """SAFE-01: the service relies on structured output, never ``json.loads`` of model text."""
    import app.services.safety as safety_module

    with open(safety_module.__file__ or "", encoding="utf-8") as fh:
        text = fh.read()
    assert "output_format=SafetyVerdict" in text
    # No actual parse-and-load of model text (the docstring may mention the anti-pattern).
    assert "json.loads(" not in text
    # Classify uses the Haiku alias, never a dated snapshot.
    assert CLASSIFY_MODEL == "claude-haiku-4-5"
