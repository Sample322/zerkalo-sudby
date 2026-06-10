"""Integration — server-side admin allowlist guard (AUTH-05).

``GET /api/admin/ping`` behind ``require_admin``: a non-allowlisted ``telegram_id`` -> 403,
an allowlisted one -> 200. The allowlist is asserted by overriding
``settings.ADMIN_TELEGRAM_IDS`` so the test does not depend on the ambient env config.

DB-backed (resolves the user from the JWT subject); skips when Postgres is unreachable.
"""

from __future__ import annotations

import pytest

from app.core.config import settings
from tests.conftest import TEST_BOT_TOKEN, make_init_data

_ADMIN_USER = {"id": 700400111, "first_name": "Хранитель", "username": "admin_probe"}
_NORMAL_USER = {"id": 700400222, "first_name": "Гость", "username": "guest_probe"}


async def _auth(client, user: dict) -> str:
    init_data = make_init_data(TEST_BOT_TOKEN, user=user)
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def test_non_admin_403(auth_client, monkeypatch: pytest.MonkeyPatch) -> None:
    """AUTH-05: a telegram_id NOT in ADMIN_TELEGRAM_IDS gets 403 from the probe."""
    # Allowlist contains only the admin id; the normal user is excluded.
    monkeypatch.setattr(settings, "ADMIN_TELEGRAM_IDS", [_ADMIN_USER["id"]])
    token = await _auth(auth_client, _NORMAL_USER)

    resp = await auth_client.get(
        "/api/admin/ping", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "admin only"


async def test_admin_200(auth_client, monkeypatch: pytest.MonkeyPatch) -> None:
    """AUTH-05: an allowlisted telegram_id reaches the probe (200 {"ok": true})."""
    monkeypatch.setattr(settings, "ADMIN_TELEGRAM_IDS", [_ADMIN_USER["id"]])
    token = await _auth(auth_client, _ADMIN_USER)

    resp = await auth_client.get(
        "/api/admin/ping", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}


async def test_admin_requires_auth(auth_client) -> None:
    """AUTH-05: the admin probe is not reachable without a Bearer at all."""
    resp = await auth_client.get("/api/admin/ping")
    assert resp.status_code in (401, 403)
