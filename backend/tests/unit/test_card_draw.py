"""READ-02 — CSPRNG card draw (count / orientation / cryptographic randomness).

Implemented in Plan 04-02 (``CardDrawService``). The DB-free behaviours below drive the
pure orientation/assembly helpers with an INJECTED rng (a seeded ``random.Random`` is fine as
a *test double* for the rng port — the production default is ``secrets.SystemRandom``, asserted
separately by ``test_uses_csprng``), so the count / reversals / 70-30-ratio guarantees are
deterministic and stable. The single DB-touching path uses the ``seeded_catalog`` fixture and
``pytest.skip`` when Postgres is down — mirroring the rest of the integration suite.

These behaviours map to the 04-VALIDATION Req→Test rows for READ-02
(``test_card_draw.py`` + ``test_card_draw.py::test_uses_csprng``).
"""

from __future__ import annotations

import inspect
import random
import secrets
from types import SimpleNamespace

import pytest

from app.models.enums import Orientation
from app.services import card_draw
from app.services.card_draw import (
    REVERSED_PROBABILITY,
    _assign_orientations,
)


def _positions(n: int) -> list[SimpleNamespace]:
    """A spread's positions, ordered by position_index (mirrors ``SpreadPosition``)."""
    return [SimpleNamespace(position_index=i, title=f"Позиция {i}") for i in range(n)]


def test_draw_count_matches_positions() -> None:
    """READ-02: drawn orientation count equals the spread's position count (by construction)."""
    rng = random.Random(1234)
    for n in (1, 3, 4, 5):
        orientations = _assign_orientations(
            count=n, reversals_enabled=True, rng=rng
        )
        assert len(orientations) == n


def test_reversals_off_all_upright() -> None:
    """READ-02: reversals_enabled=False → every orientation is upright, regardless of rng."""
    # Even an rng that "always reverses" must yield all-upright when reversals are off.
    always_reverse = SimpleNamespace(random=lambda: 0.0)
    orientations = _assign_orientations(
        count=4, reversals_enabled=False, rng=always_reverse
    )
    assert orientations == [Orientation.UPRIGHT] * 4


def test_reversals_on_produces_both() -> None:
    """READ-02: reversals_enabled=True → both orientations appear; domain is exactly {up, rev}."""
    rng = random.Random(7)
    orientations = _assign_orientations(count=200, reversals_enabled=True, rng=rng)
    assert set(orientations) == {Orientation.UPRIGHT, Orientation.REVERSED}
    assert all(o in (Orientation.UPRIGHT, Orientation.REVERSED) for o in orientations)


def test_reversed_ratio_approx_30() -> None:
    """READ-02 / D-13: over a large seeded sample, reversed share ≈ 30% within tolerance."""
    rng = random.Random(2024)
    n = 20_000
    orientations = _assign_orientations(count=n, reversals_enabled=True, rng=rng)
    reversed_share = sum(o is Orientation.REVERSED for o in orientations) / n
    assert REVERSED_PROBABILITY == pytest.approx(0.30)
    assert reversed_share == pytest.approx(0.30, abs=0.02)


def test_uses_csprng() -> None:
    """READ-02 / §12.5: the draw uses secrets/SystemRandom (CSPRNG), never plain ``random``.

    The module-level default rng must be a real CSPRNG instance, and the source must contain no
    non-secure ``random``-module import or call for the draw (only ``secrets.SystemRandom``).
    """
    assert isinstance(card_draw._rng, secrets.SystemRandom)
    source = inspect.getsource(card_draw)
    assert "secrets.SystemRandom" in source
    # No stdlib pseudo-random import or call anywhere in the draw service.
    assert "import random" not in source
    assert "random.shuffle" not in source
    assert "random.random" not in source
