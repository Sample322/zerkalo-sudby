"""DB-free schema assertions for the catalog projections (DECK-02/04, SPREAD-02)."""

from __future__ import annotations

from types import SimpleNamespace

from app.schemas.catalog import DeckDetailOut, DeckOut, SpreadOut, SpreadPositionOut

# Base card meaning/advice must NEVER cross the catalog serialization boundary (DECK-04).
FORBIDDEN_FIELDS = {
    "meaning_upright",
    "meaning_reversed",
    "advice_upright",
    "advice_reversed",
}


def test_deck_schemas_expose_prompt_modifier_without_base_meaning() -> None:
    for model in (DeckOut, DeckDetailOut):
        fields = set(model.model_fields)
        assert "prompt_modifier" in fields  # DECK-02
        assert not (fields & FORBIDDEN_FIELDS)  # DECK-04 IP boundary


def test_spread_out_carries_positions_not_card_meaning() -> None:
    fields = set(SpreadOut.model_fields)
    assert "positions" in fields
    assert not (fields & FORBIDDEN_FIELDS)


def test_spread_out_nests_positions_from_attributes() -> None:
    stub = SimpleNamespace(
        slug="three_keys",
        title="Три ключа",
        description=None,
        card_count=3,
        recommended_topics=["love", "general"],
        positions=[
            SimpleNamespace(
                position_index=1,
                title="Суть ситуации",
                description="центральная энергия вопроса",
                prompt_instruction="читай как ядро ситуации",
            )
        ],
    )

    out = SpreadOut.model_validate(stub)

    assert out.slug == "three_keys"
    assert len(out.positions) == 1
    assert isinstance(out.positions[0], SpreadPositionOut)
    assert out.positions[0].position_index == 1
    assert out.positions[0].title == "Суть ситуации"
