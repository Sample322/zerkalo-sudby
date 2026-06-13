"""READ-01 — ``POST /api/readings`` auth + request-body validation.

Wave-0 stub — implemented in Plan 04-05 (readings router). The body will assert:
  * ``POST /api/readings`` without a Bearer JWT → 401 (mirrors the other protected routes);
  * a malformed body (missing deck_slug/spread_slug, or a 9-char question) → 422 (HOME-01);
  * an empty question is accepted (HOME-02 → general reading).

Imports the request contract (``ReadingCreate``) to stay collect-clean and pin the body shape.
"""

from __future__ import annotations

import pytest

from app.schemas.reading import ReadingCreate  # noqa: F401 — pins the request contract


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (readings router)")
async def test_post_readings_requires_bearer(auth_client: object) -> None:
    """READ-01: no Authorization header → 401."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (readings router)")
async def test_post_readings_validates_body(auth_client: object) -> None:
    """READ-01/HOME-01: malformed body (e.g. too-short question) → 422."""
    raise NotImplementedError
