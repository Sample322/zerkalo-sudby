"""SAFE-03 / D-06 — the safety gate runs BEFORE the draw and short-circuits crisis/abusive.

Wave-0 stub — implemented in Plan 04-05 (ReadingService gate-before-draw ordering). Injects a
parametrized ``fake_safety`` (``crisis_sensitive`` / ``abusive_or_manipulative``) + ``fake_llm``
against ``seeded_catalog``. The body will assert:
  * **crisis** → a refusal response (supportive, NOT a mystical prediction, suggests a live
    specialist — D-03/04), with NO card draw, NO generation call, and the limit kept (SAFE-03);
  * **abusive_or_manipulative** → a gentle in-character redirect, NO draw, limit kept (D-06);
  * the gate ran BEFORE ``CardDrawService`` — asserted via ``fake_safety.calls`` incrementing
    while ``fake_llm.calls == 0`` and no ``reading_cards`` rows were written.

Imports the classify enum to pin the categories the gate routes on.
"""

from __future__ import annotations

import pytest

from app.schemas.reading import SafetyCategory  # noqa: F401 — pins the gated categories


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (gate-before-draw)")
async def test_crisis_short_circuits_before_draw(
    auth_client: object, fake_llm: object, fake_safety: object, seeded_catalog: dict
) -> None:
    """SAFE-03/D-03: crisis → refusal, NO draw, NO generation, limit kept."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (gate-before-draw)")
async def test_abusive_redirects_without_draw(
    auth_client: object, fake_llm: object, fake_safety: object, seeded_catalog: dict
) -> None:
    """D-06: abusive_or_manipulative → gentle redirect, NO draw, limit kept."""
    raise NotImplementedError
