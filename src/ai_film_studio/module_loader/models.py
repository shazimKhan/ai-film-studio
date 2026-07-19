"""Module loader models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModuleSpec(BaseModel):
    """Import specification for a framework module or object."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    import_path: str = Field(min_length=1)
    attribute: str | None = Field(default=None, min_length=1)

