"""Integration — JWT Bearer on the protected ``GET /api/me`` route (AUTH-04).

A valid Bearer (issued by ``POST /api/auth/telegram``) -> 200 with the profile; a missing,
malformed, or expired Bearer -> 401. DB-backed (resolves the user); skips when Postgres is
unreachable.
"""

from __future__ import annotations

from app.core.security import encode_jwt
from tests.conftest import TEST_BOT_TOKEN, make_init_data

_TG_USER = {
    "id": 700400002,
    "first_name": "Луна",
    "username": "seeker_me",
    "language_code": "ru",
}


async def _auth_and_get_token(client) -> tuple[str, dict]:
    """Authenticate the sample user and return ``(bearer_token, user_dict)``."""
    init_data = make_init_data(TEST_BOT_TOKEN, user=_TG_USER)
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return body["access_token"], body["user"]


async def test_me_accepts_valid_bearer(auth_client) -> None:
    """AUTH-04: a valid JWT Bearer returns 200 with the current user's profile."""
    token, user = await _auth_and_get_token(auth_client)

    resp = await auth_client.get(
        "/api/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["telegram_id"] == _TG_USER["id"]
    assert body["user"]["id"] == user["id"]
    assert "limits" in body
    assert "settings" in body


async def test_me_rejects_missing_bearer(auth_client) -> None:
    """AUTH-04: no Authorization header -> 401/403 (rejected, never the profile)."""
    resp = await auth_client.get("/api/me")
    # HTTPBearer(auto_error=True) returns 403 for a wholly missing header; either way the
    # protected resource is NOT served.
    assert resp.status_code in (401, 403)


async def test_me_rejects_invalid_bearer(auth_client) -> None:
    """AUTH-04: a malformed/garbage Bearer token -> 401."""
    resp = await auth_client.get(
        "/api/me", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert resp.status_code == 401


async def test_me_rejects_expired_bearer(auth_client) -> None:
    """AUTH-04: an expired (but otherwise valid) Bearer -> 401."""
    token, user = await _auth_and_get_token(auth_client)
    # Mint an already-expired token for the same subject.
    expired = encode_jwt(
        sub=user["id"], telegram_id=_TG_USER["id"], expires_in=-10
    )

    resp = await auth_client.get(
        "/api/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert resp.status_code == 401
