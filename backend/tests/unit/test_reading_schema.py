"""DB-free schema assertions for the Phase-4 reading contracts (READ-03/05/06, SAFE-01).

Born green in Plan 04-01 (the schema ships in the same task) — NOT a skipped stub. Verifies:
  * the fused §17+§18 ``ReadingOutput`` round-trips and rejects a bad shape (the validation seam
    Plan 03's corrective-retry depends on, T-04-11);
  * the §17 length target lives in the field *description*, NOT as a ``maxLength`` constraint
    (RESEARCH Pitfall 1 — the SDK strips length constraints before sending);
  * the classify contract exposes exactly the 7 TZ §20.4 categories;
  * the request contract enforces HOME-01 (10–500) and allows HOME-02 (empty → general).
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.schemas.reading import (
    CardInterpretation,
    ReadingCreate,
    ReadingOut,
    ReadingOutput,
    ReadingSummary,
    SafetyCategory,
    SafetyVerdict,
)


def _good_output() -> ReadingOutput:
    return ReadingOutput(
        cards=[
            CardInterpretation(
                position_index=0,
                short_meaning="Карта говорит о тихом начале перемен.",
                interpretation="Сейчас многое только зреет. Дай ситуации немного времени.",
                mystical_accent="Колода шепчет о первом шаге в тумане.",
                soft_advice="Не торопи события — позволь им сложиться.",
            )
        ],
        summary=ReadingSummary(
            summary_short="Расклад о начале нового внутреннего движения.",
            connection="Карты вместе указывают на один общий поворот.",
            main_factor="Готовность к мягким переменам.",
            attention_point="На чувства, которые проявляются не сразу.",
            advice="Двигайся спокойно и без спешки.",
            closing_phrase="Колода остаётся рядом: выбор всегда за тобой.",
        ),
    )


def test_reading_output_roundtrip() -> None:
    """A well-formed object serializes and ``model_validate_json`` round-trips it back."""
    original = _good_output()
    restored = ReadingOutput.model_validate_json(original.model_dump_json())

    assert restored == original
    assert restored.cards[0].position_index == 0
    assert restored.summary.main_factor == "Готовность к мягким переменам."


def test_reading_output_rejects_bad_shape() -> None:
    """A missing required field / wrong type raises ``ValidationError`` (the retry trigger)."""
    # summary.advice missing entirely.
    bad = {
        "cards": [
            {
                "position_index": 0,
                "short_meaning": "x",
                "interpretation": "y",
                "mystical_accent": "z",
                "soft_advice": "w",
            }
        ],
        "summary": {
            "summary_short": "a",
            "connection": "b",
            "main_factor": "c",
            "attention_point": "d",
            # "advice" missing
            "closing_phrase": "e",
        },
    }
    with pytest.raises(ValidationError):
        ReadingOutput.model_validate_json(json.dumps(bad))

    # Wrong type for position_index.
    bad_type = json.loads(_good_output().model_dump_json())
    bad_type["cards"][0]["position_index"] = "not-an-int"
    with pytest.raises(ValidationError):
        ReadingOutput.model_validate_json(json.dumps(bad_type))


def test_length_lives_in_description_not_constraint() -> None:
    """Pitfall 1: the 140-char target is in the description, NOT a maxLength constraint.

    The Anthropic SDK strips ``maxLength``/``minLength`` before sending, so a constraint would
    be silently ignored. The model only learns the limit from the field description.
    """
    schema = ReadingOutput.model_json_schema()
    card_props = schema["$defs"]["CardInterpretation"]["properties"]
    short_meaning = card_props["short_meaning"]

    assert "140" in short_meaning["description"]
    assert "maxLength" not in short_meaning
    assert "minLength" not in short_meaning

    # And no LLM-output string field carries a length constraint anywhere in the schema.
    for defn in schema["$defs"].values():
        for prop in defn.get("properties", {}).values():
            assert "maxLength" not in prop
            assert "minLength" not in prop


def test_safety_category_members() -> None:
    """The classify contract exposes exactly the 7 TZ §20.4 categories and validates."""
    expected = {
        "normal",
        "relationship_sensitive",
        "financial_sensitive",
        "health_sensitive",
        "legal_sensitive",
        "crisis_sensitive",
        "abusive_or_manipulative",
    }
    assert {member.value for member in SafetyCategory} == expected
    assert len(SafetyCategory) == 7

    verdict = SafetyVerdict.model_validate_json('{"category": "crisis_sensitive"}')
    assert verdict.category is SafetyCategory.CRISIS_SENSITIVE

    with pytest.raises(ValidationError):
        SafetyVerdict.model_validate_json('{"category": "not_a_category"}')


def test_reading_create_validates_question_bounds() -> None:
    """HOME-01: non-empty question must be 10–500 chars; HOME-02: empty → None (general)."""
    base = {"topic": "love", "deck_slug": "classic", "spread_slug": "three_keys"}

    # HOME-02: empty / whitespace-only question normalizes to None (general reading).
    assert ReadingCreate(question="", **base).question is None
    assert ReadingCreate(question="   ", **base).question is None
    assert ReadingCreate(**base).question is None

    # HOME-01: a too-short non-empty question is rejected.
    with pytest.raises(ValidationError):
        ReadingCreate(question="коротко", **base)  # < 10 chars

    # HOME-01: a too-long question is rejected.
    with pytest.raises(ValidationError):
        ReadingCreate(question="я" * 501, **base)

    # A valid question is accepted and stripped.
    ok = ReadingCreate(question="  Что меня ждёт в отношениях?  ", **base)
    assert ok.question == "Что меня ждёт в отношениях?"
    assert ok.reversals_enabled is True  # D-13 default


def test_reading_out_mirrors_frontend_mock_shape() -> None:
    """``ReadingOut`` carries the per-card + 5 summary fields the result screen renders."""
    card_fields = set(ReadingOut.model_fields["cards"].annotation.__args__[0].model_fields)
    assert {"name", "position_title", "orientation", "short_meaning", "interpretation",
            "deck_accent"} <= card_fields

    out = ReadingOut(reading_id="00000000-0000-0000-0000-000000000000", status="completed")
    assert out.cards == []
    assert out.summary is None
    assert out.remaining_limits is None
