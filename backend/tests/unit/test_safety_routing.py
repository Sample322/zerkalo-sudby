"""SAFE-01/02/04/05 — safety classification routing + allowed/banned phrasing.

Wave-0 stub — implemented in Plan 04-03 (SafetyService + PromptEngine safety routing).
The body will assert:
  * normal → normal generation (no safety_modifier appended);
  * any ``*_sensitive`` → PromptEngine appends the ``safety`` template fragment (silent
    softening, D-05 — no UI badge);
  * the regex pre-filter resolves the highest-signal crisis terms WITHOUT a classify call,
    and an empty question (HOME-02) classifies as ``normal`` with no call (SAFE-01);
  * refusal/sensitive output avoids banned categorical/fatalistic formulations and uses the
    allowed soft phrasings ("карты указывают/подсвечивают/возможное направление/не приговор") —
    SAFE-04/05.

The classify contract (``SafetyCategory`` / ``SafetyVerdict``) is imported to keep the stub
collect-clean and pin the interface this plan builds against.
"""

from __future__ import annotations

import pytest

from app.schemas.reading import SafetyCategory, SafetyVerdict


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-03 (SafetyService routing)")
def test_normal_routes_to_plain_generation() -> None:
    """SAFE-01/02: normal verdict → normal generation, no safety_modifier."""
    assert SafetyVerdict(category=SafetyCategory.NORMAL).category is SafetyCategory.NORMAL
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-03 (SafetyService routing)")
def test_sensitive_appends_safety_modifier() -> None:
    """SAFE-02: a *_sensitive verdict appends the safety template fragment (D-05)."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-03 (SafetyService routing)")
def test_regex_prefilter_short_circuits_crisis_without_call() -> None:
    """SAFE-01: the regex pre-filter flags crisis terms with zero API cost; empty → normal."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-03 (SafetyService routing)")
def test_phrasing_uses_allowed_soft_formulations() -> None:
    """SAFE-04/05: output avoids banned categorical phrasing; uses allowed soft formulations."""
    raise NotImplementedError
