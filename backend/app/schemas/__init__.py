"""Pydantic v2 request/response schemas (the API contract surface).

ORM models map to these via ``model_config = ConfigDict(from_attributes=True)`` — never
return ORM objects directly so internal columns can't leak into responses.
"""

from __future__ import annotations

from app.schemas.reading import (
    CardInterpretation,
    ClassifyCallMeta,
    ClassifyResult,
    ReadingCardOut,
    ReadingCreate,
    ReadingOut,
    ReadingOutput,
    ReadingSummary,
    ReadingSummaryOut,
    SafetyCategory,
    SafetyVerdict,
)

__all__ = [
    "CardInterpretation",
    "ReadingSummary",
    "ReadingOutput",
    "SafetyCategory",
    "SafetyVerdict",
    "ClassifyCallMeta",
    "ClassifyResult",
    "ReadingCreate",
    "ReadingCardOut",
    "ReadingSummaryOut",
    "ReadingOut",
]
