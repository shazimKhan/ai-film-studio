"""Reusable identity-lock validation and reference resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ai_film_studio.core.exceptions import AssetNotFoundError, MalformedConfigurationError
from ai_film_studio.module_loader import ModuleLoader

APPROVED_IDENTITY_STATUS = "approved"
STRICT_LOCK_LEVEL = "strict"


class IdentityModel(BaseModel):
    """Base model for identity-lock contracts."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class CanonicalReference(IdentityModel):
    """Canonical approved identity reference metadata."""

    path: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    version: str = Field(min_length=1)


class IdentityReferenceImage(IdentityModel):
    """Required local reference image for a locked identity."""

    path: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    required: bool = True


class IdentityProfile(BaseModel):
    """Project-local identity lock profile for a reusable character."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    schema_version: str = "1.0"
    project_id: str | None = Field(default=None, min_length=1)
    character_id: str = Field(min_length=1)
    identity_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    identity_locked: bool = False
    lock_level: str = Field(default="standard", min_length=1)
    canonical_reference: CanonicalReference | None = None
    reference_image: IdentityReferenceImage | None = None
    immutable_attributes: tuple[str, ...] = ()
    mutable_attributes: tuple[str, ...] = ()
    continuity_prompt: str | None = Field(default=None, min_length=1)
    negative_continuity_prompt: str | None = Field(default=None, min_length=1)
    validation_status: str = Field(default="pending", min_length=1)

    @field_validator("immutable_attributes", "mutable_attributes", mode="before")
    @classmethod
    def coerce_string_tuple(cls, value: Any) -> tuple[str, ...]:
        """Normalize YAML lists into clean immutable tuples."""
        if value is None:
            return ()
        if isinstance(value, str):
            cleaned = value.strip()
            return (cleaned,) if cleaned else ()
        if isinstance(value, list | tuple):
            return tuple(str(item).strip() for item in value if str(item).strip())
        msg = "Expected a string or list of strings."
        raise ValueError(msg)

    @property
    def is_strict(self) -> bool:
        """Return whether this identity uses a strict continuity lock."""
        return self.lock_level == STRICT_LOCK_LEVEL

    @property
    def is_approved(self) -> bool:
        """Return whether this identity has been approved for production use."""
        return self.status == APPROVED_IDENTITY_STATUS


class IdentityContinuityContext(IdentityModel):
    """Compiler-ready continuity block for a locked identity."""

    character_id: str
    identity_id: str
    lock_level: str
    continuity_prompt: str
    immutable_attributes: tuple[str, ...] = ()
    mutable_attributes: tuple[str, ...] = ()
    negative_continuity_prompt: str | None = None


class IdentityReferenceAsset(IdentityModel):
    """Engine-neutral reference asset metadata for generation requests."""

    character_id: str
    identity_id: str
    path: str
    required: bool
    identity_lock: str


@dataclass(frozen=True, slots=True)
class IdentityValidationIssue:
    """Single identity validation issue."""

    code: str
    path: str
    message: str


class IdentityLockService:
    """Loads, validates, and resolves project-local identity locks."""

    def __init__(
        self,
        *,
        repo_root: Path,
        module_loader: ModuleLoader | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._module_loader = module_loader or ModuleLoader()

    def load_identity(self, project_root: Path, character_id: str) -> IdentityProfile:
        """Load and validate one character identity profile."""
        resolved_project_root = self._resolve_project_root(project_root)
        identity_path = self.identity_path(resolved_project_root, character_id)
        if not identity_path.is_file():
            msg = f"Identity config for character '{character_id}' not found at '{identity_path}'."
            raise AssetNotFoundError(msg)

        try:
            raw_identity = self._module_loader.load_yaml_file(identity_path)
        except Exception as exc:
            msg = f"Could not load identity config '{identity_path}': {exc}"
            raise MalformedConfigurationError(msg) from exc

        try:
            identity = IdentityProfile.model_validate(raw_identity)
        except ValidationError as exc:
            msg = f"Invalid identity config '{identity_path}': {exc}"
            raise MalformedConfigurationError(msg) from exc

        if identity.character_id != character_id:
            msg = (
                f"Identity config '{identity_path}' declares character "
                f"'{identity.character_id}', expected '{character_id}'."
            )
            raise MalformedConfigurationError(msg)

        self.validate_identity(
            identity,
            project_root=resolved_project_root,
            identity_path=identity_path,
        )
        return identity

    def try_load_identity(self, project_root: Path, character_id: str) -> IdentityProfile | None:
        """Load a character identity profile when one exists."""
        resolved_project_root = self._resolve_project_root(project_root)
        identity_path = self.identity_path(resolved_project_root, character_id)
        if not identity_path.exists():
            return None
        return self.load_identity(resolved_project_root, character_id)

    def validate_identity(
        self,
        identity: IdentityProfile,
        *,
        project_root: Path,
        identity_path: Path | None = None,
    ) -> None:
        """Validate one identity profile and raise a readable error on failure."""
        issues = self.identity_issues(
            identity,
            project_root=project_root,
            identity_path=identity_path,
        )
        if not issues:
            return

        issue_text = "; ".join(f"{issue.code}: {issue.message}" for issue in issues)
        msg = f"Identity validation failed for '{identity.character_id}': {issue_text}"
        raise MalformedConfigurationError(msg)

    def identity_issues(
        self,
        identity: IdentityProfile,
        *,
        project_root: Path,
        identity_path: Path | None = None,
    ) -> tuple[IdentityValidationIssue, ...]:
        """Return validation issues for one identity profile."""
        path_label = self._repo_relative(identity_path or project_root)
        issues: list[IdentityValidationIssue] = []

        if identity.identity_locked and not identity.is_approved:
            issues.append(
                IdentityValidationIssue(
                    code="identity.locked_unapproved",
                    path=path_label,
                    message="Locked identities must have status 'approved'.",
                ),
            )

        if identity.identity_locked and identity.reference_image is None:
            issues.append(
                IdentityValidationIssue(
                    code="identity.missing_reference_image",
                    path=path_label,
                    message="Locked identities must define reference_image.",
                ),
            )

        if identity.identity_locked and identity.is_strict and not identity.immutable_attributes:
            issues.append(
                IdentityValidationIssue(
                    code="identity.missing_immutable_attributes",
                    path=path_label,
                    message="Strict identity locks must define immutable_attributes.",
                ),
            )

        if identity.identity_locked and identity.is_strict and not identity.continuity_prompt:
            issues.append(
                IdentityValidationIssue(
                    code="identity.missing_continuity_prompt",
                    path=path_label,
                    message="Strict identity locks must define continuity_prompt.",
                ),
            )

        issues.extend(self._reference_issues(identity, path_label))
        return tuple(issues)

    def validate_project(self, project_root: Path) -> tuple[IdentityValidationIssue, ...]:
        """Validate every identity profile in a project and reject duplicate ids."""
        resolved_project_root = self._resolve_project_root(project_root)
        identity_paths = sorted(
            (resolved_project_root / "05_characters").glob("*/identity.yaml"),
        )
        issues: list[IdentityValidationIssue] = []
        seen_identity_ids: dict[str, Path] = {}

        for identity_path in identity_paths:
            character_id = identity_path.parent.name
            try:
                identity = self.load_identity(resolved_project_root, character_id)
            except MalformedConfigurationError as exc:
                issues.append(
                    IdentityValidationIssue(
                        code="identity.invalid",
                        path=self._repo_relative(identity_path),
                        message=str(exc),
                    ),
                )
                continue
            except AssetNotFoundError as exc:
                issues.append(
                    IdentityValidationIssue(
                        code="identity.missing",
                        path=self._repo_relative(identity_path),
                        message=str(exc),
                    ),
                )
                continue

            duplicate_path = seen_identity_ids.get(identity.identity_id)
            if duplicate_path is not None:
                issues.append(
                    IdentityValidationIssue(
                        code="identity.duplicate_id",
                        path=self._repo_relative(identity_path),
                        message=(
                            f"Duplicate identity id '{identity.identity_id}' also used in "
                            f"'{self._repo_relative(duplicate_path)}'."
                        ),
                    ),
                )
            else:
                seen_identity_ids[identity.identity_id] = identity_path

        return tuple(issues)

    def build_continuity_context(self, identity: IdentityProfile) -> IdentityContinuityContext:
        """Build the compiler continuity context for a validated identity."""
        if not identity.continuity_prompt:
            msg = f"Identity '{identity.identity_id}' does not define a continuity prompt."
            raise MalformedConfigurationError(msg)
        return IdentityContinuityContext(
            character_id=identity.character_id,
            identity_id=identity.identity_id,
            lock_level=identity.lock_level,
            continuity_prompt=identity.continuity_prompt,
            immutable_attributes=identity.immutable_attributes,
            mutable_attributes=identity.mutable_attributes,
            negative_continuity_prompt=identity.negative_continuity_prompt,
        )

    def resolve_reference_assets(
        self,
        identity: IdentityProfile,
    ) -> tuple[IdentityReferenceAsset, ...]:
        """Resolve mandatory reference image metadata for a locked identity."""
        if not identity.identity_locked or identity.reference_image is None:
            return ()
        return (
            IdentityReferenceAsset(
                character_id=identity.character_id,
                identity_id=identity.identity_id,
                path=identity.reference_image.path,
                required=identity.reference_image.required,
                identity_lock=identity.lock_level,
            ),
        )

    @staticmethod
    def identity_path(project_root: Path, character_id: str) -> Path:
        """Return the conventional identity.yaml path for a character."""
        return project_root / "05_characters" / character_id / "identity.yaml"

    def _reference_issues(
        self,
        identity: IdentityProfile,
        path_label: str,
    ) -> tuple[IdentityValidationIssue, ...]:
        issues: list[IdentityValidationIssue] = []

        if identity.canonical_reference and identity.reference_image:
            if identity.canonical_reference.path != identity.reference_image.path:
                issues.append(
                    IdentityValidationIssue(
                        code="identity.reference_mismatch",
                        path=path_label,
                        message="canonical_reference.path must match reference_image.path.",
                    ),
                )
            if identity.canonical_reference.filename != identity.reference_image.filename:
                issues.append(
                    IdentityValidationIssue(
                        code="identity.filename_mismatch",
                        path=path_label,
                        message="canonical_reference.filename must match reference_image.filename.",
                    ),
                )

        if identity.reference_image is None:
            return tuple(issues)

        reference_path = Path(identity.reference_image.path)
        if reference_path.name != identity.reference_image.filename:
            issues.append(
                IdentityValidationIssue(
                    code="identity.filename_mismatch",
                    path=path_label,
                    message="reference_image.filename must match the configured path filename.",
                ),
            )

        if identity.identity_locked:
            resolved_path = self._resolve_reference_path(identity.reference_image.path)
            if identity.reference_image.required and not resolved_path.is_file():
                issues.append(
                    IdentityValidationIssue(
                        code="identity.reference_missing",
                        path=self._repo_relative(resolved_path),
                        message=(
                            f"Required identity reference image '{resolved_path}' does not exist."
                        ),
                    ),
                )

        return tuple(issues)

    def _resolve_reference_path(self, path: str) -> Path:
        reference_path = Path(path)
        if reference_path.is_absolute():
            return reference_path
        return self._repo_root / reference_path

    def _resolve_project_root(self, project_root: Path) -> Path:
        if project_root.is_absolute():
            return project_root
        return self._repo_root / project_root

    def _repo_relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self._repo_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()
