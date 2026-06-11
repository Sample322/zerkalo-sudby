"""Integration — deck/spread catalog endpoints (DECK-01..04, SPREAD-01..04).

DB-backed: seeds the MVP catalog into the transaction-isolated session, authenticates a
sample user, then exercises the auth-gated catalog routes. Skips cleanly when Postgres is
unreachable (shared ``_db_ready`` fixture); the no-Bearer rejection assertions document the
auth gate. Mirrors ``test_me.py`` for the Bearer-mint helper.
"""

from __future__ import annotations

import re

from app.seed.loader import run_seed
from tests.conftest import TEST_BOT_TOKEN, make_init_data

_TG_USER = {
    "id": 700400055,
    "first_name": "Вопрошающий",
    "username": "seeker_catalog",
    "language_code": "ru",
}

_BANNED = re.compile(r"ai|нейросет|модель|сгенерирован", re.IGNORECASE)
_FORBIDDEN_KEYS = {
    "meaning_upright",
    "meaning_reversed",
    "advice_upright",
    "advice_reversed",
}


async def _seed_and_auth(auth_client, auth_session) -> dict[str, str]:
    """Seed the catalog into the isolated session + return a Bearer auth header."""
    await run_seed(auth_session)
    await auth_session.flush()
    init_data = make_init_data(TEST_BOT_TOKEN, user=_TG_USER)
    resp = await auth_client.post("/api/auth/telegram", json={"init_data": init_data})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_decks_list(auth_client, auth_session) -> None:
    headers = await _seed_and_auth(auth_client, auth_session)
    resp = await auth_client.get("/api/decks", headers=headers)
    assert resp.status_code == 200, resp.text
    decks = resp.json()
    assert len(decks) == 6  # DECK-01: six MVP decks
    assert [d["sort_order"] for d in decks] == sorted(d["sort_order"] for d in decks)
    for d in decks:
        assert "prompt_modifier" in d  # DECK-02
        assert "visual_style" in d
        assert not (_FORBIDDEN_KEYS & d.keys())  # DECK-04 IP boundary


async def test_deck_detail(auth_client, auth_session) -> None:
    headers = await _seed_and_auth(auth_client, auth_session)
    resp = await auth_client.get("/api/decks/classic_arcana", headers=headers)
    assert resp.status_code == 200, resp.text
    deck = resp.json()
    assert deck["slug"] == "classic_arcana"
    for key in ("tone", "atmosphere", "prompt_modifier", "visual_style"):
        assert key in deck
    assert not (_FORBIDDEN_KEYS & deck.keys())


async def test_deck_not_found(auth_client, auth_session) -> None:
    headers = await _seed_and_auth(auth_client, auth_session)
    resp = await auth_client.get("/api/decks/no_such_deck", headers=headers)
    assert resp.status_code == 404


async def test_spreads_list(auth_client, auth_session) -> None:
    headers = await _seed_and_auth(auth_client, auth_session)
    resp = await auth_client.get("/api/spreads", headers=headers)
    assert resp.status_code == 200, resp.text
    spreads = resp.json()
    assert len(spreads) == 7  # SPREAD-01
    total_positions = sum(len(s["positions"]) for s in spreads)
    assert total_positions == 23  # SPREAD-02 (3+3+3+3+3+4+4)
    for s in spreads:
        assert s["positions"], f"{s['slug']} has no positions"
        for p in s["positions"]:
            assert "prompt_instruction" in p


async def test_spreads_topic_filter(auth_client, auth_session) -> None:
    headers = await _seed_and_auth(auth_client, auth_session)
    resp = await auth_client.get("/api/spreads?topic=love", headers=headers)
    assert resp.status_code == 200, resp.text
    spreads = resp.json()
    assert spreads  # at least one love-tagged spread
    for s in spreads:
        assert "love" in s["recommended_topics"]


async def test_spread_recommend_honors_compat(auth_client, auth_session) -> None:
    headers = await _seed_and_auth(auth_client, auth_session)
    resp = await auth_client.get(
        "/api/spreads/recommend?topic=love&deck_slug=heart_oracle", headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["recommended_spread"]["slug"]
    assert body["reason"]
    assert not _BANNED.search(body["reason"])  # brand voice


async def test_spread_recommend_fallback(auth_client, auth_session) -> None:
    headers = await _seed_and_auth(auth_client, auth_session)
    # A (topic, deck) combo with no direct compat match still resolves to a spread.
    resp = await auth_client.get(
        "/api/spreads/recommend?topic=day&deck_slug=heart_oracle", headers=headers
    )
    assert resp.status_code == 200, resp.text
    slug = resp.json()["recommended_spread"]["slug"]
    assert slug and isinstance(slug, str)


async def test_catalog_requires_auth(auth_client) -> None:
    """No Bearer -> rejected on every catalog route (T-02-01)."""
    for path in ("/api/decks", "/api/spreads", "/api/spreads/recommend?topic=love"):
        resp = await auth_client.get(path)
        assert resp.status_code in (401, 403), path
