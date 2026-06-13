"""READ-03/05/06/11 + SAFE-02 + ANALYTICS-02 — the fused single-call PromptEngine.

Implemented in Plan 04-04 (``app.services.prompt_engine``). The PromptEngine is PURE string
assembly over already-loaded ``prompt_templates`` rows + ``DrawnCard`` records, so every behaviour
below is exercised WITHOUT Postgres or the network — the pure helpers (``build_system_block`` /
``build_user_block`` / ``compose_prompt_version``) take constructed rows + records, and the
copy-resolution path (``refusal_copy`` / ``redirect_copy``) is driven through a tiny in-test fake
session that returns canned rows. The DB-backed ``PromptEngine.build`` round-trip against the real
seed lives in the integration suite (``seeded_catalog``); here we assert the assembly contract.

These behaviours map to the 04-04 plan ``<behavior>`` block:
  * test_system_includes_deck_signature
  * test_user_prompt_has_one_block_per_card
  * test_safety_modifier_appended_only_when_sensitive
  * test_russian_and_length_instructed
  * test_prompt_version_resolved
  * test_refusal_and_redirect_copy_available
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.brand_guard import contains_banned_brand_token
from app.models.enums import Orientation, PromptTemplateType
from app.services.card_draw import DrawnCard
from app.services.prompt_engine import (
    RUSSIAN_INSTRUCTION,
    SHORT_MEANING_MAX_CHARS,
    DeckCardStyle,
    PromptEngine,
    build_system_block,
    build_user_block,
    compose_prompt_version,
    deck_modifier_slug,
)


# --- Pure constructors for the already-loaded rows / records the helpers consume ---------------
def _template(slug: str, type_: PromptTemplateType, text: str, version: str = "v1") -> SimpleNamespace:
    """A stand-in for a loaded ``PromptTemplate`` row (the helpers read attributes only)."""
    return SimpleNamespace(slug=slug, type=type_, template_text=text, version=version)


def _position(index: int, title: str, instruction: str) -> SimpleNamespace:
    """A stand-in for a loaded ``SpreadPosition`` (ordered by position_index)."""
    return SimpleNamespace(
        position_index=index,
        title=title,
        description=f"Смысл позиции {index}",
        prompt_instruction=instruction,
    )


def _spread(n: int) -> SimpleNamespace:
    """A stand-in for a loaded ``SpreadType`` with ``n`` positions (mirrors catalog eager-load)."""
    return SimpleNamespace(
        slug="three_keys",
        title="Три ключа",
        card_count=n,
        positions=[
            _position(i, f"Позиция {i}", f"Прочитай карту в позиции {i}.") for i in range(n)
        ],
    )


def _deck() -> SimpleNamespace:
    """A stand-in for a loaded ``Deck`` (the builder reads title/atmosphere/tone/slug)."""
    return SimpleNamespace(
        slug="moon_mirror",
        title="Лунное Зеркало",
        atmosphere="тихий ночной свет",
        tone="мягкий, интуитивный",
    )


def _draw(n: int) -> list[DrawnCard]:
    """``n`` drawn cards with distinct position_index + alternating orientation."""
    return [
        DrawnCard(
            card_id=f"card-{i}",
            deck_card_id=f"deckcard-{i}",
            position_id=f"pos-{i}",
            position_index=i,
            orientation=Orientation.REVERSED if i % 2 else Orientation.UPRIGHT,
            card_title=f"Карта {i}",
            meaning_upright=f"Прямое значение {i}",
            meaning_reversed=f"Перевёрнутое значение {i}",
            keywords_upright=(f"ключ-{i}-а", f"ключ-{i}-б"),
            keywords_reversed=(f"ключ-{i}-в",),
        )
        for i in range(n)
    ]


# A deck modifier row that already carries BOTH the §19 tone and the mandatory D-02 signature
# (mirrors the seed authored in Task 1).
_DECK_MODIFIER_TEXT = (
    "Говори мягко, глубоко и интуитивно. Используй образы луны, воды и отражения.\n\n"
    "Обязательная подпись колоды: в каждом раскладе обязательно вплетай образ воды, "
    "луны или отражения, через который проступает скрытое чувство."
)
_SIGNATURE_MARKER = "Обязательная подпись колоды"

_SYSTEM_TEXT = "Ты — голос мистической цифровой колоды. Принципы: пиши бережно и атмосферно."
_SINGLE_CARD_TEXT = "Объясни значение каждой карты в её позиции и свяжи с вопросом."
_FINAL_SUMMARY_TEXT = "Объясни, как карты связаны, назови главный фактор и дай мягкий совет."
_SAFETY_TEXT = (
    "Эта тема требует особой осторожности. Воспринимай ответ как мягкую подсказку для "
    "размышления, а не как окончательный вывод."
)


def _build_user(*, n: int = 3, safety_text: str | None = None) -> str:
    """Helper that assembles a user block for ``n`` cards with the standard fixtures."""
    return build_user_block(
        single_card_text=_SINGLE_CARD_TEXT,
        final_summary_text=_FINAL_SUMMARY_TEXT,
        draw_records=_draw(n),
        spread=_spread(n),
        deck=_deck(),
        question="Что мне важно увидеть в отношениях?",
        topic="love",
        card_styles={
            f"deckcard-{i}": DeckCardStyle(
                keywords=(f"стиль-{i}",),
                upright_modifier=f"Прямой модификатор {i}",
                reversed_modifier=f"Перевёрнутый модификатор {i}",
            )
            for i in range(n)
        },
        safety_text=safety_text,
    )


# --- Behaviours --------------------------------------------------------------------------------
def test_system_includes_deck_signature() -> None:
    """The system block = §16 principles + the deck's §19 modifier + its D-02 signature."""
    system = build_system_block(
        system_text=_SYSTEM_TEXT, deck_modifier_text=_DECK_MODIFIER_TEXT
    )
    # §16 principles present.
    assert "голос мистической цифровой колоды" in system
    # §19 tone present.
    assert "образы луны, воды и отражения" in system
    # D-02 mandatory signature instruction present (the guaranteed per-deck device).
    assert _SIGNATURE_MARKER in system
    assert "вплетай образ воды" in system


