"""Schema for the client analytics sink (POST /api/events, ANALYTICS-01)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EventIn(BaseModel):
    """A client-emitted product event. ``user_id`` is NEVER accepted from the body (JWT-scoped)."""

    model_config = ConfigDict(extra="forbid")

    event_name: str = Field(min_length=1, max_length=64)
    properties: dict | None = None


__all__ = ["EventIn"]
