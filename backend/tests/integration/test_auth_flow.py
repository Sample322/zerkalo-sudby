"""RED stubs — auth flow end-to-end (AUTH-01/02/03/04).

Wave-0 placeholders for VALIDATION.md node IDs. Plan 04 removes the skip and implements
``POST /api/auth/telegram`` against ``make_init_data`` (valid initData -> 200 + JWT +
``users`` row upserted; ``telegram_id`` derived ONLY from validated data).

DO NOT implement here — Plan 04 owns these.
"""

from __future__ import annotations

import pytest

_OWNER = "Wave 0 stub — implemented in Plan 04 (telegram_auth slice)"


@pytest.mark.skip(reason=_OWNER)
async def test_valid_initdata_issues_jwt_and_upserts() -> None:
    """AUTH-01/02/03/04: valid initData -> 200, JWT present, user row upserted."""
    raise NotImplementedError("Plan 04 implements the auth happy path + upsert")


@pytest.mark.skip(reason=_OWNER)
async def test_repeat_auth_updates_last_seen() -> None:
    """AUTH-03: second valid auth updates ``last_seen_at`` and does not duplicate the user."""
    raise NotImplementedError("Plan 04 implements repeat-auth last_seen update")
