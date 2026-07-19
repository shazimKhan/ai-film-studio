"""Reference sheet data contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Self

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class ReferenceStatus(StrEnum):
    """Review states for extracted reference images."""

    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"


class ReferenceOutputFormat(StrEnum):
    """Supported split output image formats."""

    PNG = "png"
    JPG = "jpg"
    WEBP = "webp"


class NormalizedCrop(BaseModel):
    """Normalized crop rectangle using values from 0.0 to 1.0."""

    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_inside_unit_space(self) -> Self:
        """Reject crops that extend outside the normalized source bounds."""
        if self.x + self.width > 1.0:
            msg = "Crop x + width must be less than or equal to 1.0."
            raise ValueError(msg)
        if self.y + self.height > 1.0:
            msg = "Crop y + height must be less than or equal to 1.0."
            raise ValueError(msg)
        return self

    def with_padding(self, padding: float) -> NormalizedCrop:
        """Return a crop expanded by normalized padding on every side."""
        if padding == 0:
            return self
        return NormalizedCrop(
            x=self.x - padding,
            y=self.y - padding,
            width=self.width + (padding * 2),
            height=self.height + (padding * 2),
        )


class PixelCrop(BaseModel):
    """Pixel crop rectangle derived from a normalized crop."""

    model_config = ConfigDict(extra="forbid")

    left: int = Field(ge=0)
    top: int = Field(ge=0)
    right: int = Field(gt=0)
    bottom: int = Field(gt=0)

    @property
    def width(self) -> int:
        """Crop width in pixels."""
        return self.right - self.left

    @property
    def height(self) -> int:
        """Crop height in pixels."""
        return self.bottom - self.top


class ReferenceSheetPanel(BaseModel):
    """Single panel declared by a reusable reference sheet layout."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    output_filename: str = Field(min_length=1)
    crop: NormalizedCrop | None = None
    row: int | None = Field(default=None, ge=0)
    column: int | None = Field(default=None, ge=0)
    tags: tuple[str, ...] = ()
    shot_types: tuple[str, ...] = ()
    camera_angles: tuple[str, ...] = ()
    priority: int = Field(default=100, ge=0)
    required: bool = True
    padding: float = Field(default=0.0, ge=0.0, le=0.25)
    description: str = ""

    @field_validator("name", "output_filename")
    @classmethod
    def validate_clean_text(cls, value: str) -> str:
        """Reject empty or path-like identifiers."""
        cleaned = value.strip()
        if not cleaned:
            msg = "Value cannot be empty."
            raise ValueError(msg)
        if "/" in cleaned or "\\" in cleaned:
            msg = "Panel names and output filenames must not contain path separators."
            raise ValueError(msg)
        return cleaned

    @field_validator("tags", "shot_types", "camera_angles", mode="before")
    @classmethod
    def coerce_text_tuple(cls, value: Any) -> tuple[str, ...]:
        """Normalize YAML list values into stable tuples."""
        if value is None:
            return ()
        if isinstance(value, str):
            return (value,)
        if isinstance(value, list | tuple):
            return tuple(str(item).strip() for item in value if str(item).strip())
        msg = "Expected a string or list of strings."
        raise ValueError(msg)

    @model_validator(mode="after")
    def validate_crop_or_grid_position(self) -> Self:
        """Ensure every panel can be resolved to a crop rectangle."""
        has_grid_position = self.row is not None and self.column is not None
        if self.crop is None and not has_grid_position:
            msg = "Panel must define either a normalized crop or row and column."
            raise ValueError(msg)
        return self


