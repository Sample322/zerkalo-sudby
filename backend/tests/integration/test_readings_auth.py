"""READ-01 — ``POST /api/readings`` auth + request-body validation + thin-router wiring.

Implemented in Plan 04-05 (readings router). Exercises the real HTTP seam via the in-process
``auth_client`` (httpx ASGITransport — no live server) and a real Bearer issued by
``POST /api/auth/telegram`` (mirrors ``test_me.py``). The ``ReadingService`` is injected with
``FakeSafety`` / ``FakeLLM`` via ``app.dependency_overrides[get_reading_service]`` so the 200 path
never reaches Anthropic. Asserts:
  * no Authorization header → 401/403 (the Bearer gate — never serves the resource);
  * a valid Bearer + malformed body (a non-empty < 10-char question; or a missing slug) → 422;
  * a valid Bearer + valid body → 200 with a ``ReadingOut`` (completed, per-card + summary);
  * the authenticated user comes from the JWT, never the body — a body-supplied ``user_id`` is
    ignored (T-04-23 / V4) and the reading is still created for the JWT user.

Skips cleanly when Postgres is unreachable (via ``seeded_catalog`` → ``auth_session`` →
``_db_ready``), mirroring the rest of the integration suite.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.readings import get_reading_service
from app.main import app
from app.services.reading import ReadingService
from tests.conftest import TEST_BOT_TOKEN, make_init_data
from tests.integration.conftest import FakeLLM, FakeSafety
from tests.integration.test_readings_flow import (
    _output_for_indices,
    _spread_position_indices,
)

_TG_USER = {
    "id": 770500003,
    "first_name": "Вопрошающий",
    "username": "seeker_readings",
    "language_code": "ru",
}

_VALID_BODY = {
    "question": "Что мне поможет принять важное решение на этой неделе?",
    "topic": "choice",
    "deck_slug": "classic_arcana",
    "spread_slug": "three_keys",
}


async def _bearer(client) -> str:
    """Authenticate the sample Telegram user and return the issued Bearer token."""
    init_data = make_init_data(TEST_BOT_TOKEN, user=_TG_USER)
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
async def fake_service(
    auth_session: AsyncSession, seeded_catalog: dict
) -> AsyncIterator[ReadingService]:
    """Override ``get_reading_service`` with a fakes-backed service (matched to the seeded spread)."""
    indices = await _spread_position_indices(auth_session, _VALID_BODY["spread_slug"])
    service = ReadingService(
        safety=FakeSafety(),
        llm=FakeLLM(_output_for_indices(indices)),
    )
    app.dependency_overrides[get_reading_service] = lambda: service
    try:
        yield service
    finally:
        app.dependency_overrides.pop(get_reading_service, None)


async def test_post_readings_requires_bearer(
    auth_client, seeded_catalog: dict
) -> None:
    """READ-01: no Authorization header → 401/403 (the resource is never served)."""
    resp = await auth_client.post("/api/readings", json=_VALID_BODY)
    # HTTPBearer(auto_error=True) returns 403 for a wholly missing header; either way: rejected.
    assert resp.status_code in (401, 403)


async def test_post_readings_validates_body(
    auth_client, seeded_catalog: dict
) -> None:
    """READ-01/HOME-01: a valid Bearer but a malformed body (too-short question) → 422."""
    token = await _bearer(auth_client)
    bad = {**_VALID_BODY, "question": "коротко"}  # non-empty, < 10 chars → invalid (HOME-01)
    resp = await auth_client.post(
        "/api/readings", json=bad, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 422, resp.text


async def test_post_readings_missing_slug_is_422(
    auth_client, seeded_catalog: dict
) -> None:
    """READ-01: a missing required ``deck_slug`` → 422 (body validation before the service)."""
    token = await _bearer(auth_client)
    bad = {k: v for k, v in _VALID_BODY.items() if k != "deck_slug"}
    resp = await auth_client.post(
        "/api/readings", json=bad, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 422, resp.text


async def test_post_readings_valid_request_returns_reading(
    auth_client, fake_service: ReadingService
) -> None:
    """READ-01: a valid Bearer + valid body → 200 with a ReadingOut (fakes wired, no Anthropic)."""
    token = await _bearer(auth_client)
    resp = await auth_client.post(
        "/api/readings", json=_VALID_BODY, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["reading_id"]
    assert len(body["cards"]) == 3
    assert body["summary"] is not None
    assert body["remaining_limits"] == 2  # 3 free − 1 consumed


async def test_post_readings_user_from_jwt_not_body(
    auth_client, fake_service: ReadingService
) -> None:
    """T-04-23/V4: a body-supplied ``user_id`` is ignored; the reading is for the JWT user."""
    token = await _bearer(auth_client)
    # A forged user_id in the body must have NO effect — it is not even a ReadingCreate field.
    forged = {**_VALID_BODY, "user_id": "00000000-0000-0000-0000-000000000000"}
    resp = await auth_client.post(
        "/api/readings", json=forged, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    # The reading was created (for the JWT user) and the forged id changed nothing.
    assert body["reading_id"]
