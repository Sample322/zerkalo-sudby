"""``POST /api/readings`` — create a real personalized reading (READ-01, TZ §14.5).

Thin router (mirrors ``decks.py`` / ``spreads.py``): it authenticates via the ``get_current_user``
Bearer gate, validates the body with ``ReadingCreate``, and delegates ALL orchestration to
``ReadingService.create_reading`` (the gate→draw→generate→consume keystone). No business logic
lives here.

Security (Security Domain V4/V5):
  * the authenticated user is derived ONLY from ``get_current_user`` (the JWT ``sub``) — the
    request body is NEVER trusted for identity (T-04-23); a body-supplied ``user_id`` is simply
    not a field on ``ReadingCreate`` and is ignored;
  * the body is validated by Pydantic (question 10–500 or empty per HOME-01/02; deck/spread slugs
    required) → a malformed body is a 422 before the service runs;
  * an unknown / inactive deck or spread surfaces as ``ReadingInputError`` → a clean 404 with no
    internal detail (T-02-03). The no-quota / refusal / redirect / honest-fail responses are
    deliberate 200 soft bodies from the service (a ``status`` field carries the outcome), NOT
    errors — the global handler (``core/errors.py``) stays the last-resort 500 path.

The ``ReadingService`` is provided through the ``get_reading_service`` dependency so tests can
inject one built with the ``FakeSafety`` / ``FakeLLM`` stand-ins (via ``app.dependency_overrides``)
and the 200 path never reaches Anthropic.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, throttle_gate
from app.models.user import User
from app.schemas.reading import ReadingCreate, ReadingListItemOut, ReadingOut
from app.services.reading import ReadingInputError, ReadingService

router = APIRouter(tags=["readings"])


def get_reading_service() -> ReadingService:
    """Provide the default ``ReadingService`` (real collaborators).

    Overridden in tests via ``app.dependency_overrides[get_reading_service]`` to inject a service
    built with ``FakeSafety`` / ``FakeLLM`` so the success path is exercised without a real
    Anthropic call.
    """
    return ReadingService()


@router.post(
    "/readings",
    response_model=ReadingOut,
    dependencies=[Depends(throttle_gate)],
)
async def create_reading(
    body: ReadingCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    service: ReadingService = Depends(get_reading_service),
) -> ReadingOut:
    """Create a reading for the authenticated user (Bearer JWT, validated body).

    GATE 0 is ``throttle_gate`` (in ``dependencies=[...]``): FastAPI resolves it BEFORE the
    path-operation's own ``Depends`` params, so a burst over the cap returns 429 before
    ``get_session`` opens a transaction or the service runs (LIMIT-05, success-criterion 4).
    Delegates to ``ReadingService.create_reading``; maps an unknown/inactive deck or spread to a
    404. The user comes from the JWT (``get_current_user``), never the body (T-04-23).
    """
    try:
        return await service.create_reading(session, user, body)
    except ReadingInputError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/readings", response_model=list[ReadingListItemOut])
async def list_readings(
    limit: int = Query(10, ge=1, le=10),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    service: ReadingService = Depends(get_reading_service),
) -> list[ReadingListItemOut]:
    """List the authenticated user's reading history (HIST-01/02/06) — light, newest-first.

    Thin router: delegates ALL query logic to ``ReadingService.list_readings``. The user is the
    JWT identity (``get_current_user``) — never a body or query ``user_id`` (T-05-01). ``limit`` is
    bounded ``ge=1,le=10`` (the free-tier cap, HIST-06/T-05-05) and ``offset`` ``ge=0`` for D-01
    load-more; the service additionally bounds the effective window by ``FREE_HISTORY_CAP``.

    D-01 seam: the API may later carry optional ``topic`` / ``deck_slug`` filter params, but the
    MVP free list is ≤10 items so they are intentionally NOT surfaced here (no filters in MVP).
    """
    return await service.list_readings(session, user, limit=limit, offset=offset)


# NOTE: the literal ``GET /readings`` list is declared ABOVE these ``/{reading_id}`` routes so
# FastAPI matches the static path first and the parametrized routes never shadow it. The
# ``{reading_id}`` path is typed ``uuid.UUID`` so a malformed (non-UUID) id is a 422 from path
# validation (Security Domain V5) before the service runs.


@router.get("/readings/{reading_id}", response_model=ReadingOut)
async def get_reading(
    reading_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    service: ReadingService = Depends(get_reading_service),
) -> ReadingOut:
    """Return the immutable stored reading by id (HIST-03) — reused, never regenerated.

    Thin router: delegates to ``ReadingService.get_reading_detail`` and maps ``ReadingInputError``
    → 404 exactly like the POST handler. The user is the JWT identity (``get_current_user``), so a
    non-owned OR soft-deleted id is a clean 404 (not 403, not 200 — T-05-IDOR / no existence leak).
    """
    try:
        return await service.get_reading_detail(session, user, reading_id)
    except ReadingInputError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete("/readings/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading(
    reading_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    service: ReadingService = Depends(get_reading_service),
) -> None:
    """Soft-delete the authenticated user's reading (HIST-04) — 204 on success.

    Thin router: delegates to ``ReadingService.soft_delete`` (sets ``deleted_at``, never a hard
    delete) and maps ``ReadingInputError`` → 404. User-scoped via the JWT: a non-owned id is a 404
    and cannot delete another user's reading (T-05-IDOR).
    """
    try:
        await service.soft_delete(session, user, reading_id)
    except ReadingInputError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("/readings/{reading_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_reading(
    reading_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    service: ReadingService = Depends(get_reading_service),
) -> None:
    """Restore a soft-deleted reading (D-03 undo) — 204 on success.

    Thin router: delegates to ``ReadingService.restore`` (nulls ``deleted_at``) and maps
    ``ReadingInputError`` → 404. A dedicated, explicit ``POST .../restore`` (RESEARCH Open
    Question 1) keeps the undo intent clear and never leaks the ``deleted_at`` column over the API.
    User-scoped via the JWT: a non-owned id is a 404 (T-05-IDOR).
    """
    try:
        await service.restore(session, user, reading_id)
    except ReadingInputError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


__all__ = ["router", "get_reading_service"]