class ReferenceSheetLayout(BaseModel):
    """Reusable deterministic layout for splitting a reference sheet."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    description: str = ""
    rows: int = Field(gt=0)
    columns: int = Field(gt=0)
    panels: tuple[ReferenceSheetPanel, ...] = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def validate_layout_id(cls, value: str) -> str:
        """Keep layout ids path-safe."""
        cleaned = value.strip()
        if not cleaned:
            msg = "Layout id cannot be empty."
            raise ValueError(msg)
        if "/" in cleaned or "\\" in cleaned:
            msg = "Layout id must not contain path separators."
            raise ValueError(msg)
        return cleaned

    @model_validator(mode="after")
    def validate_unique_panels(self) -> Self:
        """Reject duplicated panel names or output filenames."""
        names: set[str] = set()
        output_names: set[str] = set()
        for panel in self.panels:
            if panel.name in names:
                msg = f"Duplicate panel name '{panel.name}'."
                raise ValueError(msg)
            names.add(panel.name)

            output_name = panel.output_filename.lower()
            if output_name in output_names:
                msg = f"Duplicate panel output filename '{panel.output_filename}'."
                raise ValueError(msg)
            output_names.add(output_name)

            if panel.row is not None and panel.row >= self.rows:
                msg = f"Panel '{panel.name}' row {panel.row} is outside layout rows."
                raise ValueError(msg)
            if panel.column is not None and panel.column >= self.columns:
                msg = f"Panel '{panel.name}' column {panel.column} is outside layout columns."
                raise ValueError(msg)
        return self

    def crop_for_panel(
        self,
        panel: ReferenceSheetPanel,
        overrides: MappingNormalizedCrops | None = None,
    ) -> NormalizedCrop:
        """Resolve the normalized crop for a panel, honoring manual overrides first."""
        if overrides is not None and panel.name in overrides:
            return overrides[panel.name]
        if panel.crop is not None:
            return panel.crop
        if panel.row is None or panel.column is None:
            msg = f"Panel '{panel.name}' has no crop or grid position."
            raise ValueError(msg)
        return NormalizedCrop(
            x=panel.column / self.columns,
            y=panel.row / self.rows,
            width=1 / self.columns,
            height=1 / self.rows,
        )


MappingNormalizedCrops = dict[str, NormalizedCrop]


class CropOverrideSet(BaseModel):
    """Manual crop overrides keyed by panel name."""

    model_config = ConfigDict(extra="forbid")

    panels: MappingNormalizedCrops = Field(default_factory=dict)


class SplitOptions(BaseModel):
    """Runtime options for reference sheet splitting."""

    model_config = ConfigDict(extra="forbid")

    output_format: ReferenceOutputFormat = ReferenceOutputFormat.PNG
    padding: float = Field(default=0.0, ge=0.0, le=0.25)
    min_width: int = Field(default=128, gt=0)
    min_height: int = Field(default=128, gt=0)
    overwrite: bool = False
    dry_run: bool = False


class PlannedCrop(BaseModel):
    """Validated crop plan before files are written."""

    model_config = ConfigDict(extra="forbid")

    panel: ReferenceSheetPanel
    normalized_crop: NormalizedCrop
    pixel_crop: PixelCrop
    output_path: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class GeneratedReference(BaseModel):
    """Image generated from a panel split."""

    model_config = ConfigDict(extra="forbid")

    name: str
    path: str
    normalized_crop: NormalizedCrop
    pixel_crop: PixelCrop
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    tags: tuple[str, ...] = ()
    shot_types: tuple[str, ...] = ()
    camera_angles: tuple[str, ...] = ()
    priority: int = Field(ge=0)
    checksum: str
    validation_status: ReferenceStatus = ReferenceStatus.PENDING_REVIEW


class ReferenceSheetSplitResult(BaseModel):
    """Result of a reference sheet split or dry run."""

    model_config = ConfigDict(extra="forbid")

    project: str
    character: str
    layout_id: str
    source_image: str
    source_checksum: str
    source_width: int = Field(gt=0)
    source_height: int = Field(gt=0)
    preview_path: str | None = None
    manifest_path: str | None = None
    generated_files: tuple[GeneratedReference, ...] = ()
    planned_crops: tuple[PlannedCrop, ...] = ()
    dry_run: bool = False


class SelectedReference(BaseModel):
    """Reference chosen for a generation request."""

    model_config = ConfigDict(extra="forbid")

    name: str
    path: str
    score: float
    priority: int
    reason: str = ""
    tags: tuple[str, ...] = ()
    status: ReferenceStatus = ReferenceStatus.PENDING_REVIEW


class ExcludedReference(BaseModel):
    """Reference that was considered but not selected."""

    model_config = ConfigDict(extra="forbid")

    name: str
    path: str | None = None
    reason: str
    score: float = 0.0
    status: ReferenceStatus = ReferenceStatus.PENDING_REVIEW
    tags: tuple[str, ...] = ()


class ReferenceSelectionRequest(BaseModel):
    """Engine-neutral reference selection input."""

    model_config = ConfigDict(extra="forbid")

    camera_shot_type: str | None = None
    angle: str | None = None
    framing: str | None = None
    action: str | None = None
    pose: str | None = None
    approved_only: bool = True
    engine_reference_limit: int = Field(default=1, gt=0)
    preferred_reference_types: tuple[str, ...] = ()
    allow_weak_fallbacks: bool = False

    @field_validator(
        "camera_shot_type",
        "angle",
        "framing",
        "action",
        "pose",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        """Normalize blank strings to ``None``."""
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("preferred_reference_types", mode="before")
    @classmethod
    def coerce_preferred_types(cls, value: Any) -> tuple[str, ...]:
        """Normalize preferred reference type filters."""
        if value is None:
            return ()
        if isinstance(value, str):
            return (value,)
        if isinstance(value, list | tuple):
            return tuple(str(item).strip() for item in value if str(item).strip())
        msg = "Expected a string or list of strings."
        raise ValueError(msg)


class ReferenceSelectionResult(BaseModel):
    """Explainable result for a character reference selection request."""

    model_config = ConfigDict(extra="forbid")

    character_id: str
    selector_inputs: ReferenceSelectionRequest
    selected: tuple[SelectedReference, ...] = ()
    excluded: tuple[ExcludedReference, ...] = ()
    engine_reference_limit: int = Field(gt=0)
    allow_weak_fallbacks: bool = False


class ReferenceImageValidation(BaseModel):
    """Validation result for a single mapped character reference image."""

    model_config = ConfigDict(extra="forbid")

    name: str
    path: str | None = None
    exists: bool = False
    readable: bool = False
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    checksum: str | None = None
    expected_checksum: str | None = None
    checksum_matches: bool | None = None
    status: ReferenceStatus = ReferenceStatus.PENDING_REVIEW
    approved: bool = False
    reason: str = ""

    @property
    def is_valid(self) -> bool:
        """Return whether the image exists, is readable, and matches checksum if present."""
        checksum_ok = self.checksum_matches is not False
        return self.exists and self.readable and checksum_ok


class ReferenceSceneCamera(BaseModel):
    """Camera inputs used for reference selection integration scenes."""

    model_config = ConfigDict(extra="forbid")

    shot_type: str = Field(
        min_length=1,
        validation_alias=AliasChoices("shot_type", "shot", "camera_shot_type"),
    )
    angle: str = Field(min_length=1)
    framing: str | None = None
    pose: str | None = None


class ReferenceSelectionScene(BaseModel):
    """Small test scene blueprint for reference selector integration."""

    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1)
    character: str = Field(min_length=1)
    title: str = Field(min_length=1)
    action: str = Field(min_length=1)
    camera: ReferenceSceneCamera = Field(validation_alias=AliasChoices("camera", "Camera"))
    expected_reference: str | None = None


class SceneReferenceSelectionArtifact(BaseModel):
    """Manifest artifact emitted by reference selection scene compilation."""

    model_config = ConfigDict(extra="forbid")

    scene_file: str
    output_path: str
    result: ReferenceSelectionResult
    validations: tuple[ReferenceImageValidation, ...] = ()
