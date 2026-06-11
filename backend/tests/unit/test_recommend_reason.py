"""DB-free tests for the recommendation reason builder + fallback constant (SPREAD-04)."""

from __future__ import annotations

import re
from types import SimpleNamespace

from app.services.catalog import DEFAULT_SPREAD_SLUG, _build_reason

# Brand voice: a reason must never expose the machine behind the ritual (TZ §0).
BANNED = re.compile(r"ai|нейросет|модель|сгенерирован", re.IGNORECASE)


def test_default_spread_constant() -> None:
    assert DEFAULT_SPREAD_SLUG == "three_keys"


def test_reason_never_leaks_brand_voice() -> None:
    decks = [
        None,
        SimpleNamespace(title="Лунное Зеркало", atmosphere="ночь, луна, вода"),
        SimpleNamespace(title="Колода Пути", atmosphere=None),
    ]
    topics = [
        "love",
        "work",
        "money",
        "choice",
        "day",
        "self_reflection",
        "general",
        "unmapped_topic",
    ]
    for deck in decks:
        for topic in topics:
            reason = _build_reason(topic, deck)
            assert reason  # non-empty
            assert not BANNED.search(reason), f"brand-voice leak in reason: {reason!r}"


def test_reason_mentions_topic_label() -> None:
    assert "любовь" in _build_reason("love", None)
    assert "деньги" in _build_reason("money", None)
