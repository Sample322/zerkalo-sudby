"""RED stubs — JWT bearer on a protected route (AUTH-04).

Wave-0 placeholders for VALIDATION.md node IDs. Plan 04 removes the skip and implements
``GET /api/me``: a valid Bearer -> 200; a missing / malformed / expired Bearer -> 401.

DO NOT implement here — Plan 04 owns these.
"""

from __future__ import annotations

import pytest

_OWNER = "Wave 0 stub — implemented in Plan 04 (telegram_auth slice)"


@pytest.mark.skip(reason=_OWNER)
async def test_me_accepts_valid_bearer() -> None:
    """AUTH-04: a valid JWT Bearer returns 200 with the current user."""
    raise NotImplementedError("Plan 04 implements GET /api/me bearer accept")


@pytest.mark.skip(reason=_OWNER)
async def test_me_rejects_missing_or_invalid_bearer() -> None:
    """AUTH-04: a missing / invalid / expired Bearer returns 401."""
    raise NotImplementedError("Plan 04 implements GET /api/me bearer reject")
