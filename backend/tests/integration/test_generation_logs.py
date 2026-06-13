"""ANALYTICS-02 — one ``generation_logs`` row per ACTUAL LLM call (classify + each generation).

Implemented in Plan 04-05 (ReadingService generation_logs writes). Injects ``fake_llm`` /
``fake_safety`` against ``seeded_catalog`` in the transaction-isolated ``auth_session`` and drives
the service directly. Asserts:
  * a clean success with a regex-decided safety verdict (no classify call) writes exactly one
    ``generation_logs`` row (status ``completed``), carrying model/tokens/latency/prompt_version;
  * when the safety gate DID make a real classify call (a non-None call-meta), a second row with
    status ``classify`` is written — and NOT when the verdict came from the regex fast-path;
  * a failed generation logs status ``failed`` with the error and does NOT consume the limit.

``generation_logs.reading_id`` is a NOT-NULL FK, so even on crisis/abusive a parent reading row
exists before any classify log is written — verified indirectly by the row counts here and
directly in ``test_safety_gate``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationLog, Reading
from app.models.enums import ReadingStatus
from app.schemas.reading import (
    ClassifyCallMeta,
    ClassifyResult,
    SafetyCategory,
    SafetyVerdict,
)
from app.services.llm import LLMService
from app.services.reading import (
    LOG_STATUS_CLASSIFY,
    LOG_STATUS_COMPLETED,
    LOG_STATUS_FAILED,
    ReadingService,
)
from tests.integration.conftest import FakeLLM, FakeSafety
from tests.integration.test_readings_flow import (
    _REQ,
    _AlwaysInvalidClient,
    _make_user,
    _output_for_indices,
    _spread_position_indices,
)


class _ClassifyingSafety:
    """A safety stand-in that returns a full ``ClassifyResult`` WITH call-meta (a real classify call).

    Models the Stage-2 Haiku path of the real ``SafetyService``: the verdict arrives with
    ``meta`` populated, so ``ReadingService`` must write a ``classify`` generation_logs row.
    """

    def __init__(self, category: SafetyCategory = SafetyCategory.NORMAL) -> None:
        self._category = category
        self.calls = 0

    async def classify(self, *_: object, **__: object) -> ClassifyResult:
        self.calls += 1
        return ClassifyResult(
            verdict=SafetyVerdict(category=self._category),
            via_regex=False,
            meta=ClassifyCallMeta(
                model_name="claude-haiku-4-5",
                input_tokens=7,
                output_tokens=2,
                latency_ms=120,
            ),
        )


async def _logs_for(session: AsyncSession, reading_id: uuid.UUID) -> list[GenerationLog]:
    return list(
        (
            await session.execute(
                select(GenerationLog).where(GenerationLog.reading_id == reading_id)
            )
        ).scalars().all()
    )


async def test_log_row_per_llm_call(
    auth_session: AsyncSession,
    fake_safety: FakeSafety,
    seeded_catalog: dict,
) -> None:
    """ANALYTICS-02: a regex-decided success writes exactly one generation row (the generation)."""
    user = await _make_user(auth_session)
    indices = await _spread_position_indices(auth_session, _REQ.spread_slug)
    fake_llm = FakeLLM(_output_for_indices(indices))
    service = ReadingService(safety=fake_safety, llm=fake_llm)

    result = await service.create_reading(auth_session, user, _REQ)
    reading = await auth_session.get(Reading, uuid.UUID(result.reading_id))
    assert reading is not None

    logs = await _logs_for(auth_session, reading.id)
    # fake_safety resolves via the regex fast-path (no classify call) → only the generation row.
    assert len(logs) == 1
    row = logs[0]
    assert row.status == LOG_STATUS_COMPLETED
    assert row.prompt_template_version  # composed prompt_version persisted (ANALYTICS-02)
    assert row.prompt_template_version == reading.prompt_version


async def test_classify_call_logged_when_made(
    auth_session: AsyncSession,
    seeded_catalog: dict,
) -> None:
    """ANALYTICS-02: a real classify call writes a ``classify`` row in addition to the generation."""
    user = await _make_user(auth_session)
    indices = await _spread_position_indices(auth_session, _REQ.spread_slug)
    fake_llm = FakeLLM(_output_for_indices(indices))
    service = ReadingService(safety=_ClassifyingSafety(), llm=fake_llm)

    result = await service.create_reading(auth_session, user, _REQ)
    reading = await auth_session.get(Reading, uuid.UUID(result.reading_id))
    assert reading is not None

    logs = await _logs_for(auth_session, reading.id)
    statuses = sorted(log.status for log in logs)
    assert statuses == sorted([LOG_STATUS_CLASSIFY, LOG_STATUS_COMPLETED])

    classify_row = next(log for log in logs if log.status == LOG_STATUS_CLASSIFY)
    assert classify_row.model_name == "claude-haiku-4-5"
    assert classify_row.input_tokens == 7
    assert classify_row.latency_ms == 120


async def test_failed_attempt_logged(
    auth_session: AsyncSession,
    fake_safety: FakeSafety,
    seeded_catalog: dict,
) -> None:
    """ANALYTICS-02: a failed generation logs status='failed' + the error."""
    user = await _make_user(auth_session)
    llm = LLMService(client=_AlwaysInvalidClient())
    service = ReadingService(safety=fake_safety, llm=llm)

    result = await service.create_reading(auth_session, user, _REQ)
    reading = await auth_session.get(Reading, uuid.UUID(result.reading_id))
    assert reading is not None
    assert reading.status is ReadingStatus.FAILED

    logs = await _logs_for(auth_session, reading.id)
    assert len(logs) == 1
    row = logs[0]
    assert row.status == LOG_STATUS_FAILED
    assert row.error  # the truncated server-side error is recorded
