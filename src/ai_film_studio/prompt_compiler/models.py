"""Prompt compiler data contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PromptCompilationRequest(BaseModel):
    """Input contract for prompt compilation."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1)
    template_name: str = Field(min_length=1)
    scene_id: str | None = Field(default=None, min_length=1)
    target_engine: str | None = Field(default=None, min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptCompilationResult(BaseModel):
    """Output contract for prompt compilation."""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    target_engine: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

