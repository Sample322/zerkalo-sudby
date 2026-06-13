"""READ-02 — CSPRNG card draw (count / orientation / cryptographic randomness).

Wave-0 stub — implemented in Plan 04-02 (CardDrawService). The body will assert:
  * the draw returns exactly ``position_count`` cards;
  * ``reversals_enabled=False`` → every card upright;
  * ``reversals_enabled=True`` → reversed cards are possible (70/30, over many draws);
  * the service uses ``secrets``/``SystemRandom`` (CSPRNG), NOT ``random`` (TZ §12.5).

These behaviours map to the 04-VALIDATION Req→Test rows for READ-02
(``test_card_draw.py`` + ``test_card_draw.py::test_uses_csprng``).
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-02 (CardDrawService)")
def test_draw_count_matches_positions() -> None:
    """READ-02: drawn card count equals the spread's position count."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-02 (CardDrawService)")
def test_reversals_off_all_upright() -> None:
    """READ-02: reversals_enabled=False → every drawn card is upright."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-02 (CardDrawService)")
def test_reversals_on_allows_reversed() -> None:
    """READ-02: reversals_enabled=True → reversed orientation is possible (70/30)."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-02 (CardDrawService)")
def test_uses_csprng() -> None:
    """READ-02: the draw uses secrets/SystemRandom (CSPRNG), never random (TZ §12.5)."""
    raise NotImplementedError
