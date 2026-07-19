"""Asset bible data contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AssetValidationSeverity(StrEnum):
    """Severity levels for asset validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AssetValidationIssue(BaseModel):
    """Single asset validation issue."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: str
    severity: AssetValidationSeverity = AssetValidationSeverity.ERROR


class AssetReferenceImage(BaseModel):
    """Reference image slot captured in the asset index."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1)
    name: str = Field(min_length=1)
    path: str
    exists: bool


class AssetRecord(BaseModel):
    """Indexed production asset."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    asset_type: str = Field(min_length=1)
    path: str
    yaml_path: str | None = None
    prompt_path: str | None = None
    notes_path: str | None = None
    reference_status: str = "awaiting_reference"
    reference_images: tuple[AssetReferenceImage, ...] = ()


class AssetIndex(BaseModel):
    """Full asset index for a project."""

    model_config = ConfigDict(extra="forbid")

    project_root: str
    characters: tuple[AssetRecord, ...] = ()
    environments: tuple[AssetRecord, ...] = ()
    props: tuple[AssetRecord, ...] = ()


class AssetValidationReport(BaseModel):
    """Validation output plus generated index path."""

    model_config = ConfigDict(extra="forbid")

    index_path: str
    index: AssetIndex
    issues: tuple[AssetValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether no error-level issues were found."""
        return all(issue.severity != AssetValidationSeverity.ERROR for issue in self.issues)
