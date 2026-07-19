"""Module loader models."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ModuleSpec(BaseModel):
    """Import specification for a framework module or object."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    import_path: str = Field(min_length=1)
    attribute: str | None = Field(default=None, min_length=1)


class LoadedDataModule(BaseModel):
    """Reusable YAML or Markdown module loaded from disk."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path
    kind: Literal["yaml", "markdown"]
    data: dict[str, Any] | str
