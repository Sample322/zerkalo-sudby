"""Admin API schemas — prompt-template versioning (ADMIN-05, the generation safety valve)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PromptVersionOut(BaseModel):
    """One version row of a logical prompt template."""

    model_config = ConfigDict(from_attributes=True)

    version: str
    title: str
    is_active: bool
    updated_at: datetime


class PromptSlugOut(BaseModel):
    """All versions of one logical template, addressed by ``slug``."""

    slug: str
    type: str
    versions: list[PromptVersionOut]


class CreateVersionIn(BaseModel):
    """Publish a new version of a template — it becomes the active one (create + activate)."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1, max_length=64)
    template_text: str = Field(min_length=1)
    title: str | None = Field(default=None, max_length=200)


class ActivateVersionIn(BaseModel):
    """Activate (roll back to) an existing version of a template."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1, max_length=64)


__all__ = ["PromptVersionOut", "PromptSlugOut", "CreateVersionIn", "ActivateVersionIn"]