def test_user_prompt_has_one_block_per_card() -> None:
    """The user block carries one position_index-anchored context per drawn card + the summary."""
    for n in (1, 3, 4):
        user = _build_user(n=n)
        # Exactly one anchored block per position_index, in order.
        for i in range(n):
            assert f"position_index={i}" in user
            assert f"Карта {i}" in user
        assert user.count("Карта в позиции position_index=") == n
        # The §18 summary instruction is fused into the same task.
        assert "общий итог расклада" in user
        assert _FINAL_SUMMARY_TEXT in user
        # Orientation-aware meaning: upright card 0 uses its upright meaning, reversed card 1 reversed.
        assert "Прямое значение 0" in user
        if n > 1:
            assert "Перевёрнутое значение 1" in user


def test_orientation_selects_meaning_and_modifier() -> None:
    """An upright card surfaces its upright meaning/modifier; a reversed one the reversed set."""
    user = _build_user(n=2)
    # Card 0 = upright → upright universal meaning + upright deck modifier.
    assert "Прямое значение 0" in user
    assert "Прямой модификатор 0" in user
    # Card 1 = reversed → reversed universal meaning + reversed deck modifier.
    assert "Перевёрнутое значение 1" in user
    assert "Перевёрнутый модификатор 1" in user


def test_safety_modifier_appended_only_when_sensitive() -> None:
    """The §20.3 safety fragment is present iff a safety_text is supplied (D-05 / SAFE-02)."""
    normal = _build_user(safety_text=None)
    assert _SAFETY_TEXT not in normal

    sensitive = _build_user(safety_text=_SAFETY_TEXT)
    assert _SAFETY_TEXT in sensitive


def test_russian_and_length_instructed() -> None:
    """The task restates Russian output (D-14) and the ≤140-char short_meaning target (D-10)."""
    user = _build_user()
    assert RUSSIAN_INSTRUCTION in user
    assert "русском" in user
    assert str(SHORT_MEANING_MAX_CHARS) in user
    assert SHORT_MEANING_MAX_CHARS == 140
    # Pitfall 3: the model is told to return exactly card_count interpretations by position_index.
    assert "position_index" in user
    assert "ровно 3" in user


def test_general_reading_when_question_empty() -> None:
    """An empty/None question becomes an explicit general-reading instruction (HOME-02)."""
    user = build_user_block(
        single_card_text=_SINGLE_CARD_TEXT,
        final_summary_text=_FINAL_SUMMARY_TEXT,
        draw_records=_draw(3),
        spread=_spread(3),
        deck=_deck(),
        question=None,
        topic="general",
    )
    assert "общий расклад" in user
    assert "не задан" in user


