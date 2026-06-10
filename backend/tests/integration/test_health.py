"""Integration test for the health probe (INFRA-04).

PASSES when the test Postgres + Redis are reachable (``docker compose up``). Skips
cleanly otherwise (the ``redis_client`` / ``db_session`` fixtures gate on reachability),
so the suite stays green in environments without the stack running.

Covers VALIDATION.md node ID: ``test_healthz_ok`` (healthz).
"""

from __future__ import annotations


async def test_healthz_ok(client, db_session, redis_client) -> None:
    """``GET /healthz`` returns 200 with db=ok and redis=ok when deps are reachable."""
    response = await client.get("/healthz")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["db"] == "ok"
    assert body["redis"] == "ok"
