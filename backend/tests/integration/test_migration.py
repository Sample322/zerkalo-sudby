"""RED stub — full-schema migration (INFRA-02).

Wave-0 placeholder for the VALIDATION.md node ID. Plan 02 removes the skip and asserts
``alembic upgrade head`` creates all 16 tables (+ key uniques) via ``information_schema``,
and that ``alembic downgrade base`` is clean.

DO NOT implement here — Plan 02 owns this.
"""

from __future__ import annotations

import pytest

_OWNER = "Wave 0 stub — implemented in Plan 02 (schema migration)"


@pytest.mark.skip(reason=_OWNER)
async def test_full_schema_applies() -> None:
    """INFRA-02: upgrade head creates all 16 tables with the required uniques."""
    raise NotImplementedError("Plan 02 implements the full-schema migration assertion")
