"""Integration — admin prompt-template versioning (ADMIN-05), the generation safety valve.

Exercises ``/api/admin/prompts``: list / publish (create+activate) / activate (rollback), the
allowlist guard, the 404/409 edges, and the partial-unique "one active per slug" invariant that
``PromptEngine._active_template`` relies on. DB-backed; skips when Postgres is unreachable.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models import PromptTemplate
from app.models.enums import PromptTemplateType
from app.services.prompt_engine import PromptEngine
from tests.conftest import TEST_BOT_TOKEN, make_init_data

_ADMIN_USER = {"id": 700500111, "first_name": "Хранитель", "username": "prompt_admin"}
_NORMAL_USER = {"id": 700500222, "first_name": "Гость", "username": "prompt_guest"}


async def _auth(client, user: dict) -> str:
    init_data = make_init_data(TEST_BOT_TOKEN, user=user)
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _system_active_version(session) -> str:
    row = await PromptEngine._active_template(session, "system")
    return row.version


async def test_non_admin_403(auth_client, seeded_catalog, monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-allowlisted telegram_id is refused on every prompt-admin route (valid bodies → 403, not 422)."""
    monkeypatch.setattr(settings, "ADMIN_TELEGRAM_IDS", [_ADMIN_USER["id"]])
    token = await _auth(auth_client, _NORMAL_USER)

    get_resp = await auth_client.get("/api/admin/prompts", headers=_headers(token))
    pub_resp = await auth_client.post(
        "/api/admin/prompts/system/versions",
        headers=_headers(token),
        json={"version": "x", "template_text": "y"},
    )
    act_resp = await auth_client.post(
        "/api/admin/prompts/system/activate",
        headers=_headers(token),
        json={"version": "x"},
    )
    assert get_resp.status_code == 403
    assert pub_resp.status_code == 403
    assert act_resp.status_code == 403


async def test_list_grouped_one_active(
    auth_client, seeded_catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The admin list groups versions by slug; the seeded 'system' template has exactly one active."""
    monkeypatch.setattr(settings, "ADMIN_TELEGRAM_IDS", [_ADMIN_USER["id"]])
    token = await _auth(auth_client, _ADMIN_USER)

    resp = await auth_client.get("/api/admin/prompts", headers=_headers(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    system = next(g for g in body if g["slug"] == "system")
    assert system["type"] == "system"
    assert sum(1 for v in system["versions"] if v["is_active"]) == 1


async def test_publish_creates_and_activates(
    auth_client, seeded_catalog, auth_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Publishing a new version activates it; the engine now resolves it, the old one is inactive."""
    monkeypatch.setattr(settings, "ADMIN_TELEGRAM_IDS", [_ADMIN_USER["id"]])
    token = await _auth(auth_client, _ADMIN_USER)
    base_version = await _system_active_version(auth_session)

    resp = await auth_client.post(
        "/api/admin/prompts/system/versions",
        headers=_headers(token),
        json={"version": "adm-v2", "template_text": "Обновлённый системный блок.", "title": "System v2"},
    )
    assert resp.status_code == 201, resp.text
    versions = {v["version"]: v["is_active"] for v in resp.json()["versions"]}
    assert versions["adm-v2"] is True
    assert versions[base_version] is False
    # The engine's hot path now composes from the new active version.
    assert await _system_active_version(auth_session) == "adm-v2"


async def test_activate_rollback(
    auth_client, seeded_catalog, auth_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After publishing a new version, activating the previous one rolls back — one active again."""
    monkeypatch.setattr(settings, "ADMIN_TELEGRAM_IDS", [_ADMIN_USER["id"]])
    token = await _auth(auth_client, _ADMIN_USER)
    base_version = await _system_active_version(auth_session)

    await auth_client.post(
        "/api/admin/prompts/system/versions",
        headers=_headers(token),
        json={"version": "adm-v2", "template_text": "Новый текст."},
    )
    assert await _system_active_version(auth_session) == "adm-v2"

    resp = await auth_client.post(
        "/api/admin/prompts/system/activate",
        headers=_headers(token),
        json={"version": base_version},
    )
    assert resp.status_code == 200, resp.text
    active = [v["version"] for v in resp.json()["versions"] if v["is_active"]]
    assert active == [base_version]
    assert await _system_active_version(auth_session) == base_version


async def test_publish_duplicate_409(
    auth_client, seeded_catalog, auth_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Publishing a (slug, version) that already exists is a 409 — the seeded version is untouched."""
    monkeypatch.setattr(settings, "ADMIN_TELEGRAM_IDS", [_ADMIN_USER["id"]])
    token = await _auth(auth_client, _ADMIN_USER)
    base_version = await _system_active_version(auth_session)

    resp = await auth_client.post(
        "/api/admin/prompts/system/versions",
        headers=_headers(token),
        json={"version": base_version, "template_text": "duplicate"},
    )
    assert resp.status_code == 409
    assert await _system_active_version(auth_session) == base_version


async def test_activate_unknown_404_leaves_active(
    auth_client, seeded_catalog, auth_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Activating a version that doesn't exist is 404 and the currently-active version is unchanged."""
    monkeypatch.setattr(settings, "ADMIN_TELEGRAM_IDS", [_ADMIN_USER["id"]])
    token = await _auth(auth_client, _ADMIN_USER)
    base_version = await _system_active_version(auth_session)

    resp = await auth_client.post(
        "/api/admin/prompts/system/activate",
        headers=_headers(token),
        json={"version": "does-not-exist"},
    )
    assert resp.status_code == 404
    assert await _system_active_version(auth_session) == base_version


async def test_publish_unknown_slug_404(
    auth_client, seeded_catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Publishing under a slug with no existing rows is 404 (new template types belong in the seed)."""
    monkeypatch.setattr(settings, "ADMIN_TELEGRAM_IDS", [_ADMIN_USER["id"]])
    token = await _auth(auth_client, _ADMIN_USER)

    resp = await auth_client.post(
        "/api/admin/prompts/no_such_slug/versions",
        headers=_headers(token),
        json={"version": "v1", "template_text": "x"},
    )
    assert resp.status_code == 404


async def test_partial_unique_blocks_two_active(auth_session) -> None:
    """The partial-unique index forbids two active rows for one slug (the invariant the engine relies on)."""
    auth_session.add(
        PromptTemplate(
            slug="__guard__", version="a", title="t", type=PromptTemplateType.SYSTEM,
            template_text="x", is_active=True,
        )
    )
    auth_session.add(
        PromptTemplate(
            slug="__guard__", version="b", title="t", type=PromptTemplateType.SYSTEM,
            template_text="y", is_active=True,
        )
    )
    with pytest.raises(IntegrityError):
        await auth_session.flush()
