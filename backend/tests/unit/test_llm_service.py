"""READ-03/04 / D-12 — ``LLMService`` resilience contract (single ``messages.parse`` call).

The five behaviours below pin the locked contract with a MOCKED ``AsyncAnthropic`` client —
no network, no ``ANTHROPIC_API_KEY`` needed. A scripted ``messages.parse`` ``AsyncMock`` returns
a fake response object (``.parsed_output`` / ``.usage`` / ``.stop_reason`` / ``.model``) or raises,
so we can assert:
  * success on attempt 1 uses Haiku and makes exactly one call;
  * a ``ValidationError`` on attempt 1 escalates the corrective retry to Sonnet (D-12);
  * a double failure reraises after exactly two attempts (no templated fallback);
  * usage / latency / model / stop_reason are extracted onto the result (ANALYTICS-02);
  * a non-retryable exception is NOT retried (single attempt).

These map to the 04-VALIDATION Req→Test rows for READ-03/04.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import anthropic
import pytest
from pydantic import ValidationError

from app.schemas.reading import (
    CardInterpretation,
    ReadingOutput,
    ReadingSummary,
)
from app.services.llm import (
    HAIKU_MODEL,
    SONNET_MODEL,
    GenerationResult,
    LLMGenerationError,
    LLMService,
)


# --- helpers ----------------------------------------------------------------------------
def _valid_output() -> ReadingOutput:
    """A minimal schema-valid ``ReadingOutput`` (the success-path ``parsed_output``)."""
    return ReadingOutput(
        cards=[
            CardInterpretation(
                position_index=0,
                short_meaning="Короткое значение карты.",
                interpretation="Глубокая интерпретация под вопрос. Ещё одно предложение.",
                mystical_accent="Лес шепчет о переменах.",
                soft_advice="Прислушайся к себе без спешки.",
            )
        ],
        summary=ReadingSummary(
            summary_short="Короткий итог расклада.",
            connection="Карты связаны общим узором перемен.",
            main_factor="Внутренняя готовность к шагу.",
            attention_point="Не торопи решение.",
            advice="Дай себе время.",
            closing_phrase="Тропа уже под ногами.",
        ),
    )


def _fake_response(
    *, model: str, stop_reason: str = "end_turn", input_tokens: int = 321, output_tokens: int = 654
) -> SimpleNamespace:
    """A stand-in for ``ParsedMessage``: exposes the attributes ``LLMService`` reads."""
    return SimpleNamespace(
        parsed_output=_valid_output(),
        model=model,
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def _make_service(parse_mock: AsyncMock) -> LLMService:
    """Wrap a scripted ``messages.parse`` AsyncMock in a fake AsyncAnthropic-shaped client."""
    fake_client = SimpleNamespace(messages=SimpleNamespace(parse=parse_mock))
    return LLMService(client=fake_client)


def _validation_error() -> ValidationError:
    """A real ``pydantic.ValidationError`` — the retry trigger ``parsed_output`` raises."""
    try:
        ReadingOutput.model_validate({"cards": "not-a-list", "summary": {}})
    except ValidationError as exc:
        return exc
    raise AssertionError("expected ValidationError")  # pragma: no cover


# --- behaviours -------------------------------------------------------------------------
async def test_success_first_attempt_haiku() -> None:
    """Valid output on attempt 1 → returns it; model == Haiku; exactly one call."""
    parse_mock = AsyncMock(return_value=_fake_response(model=HAIKU_MODEL))
    service = _make_service(parse_mock)

    result = await service.generate(system="sys", user_prompt="usr")

    assert isinstance(result, GenerationResult)
    assert isinstance(result.output, ReadingOutput)
    assert parse_mock.await_count == 1
    assert parse_mock.await_args.kwargs["model"] == HAIKU_MODEL
    assert result.model_name == HAIKU_MODEL


async def test_corrective_retry_escalates_to_sonnet() -> None:
    """ValidationError on attempt 1, valid on attempt 2 → succeeds; attempt 2 uses Sonnet (D-12)."""
    parse_mock = AsyncMock(
        side_effect=[_validation_error(), _fake_response(model=SONNET_MODEL)]
    )
    service = _make_service(parse_mock)

    result = await service.generate(system="sys", user_prompt="usr")

    assert parse_mock.await_count == 2
    models_used = [call.kwargs["model"] for call in parse_mock.await_args_list]
    assert models_used == [HAIKU_MODEL, SONNET_MODEL]
    assert result.model_name == SONNET_MODEL


async def test_exhausted_reraises() -> None:
    """ValidationError twice → generate raises after exactly two attempts (no fallback)."""
    parse_mock = AsyncMock(side_effect=[_validation_error(), _validation_error()])
    service = _make_service(parse_mock)

    with pytest.raises(LLMGenerationError):
        await service.generate(system="sys", user_prompt="usr")

    assert parse_mock.await_count == 2


async def test_usage_and_metadata_extracted() -> None:
    """The result exposes input/output tokens, latency_ms, model_name, stop_reason."""
    parse_mock = AsyncMock(
        return_value=_fake_response(
            model=HAIKU_MODEL, stop_reason="end_turn", input_tokens=123, output_tokens=456
        )
    )
    service = _make_service(parse_mock)

    result = await service.generate(system="sys", user_prompt="usr")

    assert result.input_tokens == 123
    assert result.output_tokens == 456
    assert result.model_name == HAIKU_MODEL
    assert result.stop_reason == "end_turn"
    assert isinstance(result.latency_ms, int)
    assert result.latency_ms >= 0


async def test_refusal_stop_reason_triggers_retry() -> None:
    """A ``refusal``/``max_tokens`` stop_reason is treated as a retry trigger (Pitfall 2)."""
    parse_mock = AsyncMock(
        side_effect=[
            _fake_response(model=HAIKU_MODEL, stop_reason="max_tokens"),
            _fake_response(model=SONNET_MODEL, stop_reason="end_turn"),
        ]
    )
    service = _make_service(parse_mock)

    result = await service.generate(system="sys", user_prompt="usr")

    assert parse_mock.await_count == 2
    assert result.stop_reason == "end_turn"
    assert result.model_name == SONNET_MODEL


async def test_non_retryable_not_retried() -> None:
    """A non-retryable exception type is NOT retried (single attempt, raised as-is)."""

    class _Boom(Exception):
        pass

    parse_mock = AsyncMock(side_effect=_Boom("not retryable"))
    service = _make_service(parse_mock)

    with pytest.raises(_Boom):
        await service.generate(system="sys", user_prompt="usr")

    assert parse_mock.await_count == 1


def test_module_uses_model_aliases_not_dated_snapshots() -> None:
    """D-12 / CLAUDE.md: aliases only — no dated ``-YYYYMMDD`` snapshot in the module."""
    import re

    import app.services.llm as llm_module

    assert HAIKU_MODEL == "claude-haiku-4-5"
    assert SONNET_MODEL == "claude-sonnet-4-6"
    source = (llm_module.__file__ or "")
    with open(source, encoding="utf-8") as fh:
        text = fh.read()
    # No dated model snapshot (e.g. claude-haiku-4-5-20251001).
    assert re.search(r"claude-[a-z]+-4-[0-9]-\d{8}", text) is None


def test_anthropic_retryable_types_present() -> None:
    """RETRYABLE includes the verified transient anthropic error types + ValidationError."""
    from app.services.llm import RETRYABLE

    assert ValidationError in RETRYABLE
    assert anthropic.APIStatusError in RETRYABLE
    assert anthropic.APIConnectionError in RETRYABLE
    assert TimeoutError in RETRYABLE
