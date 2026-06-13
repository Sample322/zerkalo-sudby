"""SAFE-06 (backend) — brand-voice ban-list guard on generated copy.

Implemented in Plan 04-02 (backend brand guard). The backend ``BANNED_BRAND_TOKENS`` /
``contains_banned_brand_token`` is a 1:1 port of the canonical frontend regex from
``frontend/src/reading/copy.ts`` (W-1) — one source of truth. These cases mirror the frontend
``copy.test.ts`` cases exactly: it detects AI / нейросеть / модель / сгенерировано and the
standalone Cyrillic «ИИ» token, WITHOUT false-positiving benign words that merely contain the
«ии» bigram (гармонии / линии / версии / комиссии).

Disposition (RESEARCH Open Question 2): LOG + FLAG — the guard never fails the reading.
"""

from __future__ import annotations

from app.core.brand_guard import BANNED_BRAND_TOKENS, contains_banned_brand_token
from app.schemas.reading import ReadingOutput  # noqa: F401 — pins the guarded contract


def test_detects_banned_tokens() -> None:
    """SAFE-06: AI/ИИ/нейросеть/модель/сгенерировано in generated copy is flagged."""
    assert contains_banned_brand_token("сгенерировано ИИ") is True
    assert contains_banned_brand_token("это ответ нейросети") is True
    assert contains_banned_brand_token("наша модель") is True
    assert contains_banned_brand_token("AI reading") is True
    # Each banned stem in isolation (mirrors frontend copy.test.ts).
    assert contains_banned_brand_token("это AI") is True
    assert contains_banned_brand_token("нейросеть") is True
    assert contains_banned_brand_token("нейросети") is True
    assert contains_banned_brand_token("модель") is True
    assert contains_banned_brand_token("сгенерировано") is True
    assert contains_banned_brand_token("сгенерирован") is True
    # Standalone Cyrillic ИИ / ии token, case-insensitive, at various boundaries (W-1).
    assert contains_banned_brand_token("ИИ") is True
    assert contains_banned_brand_token("ии") is True
    assert contains_banned_brand_token("текст ии текст") is True
    assert contains_banned_brand_token("вопрос к ИИ.") is True


def test_no_false_positive_on_benign_ii() -> None:
    """SAFE-06: benign words containing «ии» (гармонии/линии/версии) are NOT flagged (W-1)."""
    assert contains_banned_brand_token("в гармонии с собой") is False
    assert contains_banned_brand_token("линии судьбы") is False
    assert contains_banned_brand_token("несколько версий") is False
    # Frontend benign-word set, mirrored exactly.
    assert contains_banned_brand_token("гармонии") is False
    assert contains_banned_brand_token("линии") is False
    assert contains_banned_brand_token("версии") is False
    assert contains_banned_brand_token("комиссии") is False


def test_brand_safe_copy_passes() -> None:
    """SAFE-06: brand-safe RU reading copy is not flagged."""
    assert contains_banned_brand_token("карты подсвечивают возможное направление") is False
    assert (
        contains_banned_brand_token(
            "Колода остаётся рядом: ответ всегда остаётся за тобой."
        )
        is False
    )
    assert contains_banned_brand_token("") is False


def test_pattern_is_stateless_non_global() -> None:
    """The compiled pattern must be reusable: repeated calls on the same input still match.

    (A Python ``re.Pattern`` is inherently stateless via ``.search``; this guards the public
    contract the frontend relies on — ``BANNED_BRAND_TOKENS`` is a compiled, reusable pattern.)
    """
    assert BANNED_BRAND_TOKENS.search("ai") is not None
    assert BANNED_BRAND_TOKENS.search("ai") is not None
    assert BANNED_BRAND_TOKENS.search("гармонии") is None
