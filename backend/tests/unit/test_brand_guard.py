"""SAFE-06 (backend) — brand-voice ban-list guard on generated copy.

Wave-0 stub — implemented in Plan 04-02 (backend brand guard). The body will assert:
  * the backend guard (a port of the canonical frontend ``BANNED_BRAND_TOKENS`` from
    ``reading/copy.ts``) detects the standalone Cyrillic ``ИИ`` token + AI/нейросеть/модель/
    сгенерировано WITHOUT false-positiving benign words that merely contain the «ии» bigram
    (гармонии / линии / версии);
  * generated/response copy that contains a banned token is flagged (READ-11/SAFE-06).

One source of truth: the backend ban-list mirrors the frontend regex (W-1), so this stub
references the contract it will guard (``ReadingOutput`` text fields).
"""

from __future__ import annotations

import pytest

from app.schemas.reading import ReadingOutput  # noqa: F401 — pins the guarded contract


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-02 (backend brand guard)")
def test_guard_flags_banned_tokens() -> None:
    """SAFE-06: AI/ИИ/нейросеть/модель/сгенерировано in generated copy is flagged."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-02 (backend brand guard)")
def test_guard_ignores_benign_ii_bigram() -> None:
    """SAFE-06: benign words containing «ии» (гармонии/линии/версии) are NOT flagged (W-1)."""
    raise NotImplementedError
