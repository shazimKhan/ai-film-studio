"""Project configuration contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPORTED_ADAPTER_IDS = frozenset(
    {
        "gemini",
        "flow",
        "veo",
        "kling",
        "runway",
        "hailuo",
        "seedance",
    },
)

SOURCE_VALIDATION_STATES = frozenset(
    {
        "unverified",
        "under_review",
        "verified",
        "disputed",
        "rejected",
        "approved_for_narration",
        "approved_for_visual_context",
    },
)

APPROVED_SOURCE_STATES = frozenset(
    {
        "approved_for_narration",
        "approved_for_visual_context",
    },
)


class ProjectConfig(BaseModel):
    """Reusable project-level configuration."""

    model_config = ConfigDict(extra="allow")

    project_id: str = Field(min_length=1)
    project_name: str = Field(min_length=1)
    project_type: str = Field(min_length=1)
    genre: tuple[str, ...] = Field(min_length=1)
    language: str = Field(min_length=1)
    research_required: bool
    source_validation_required: bool
    depiction_policy: str = Field(min_length=1)
    visual_style: dict[str, Any]
    default_shot_duration: int = Field(gt=0)
    prompt_engines: tuple[str, ...] = Field(min_length=1)
    qa_profiles: tuple[str, ...] = Field(min_length=1)
    project_asset_path: str = Field(min_length=1)

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value: str) -> str:
        """Keep project ids path-safe and machine-readable."""
        cleaned = value.strip()
        if not cleaned:
            msg = "Project id cannot be empty."
            raise ValueError(msg)
        if cleaned.lower() != cleaned or " " in cleaned or "-" in cleaned:
            msg = "Project id must use lowercase snake_case."
            raise ValueError(msg)
        return cleaned

    @field_validator("genre", "prompt_engines", "qa_profiles", mode="before")
    @classmethod
    def coerce_string_tuple(cls, value: Any) -> tuple[str, ...]:
        """Normalize YAML lists into tuples of non-empty strings."""
        if isinstance(value, str):
            return (value,)
        if isinstance(value, list | tuple):
            return tuple(str(item).strip() for item in value if str(item).strip())
        msg = "Expected a string or list of strings."
        raise ValueError(msg)


class SourceRecord(BaseModel):
    """Research source record used by source validation."""

    model_config = ConfigDict(extra="allow")

    source_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    validation_state: str = "unverified"
    approved_for_script: bool = False

    @field_validator("validation_state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        """Reject unsupported source validation states."""
        if value not in SOURCE_VALIDATION_STATES:
            msg = f"Unsupported source validation state '{value}'."
            raise ValueError(msg)
        return value

    @property
    def is_approved_for_production(self) -> bool:
        """Return whether the source can unblock research-first production."""
        return self.approved_for_script and self.validation_state in APPROVED_SOURCE_STATES


class SourceRegistry(BaseModel):
    """Source registry for a research-first project."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    project_id: str = Field(min_length=1)
    validation_states: tuple[str, ...] = tuple(SOURCE_VALIDATION_STATES)
    source_records: tuple[SourceRecord, ...] = ()

    @field_validator("validation_states", mode="before")
    @classmethod
    def coerce_states(cls, value: Any) -> tuple[str, ...]:
        """Normalize validation state declarations."""
        if value is None:
            return tuple(SOURCE_VALIDATION_STATES)
        if isinstance(value, list | tuple):
            return tuple(str(item).strip() for item in value if str(item).strip())
        msg = "Expected a list of source validation states."
        raise ValueError(msg)


class ProjectValidationIssue(BaseModel):
    """Single project validation issue."""

    model_config = ConfigDict(extra="forbid")

    code: str
    path: str
    message: str


class ProjectValidationReport(BaseModel):
    """Validation report for one or more project configs."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    project_root: str
    issues: tuple[ProjectValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether validation found no issues."""
        return not self.issues
