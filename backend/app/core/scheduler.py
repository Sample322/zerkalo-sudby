"""In-process recurring-renewal scheduler (PAY-06, D-08) — the proactive layer over the lazy gate.

ЮKassa does NOT auto-charge: the merchant must trigger each «Лунный доступ» renewal. This module
runs an in-process APScheduler ``AsyncIOScheduler`` daily sweep (broker-FREE — respects the
Celery/RQ/Arq ban, D-08) that finds ACTIVE subscriptions whose window is closing and issues a
merchant-initiated charge via ``PaymentService.renew_subscription`` (Plan 03).

The DB window stays the source of truth and the Plan-04 consume-gate is the correctness FLOOR, so
the sweep is purely PROACTIVE: a missed tick self-heals because each run recomputes "who's due" from
the DB, and the deterministic per-period Idempotence-Key (``renew:<sub_id>:<period_index>``) makes a
same-period double-run a no-op at ЮKassa (T-07-DOUBLE-CHARGE). If the deploy ever scales past one
instance, swap this for a timeweb cron hitting one endpoint (A2 / T-07-MULTI-INSTANCE) — the charge
logic already lives in the service, so only the trigger moves.

The scheduler is started/stopped from the FastAPI ``lifespan`` (``start_scheduler`` /
``shutdown_scheduler``); a start failure must NOT crash boot (logged + swallowed) because the lazy
backbone still enforces entitlement.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.services.payments import PaymentService

logger = logging.getLogger("app.scheduler")

# A daily idempotent sweep self-heals a missed tick, so an in-MEMORY scheduler (NO PG jobstore) is
# correct — we never persist/replay individual jobs. A generous misfire grace lets a tick the loop
# missed (restart / GC pause) still fire once, and ``coalesce`` collapses a backlog into one run.
_SWEEP_INTERVAL_DAYS = 1
_MISFIRE_GRACE_SECONDS = 6 * 60 * 60  # 6h — a delayed daily tick still runs (self-healing)

scheduler = AsyncIOScheduler()


async def _run_sweep(svc: PaymentService, session: AsyncSession) -> dict[str, int]:
    """Charge every due subscription on ``session``, isolating per-subscription failures.

    Asks the service for the due set, then calls ``renew_subscription`` per subscription inside a
    try/except so ONE failed charge never aborts the whole sweep (T-07-SWEEP-ABORT — the lazy gate
    still guards access). ``renew_subscription`` already swallows a charge failure internally
    (→ PAYMENT_FAILED, D-10); this outer guard additionally isolates any unexpected error. Returns a
    ``{due, charged, failed}`` summary (the production job ignores it; tests assert on it).
    """
    charged = 0
    failed = 0
    due = await svc.find_due_subscriptions(session)
    for sub in due:
        try:
            await svc.renew_subscription(session, sub)
            charged += 1
        except Exception:  # noqa: BLE001 - one failed charge must not abort the sweep.
            failed += 1
            logger.warning(
                "subscription_sweep_charge_failed",
                extra={
                    "event": "payment.sweep_charge_failed",
                    "subscription_id": str(sub.id),
                },
            )
    logger.info(
        "subscription_sweep_complete",
        extra={
            "event": "payment.sweep_complete",
            "due": charged + failed,
            "charged": charged,
            "failed": failed,
        },
    )
    return {"due": charged + failed, "charged": charged, "failed": failed}


async def sweep_due_subscriptions(
    *,
    service: PaymentService | None = None,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    """Daily job: renew every ACTIVE subscription due for a charge (PAY-06).

    In production (the APScheduler tick) it takes no args: it builds a ``PaymentService`` and opens
    its OWN ``AsyncSession`` from ``SessionLocal`` (the job runs OUTSIDE a request, so it must not
    borrow a request session). The ``service`` / ``session`` seams exist ONLY so a test can drive the
    sweep with a ``FakeYooKassa``-backed service against the isolated test session (no live charge).
    """
    svc = service or PaymentService()
    if session is not None:
        return await _run_sweep(svc, session)
    async with SessionLocal() as own_session:
        return await _run_sweep(svc, own_session)


def start_scheduler() -> None:
    """Register the daily sweep + start the scheduler (FastAPI lifespan startup).

    Adds the job with a fixed id (``replace_existing=True``) so a re-entrant start never
    double-registers. NEVER raises into boot — a scheduler failure is logged and swallowed (the lazy
    consume-gate remains the correctness floor), matching the "start failure must not crash boot"
    contract.
    """
    try:
        scheduler.add_job(
            sweep_due_subscriptions,
            "interval",
            days=_SWEEP_INTERVAL_DAYS,
            id="sweep_due_subscriptions",
            replace_existing=True,
            misfire_grace_time=_MISFIRE_GRACE_SECONDS,
            coalesce=True,
        )
        if not scheduler.running:
            scheduler.start()
        logger.info("scheduler_started", extra={"event": "scheduler.started"})
    except Exception:  # noqa: BLE001 - a scheduler failure must never crash boot (lazy backbone holds).
        logger.exception(
            "scheduler_start_failed", extra={"event": "scheduler.start_failed"}
        )


def shutdown_scheduler() -> None:
    """Stop the scheduler cleanly (FastAPI lifespan shutdown ``finally``) — best-effort, never raises."""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped", extra={"event": "scheduler.stopped"})
    except Exception:  # noqa: BLE001 - shutdown best-effort; never raise from teardown.
        logger.warning(
            "scheduler_shutdown_failed", extra={"event": "scheduler.shutdown_failed"}
        )


__all__ = [
    "scheduler",
    "sweep_due_subscriptions",
    "start_scheduler",
    "shutdown_scheduler",
]
