"""RED stubs — Telegram initData validation (AUTH-02).

Wave-0 placeholders so the VALIDATION.md node IDs are collectable now. The owning plan
(Plan 04) REMOVES the ``@pytest.mark.skip`` and implements each body against the real
``validate_init_data`` (RESEARCH Pattern 3), using ``make_init_data`` from conftest to
build valid / tampered / stale / missing-hash variants.

DO NOT implement these here — that is Plan 04's job. Shipping a self-passing skipped test
as "done" is explicitly disallowed by the plan.
"""

from __future__ import annotations

import pytest

_OWNER = "Wave 0 stub — implemented in Plan 04 (telegram_auth slice)"


@pytest.mark.skip(reason=_OWNER)
def test_forged_hash_rejected() -> None:
    """AUTH-02: a forged ``hash`` must be rejected (401 / ValueError)."""
    raise NotImplementedError("Plan 04 implements initData forged-hash rejection")


@pytest.mark.skip(reason=_OWNER)
def test_tampered_field_rejected() -> None:
    """AUTH-02: mutating a field after signing (hash mismatch) must be rejected."""
    raise NotImplementedError("Plan 04 implements initData tampered-field rejection")


@pytest.mark.skip(reason=_OWNER)
def test_stale_auth_date_rejected() -> None:
    """AUTH-02: an ``auth_date`` older than the freshness window must be rejected."""
    raise NotImplementedError("Plan 04 implements initData stale auth_date rejection")


@pytest.mark.skip(reason=_OWNER)
def test_missing_hash_rejected() -> None:
    """AUTH-02: initData with no ``hash`` field must be rejected."""
    raise NotImplementedError("Plan 04 implements initData missing-hash rejection")
