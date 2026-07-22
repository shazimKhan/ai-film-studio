"""Prompt compiler data contracts."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from ai_film_studio.asset_bible import IdentityProfile


class PromptModel(BaseModel):
    """Base model configuration for prompt compiler contracts."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class CharacterReference(PromptModel):
    """Scene-level reference to a reusable character asset."""

    id: str = Field(min_length=1)
    module: Path
    role: str | None = Field(default=None, min_length=1)
    wardrobe: str | None = Field(default=None, min_length=1)
    hair: str | None = Field(default=None, min_length=1)
    notes: tuple[str, ...] = ()


class WorldReference(PromptModel):
    """Scene-level reference to a reusable world asset."""

    id: str = Field(min_length=1)
    module: Path


class CameraConfig(PromptModel):
    """Camera language for a clip."""

    shot_size: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    lens: str = Field(min_length=1)
    movement: str = Field(min_length=1)
    framing: str = Field(min_length=1)
    focus: str = Field(min_length=1)


class LightingConfig(PromptModel):
    """Lighting language for a clip."""

    quality: str = Field(min_length=1)
    source: str = Field(min_length=1)
    color_temperature: str = Field(min_length=1)
    contrast: str = Field(min_length=1)
    mood: str = Field(min_length=1)


class MotionConfig(PromptModel):
    """Motion language for a clip."""

    subject: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    camera: str = Field(min_length=1)
    pace: str = Field(min_length=1)


class ContinuityConfig(PromptModel):
    """Continuity rules for a clip."""

    previous_clip: str = Field(min_length=1)
    visual_state: str = Field(min_length=1)
    prop_state: str = Field(min_length=1)
    emotional_state: str = Field(min_length=1)


class SceneBlueprint(PromptModel):
    """Validated scene blueprint loaded from YAML."""

    project: str = Field(min_length=1)
    episode: str = Field(min_length=1)
    scene: str = Field(min_length=1)
    clip: str = Field(min_length=1)
    title: str = Field(min_length=1)
    duration: float = Field(gt=0, description="Duration in seconds.")
    action: str = Field(min_length=1)
    emotion: str = Field(min_length=1)
    characters: tuple[CharacterReference, ...] = Field(min_length=1)
    world: WorldReference
    camera: CameraConfig
    lighting: LightingConfig
    motion: MotionConfig
    continuity: ContinuityConfig
    negative_prompts: tuple[str, ...] = Field(
        min_length=1,
        validation_alias=AliasChoices("negative_prompts", "negative prompts"),
        serialization_alias="negative prompts",
    )
    audio: str | None = Field(default=None, min_length=1)

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, value: float) -> float:
        """Reject non-finite durations even if a YAML parser accepts them."""
        if not math.isfinite(value):
            msg = "Duration must be a finite number of seconds."
            raise ValueError(msg)
        return value


class CharacterAsset(PromptModel):
    """Reusable character identity asset."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    id: str = Field(min_length=1, validation_alias=AliasChoices("id", "asset_id"))
    name: str = Field(min_length=1)
    age: str = Field(min_length=1)
    appearance: str = Field(min_length=1)
    wardrobe: str = Field(min_length=1)
    hair: str = Field(min_length=1)
    personality: str = Field(min_length=1)
    performance_constraints: tuple[str, ...] = ()
    status: str | None = Field(default=None, min_length=1)
    identity_id: str | None = Field(default=None, min_length=1)
    identity_locked: bool = False
    lock_level: str | None = Field(default=None, min_length=1)
    canonical_reference: dict[str, Any] | None = None
    immutable_attributes: tuple[str, ...] = ()
    mutable_attributes: tuple[str, ...] = ()
    continuity_prompt: str | None = Field(default=None, min_length=1)
    negative_continuity_prompt: str | None = Field(default=None, min_length=1)


class WorldAsset(PromptModel):
    """Reusable world and period asset."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    period: str = Field(min_length=1)
    location: str = Field(min_length=1)
    description: str = Field(min_length=1)
    visual_rules: tuple[str, ...] = Field(min_length=1)
    textures: tuple[str, ...] = Field(min_length=1)
    atmosphere: str = Field(min_length=1)
    soundscape: str = Field(min_length=1)


class ResolvedCharacterReference(PromptModel):
    """Scene character reference with loaded reusable asset data."""

    reference: CharacterReference
    asset: CharacterAsset
    identity: IdentityProfile | None = None


class ResolvedWorldReference(PromptModel):
    """Scene world reference with loaded reusable asset data."""

    reference: WorldReference
    asset: WorldAsset


class ResolvedSceneContext(PromptModel):
    """Scene blueprint plus resolved reusable modules."""

    scene: SceneBlueprint
    characters: tuple[ResolvedCharacterReference, ...] = Field(min_length=1)
    world: ResolvedWorldReference


class PromptSection(PromptModel):
    """A named prompt section in production order."""

    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class PromptCompilationRequest(PromptModel):
    """Input contract for prompt compilation."""

    scene_context: ResolvedSceneContext
    target_engine: str | None = Field(default=None, min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptCompilationResult(PromptModel):
    """Output contract for prompt compilation."""

    scene: SceneBlueprint
    sections: tuple[PromptSection, ...] = Field(min_length=1)
    prompt: str
    target_engine: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
