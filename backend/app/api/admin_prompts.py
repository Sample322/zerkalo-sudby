"""Admin prompt-template versioning (ADMIN-05) — the production safety valve for generation.

Behind ``require_admin`` (server-side ``ADMIN_TELEGRAM_IDS`` allowlist). Lets an operator LIST
versions, PUBLISH a new version (create + activate atomically), and ACTIVATE / ROLL BACK an existing
version — all live, no redeploy. ``PromptEngine._active_template`` reads only the active row per
slug; the partial-unique index ``uq_prompt_active_per_slug`` guarantees exactly one active per slug,
so activation is a deactivate-then-activate within a single transaction (deactivate FIRST so there
is never a window with two active rows for the slug).

Templates are DATA — no route emits any "AI/нейросеть/модель" copy (SAFE-06 is a UI concern; the
stored template text is the interpreter's private instruction set, never surfaced verbatim).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_admin
from app.models import PromptTemplate, User
from app.schemas.admin import (
    ActivateVersionIn,
    CreateVersionIn,
    PromptSlugOut,
    PromptVersionOut,
)

router = APIRouter(prefix="/admin/prompts", tags=["admin"])


async def _slug_out(session: AsyncSession, slug: str) -> PromptSlugOut:
    """Re-read one slug's versions (ordered) into the response schema; 404 if the slug is unknown."""
    rows = (
        await session.execute(
            select(PromptTemplate)
            .where(PromptTemplate.slug == slug)
            .order_by(PromptTemplate.version)
        )
    ).scalars().all()
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "prompt slug not found")
    return PromptSlugOut(
        slug=slug,
        type=rows[0].type.value,
        versions=[PromptVersionOut.model_validate(r) for r in rows],
    )


async def _activate(session: AsyncSession, slug: str, version: str) -> None:
    """Make ``(slug, version)`` the single active row for its slug, atomically + committed.

    Existence-checks the target FIRST (so the 404 path mutates nothing), then — in one transaction —
    deactivates every row for the slug and activates the target. Deactivate-first means the
    partial-unique ``uq_prompt_active_per_slug`` index never sees two active rows for the slug.
    """
    target = await session.scalar(
        select(PromptTemplate.id).where(
            PromptTemplate.slug == slug, PromptTemplate.version == version
        )
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "prompt version not found")
    await session.execute(
        update(PromptTemplate).where(PromptTemplate.slug == slug).values(is_active=False)
    )
    await session.execute(
        update(PromptTemplate).where(PromptTemplate.id == target).values(is_active=True)
    )
    await session.commit()


@router.get("", response_model=list[PromptSlugOut])
async def list_prompts(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[PromptSlugOut]:
    """List every template grouped by slug, each with its versions + which one is active."""
    rows = (
        await session.execute(
            select(PromptTemplate).order_by(PromptTemplate.slug, PromptTemplate.version)
        )
    ).scalars().all()
    grouped: dict[str, PromptSlugOut] = {}
    for row in rows:
        group = grouped.get(row.slug)
        if group is None:
            group = PromptSlugOut(slug=row.slug, type=row.type.value, versions=[])
            grouped[row.slug] = group
        group.versions.append(PromptVersionOut.model_validate(row))
    return list(grouped.values())


@router.post("/{slug}/versions", response_model=PromptSlugOut, status_code=status.HTTP_201_CREATED)
async def publish_version(
    slug: str,
    body: CreateVersionIn,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PromptSlugOut:
    """Publish a NEW version of an existing template and activate it (create + activate).

    404 if the slug does not exist yet (a brand-new template type belongs in the seed, not the
    live valve). 409 if ``(slug, version)`` already exists. The new row's ``type`` is copied from
    the slug's existing rows; ``title`` defaults to the current one when omitted.
    """
    existing = (
        await session.execute(
            select(PromptTemplate).where(PromptTemplate.slug == slug)
        )
    ).scalars().all()
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "prompt slug not found")
    if any(row.version == body.version for row in existing):
        raise HTTPException(status.HTTP_409_CONFLICT, "version already exists")

    session.add(
        PromptTemplate(
            slug=slug,
            version=body.version,
            template_text=body.template_text,
            title=body.title or existing[0].title,
            type=existing[0].type,
            is_active=False,
        )
    )
    await session.flush()  # the row must exist before _activate's existence check
    await _activate(session, slug, body.version)  # deactivate-then-activate + commit
    return await _slug_out(session, slug)


@router.post("/{slug}/activate", response_model=PromptSlugOut)
async def activate_version(
    slug: str,
    body: ActivateVersionIn,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PromptSlugOut:
    """Activate (roll back to) an existing version — the safety valve. 404 if that version is unknown."""
    await _activate(session, slug, body.version)
    return await _slug_out(session, slug)


__all__ = ["router"]
