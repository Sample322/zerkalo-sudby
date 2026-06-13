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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.reading import ReadingCreate, ReadingOut
from app.services.reading import ReadingInputError, ReadingService

router = APIRouter(tags=["readings"])


def get_reading_service() -> ReadingService:
    """Provide the default ``ReadingService`` (real collaborators).

    Overridden in tests via ``app.dependency_overrides[get_reading_service]`` to inject a service
    built with ``FakeSafety`` / ``FakeLLM`` so the success path is exercised without a real
    Anthropic call.
    """
    return ReadingService()


@router.post("/readings", response_model=ReadingOut)
async def create_reading(
    body: ReadingCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    service: ReadingService = Depends(get_reading_service),
) -> ReadingOut:
    """Create a reading for the authenticated user (Bearer JWT, validated body).

    Delegates to ``ReadingService.create_reading``; maps an unknown/inactive deck or spread to a
    404. The user comes from the JWT (``get_current_user``), never the body (T-04-23).
    """
    try:
        return await service.create_reading(session, user, body)
    except ReadingInputError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


__all__ = ["router", "get_reading_service"]