def test_prompt_version_resolved() -> None:
    """prompt_version is composed from the active templates' type@version fields (ANALYTICS-02)."""
    templates = [
        _template("system", PromptTemplateType.SYSTEM, _SYSTEM_TEXT, version="v1"),
        _template(
            deck_modifier_slug("moon_mirror"),
            PromptTemplateType.DECK_MODIFIER,
            _DECK_MODIFIER_TEXT,
            version="v2",
        ),
        _template("single_card", PromptTemplateType.SINGLE_CARD, _SINGLE_CARD_TEXT, version="v1"),
        _template(
            "final_summary", PromptTemplateType.FINAL_SUMMARY, _FINAL_SUMMARY_TEXT, version="v1"
        ),
    ]
    version = compose_prompt_version(templates)
    assert version == "system@v1+deck_modifier@v2+single_card@v1+final_summary@v1"
    # Contains the load-bearing components the audit trail keys on.
    assert "system@" in version
    assert "deck_modifier@" in version

    # When the safety fragment is included, its version is appended too.
    with_safety = compose_prompt_version(
        [*templates, _template("safety", PromptTemplateType.SAFETY, _SAFETY_TEXT, version="v1")]
    )
    assert with_safety.endswith("safety@v1")


class _FakeResult:
    """Mimics ``session.execute(...)`` → ``.scalar_one_or_none()`` for the copy-resolution tests."""

    def __init__(self, row: object) -> None:
        self._row = row

    def scalar_one_or_none(self) -> object:
        return self._row


class _FakeSession:
    """A tiny async session double: returns a canned row per requested slug (no Postgres)."""

    def __init__(self, rows_by_slug: dict[str, object]) -> None:
        self._rows = rows_by_slug

    async def execute(self, stmt: object) -> _FakeResult:
        # The slug lives in the WHERE clause; pull it out of the compiled params.
        params = stmt.compile().params
        slug = next(v for k, v in params.items() if "slug" in k)
        return _FakeResult(self._rows.get(slug))


@pytest.mark.asyncio
async def test_refusal_and_redirect_copy_available() -> None:
    """refusal (generic, D-04) + redirect (D-06) copy resolve from the active rows (single source)."""
    refusal_row = _template(
        "refusal",
        PromptTemplateType.REFUSAL,
        "Бережно предложи обратиться к близкому человеку, которому ты доверяешь, или к специалисту.",
        version="v2",
    )
    redirect_row = _template(
        "redirect",
        PromptTemplateType.SAFETY,
        "Колода молчит на это. Задай вопрос от сердца — о том, что тебя по-настоящему волнует.",
    )
    # The fake row needs an ``is_active`` attr for the WHERE clause to compile; SimpleNamespace
    # ignores extra attributes on read, so add it.
    refusal_row.is_active = True
    redirect_row.is_active = True

    session = _FakeSession({"refusal": refusal_row, "redirect": redirect_row})
    engine = PromptEngine()

    refusal = await engine.refusal_copy(session)
    redirect = await engine.redirect_copy(session)

    # D-04: generic crisis copy, no region/phone specifics, fully out of the mystical frame.
    assert "специалисту" in refusal
    assert "регион" not in refusal
    assert not any(ch.isdigit() for ch in refusal)
    # D-06: the in-character abusive redirect.
    assert "Колода молчит" in redirect

    # SAFE-06: neither copy trips the brand-voice ban-list.
    assert not contains_banned_brand_token(refusal)
    assert not contains_banned_brand_token(redirect)


def test_assembled_copy_is_brand_safe() -> None:
    """The fully-assembled system + user prompt contains no banned brand tokens (READ-11)."""
    system = build_system_block(
        system_text=_SYSTEM_TEXT, deck_modifier_text=_DECK_MODIFIER_TEXT
    )
    user = _build_user(safety_text=_SAFETY_TEXT)
    # The engine-authored scaffolding + the seeded fragments under test are brand-safe. (The
    # canonical §16 system row legitimately names the forbidden words as a NEGATIVE instruction;
    # that pre-existing row is out of this plan's scope, so the fixture system text here is the
    # brand-safe shape the assembler must not corrupt.)
    assert not contains_banned_brand_token(system)
    assert not contains_banned_brand_token(user)
