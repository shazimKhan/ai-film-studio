"""Engine-neutral request and result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EngineArtifact(BaseModel):
    """Artifact produced by an engine adapter."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EngineRequest(BaseModel):
    """Engine-neutral request payload."""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EngineReferenceCapabilities(BaseModel):
    """Reference image support advertised by an engine adapter."""

    model_config = ConfigDict(extra="forbid")

    max_character_reference_images: int = Field(default=1, gt=0)
    supports_multiple_references: bool = False
    supports_reference_manifest: bool = False
    preferred_reference_types: tuple[str, ...] = ()


class EngineResult(BaseModel):
    """Engine-neutral result payload."""

    model_config = ConfigDict(extra="forbid")

    external_id: str | None = None
    artifacts: tuple[EngineArtifact, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)
