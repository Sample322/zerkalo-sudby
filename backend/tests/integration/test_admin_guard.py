"""RED stubs — admin allowlist guard (AUTH-05).

Wave-0 placeholders for VALIDATION.md node IDs. Plan 04 removes the skip and implements
``require_admin`` + an admin probe endpoint (e.g. ``GET /api/admin/ping``): a non-allowlisted
``telegram_id`` -> 403; an allowlisted one -> 200. The check is server-side.

DO NOT implement here — Plan 04 owns these.
"""

from __future__ import annotations

import pytest

_OWNER = "Wave 0 stub — implemented in Plan 04 (telegram_auth slice)"


@pytest.mark.skip(reason=_OWNER)
async def test_non_admin_403() -> None:
    """AUTH-05: a caller whose telegram_id is not in ADMIN_TELEGRAM_IDS gets 403."""
    raise NotImplementedError("Plan 04 implements require_admin 403 path")


@pytest.mark.skip(reason=_OWNER)
async def test_admin_200() -> None:
    """AUTH-05: an allowlisted telegram_id reaches the admin probe (200)."""
    raise NotImplementedError("Plan 04 implements require_admin 200 path")
