"""Reference image inventory validation and guarded approval."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, UnidentifiedImageError

from ai_film_studio.core.exceptions import ReferenceSheetError
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.reference_sheets.models import (
    PRODUCTION_SELECTABLE_SOURCE_TYPES,
    ProductionReadiness,
    ReferenceImageValidation,
    ReferenceSourceType,
    ReferenceStatus,
)

REQUIRED_PRODUCTION_REFERENCES = (
    "front",
    "left_profile",
    "three_quarter_left",
    "three_quarter_right",
    "full_body_front",
    "full_body_back",
    "seated_front",
)
PRODUCTION_REFERENCE_TYPES = (
    "front",
    "left_profile",
    "right_profile",
    "three_quarter_left",
    "three_quarter_right",
    "full_body_front",
    "full_body_back",
    "seated_front",
)
PORTRAIT_REFERENCE_TYPES = {
    "front",
    "left_profile",
    "right_profile",
    "three_quarter_left",
    "three_quarter_right",
}
FULL_BODY_REFERENCE_TYPES = {"full_body_front", "full_body_back", "seated_front"}


class ReferenceInventoryService:
    """Validates mapped reference images and approves only valid references."""

    def __init__(self, *, repo_root: Path, module_loader: ModuleLoader | None = None) -> None:
        self._repo_root = repo_root
        self._module_loader = module_loader or ModuleLoader()

    def validate_character(
        self,
        *,
        project: str,
        character: str,
    ) -> tuple[ReferenceImageValidation, ...]:
        """Validate all mapped character reference images."""
        character_yaml = self._character_yaml(project, character)
        data = self._load_character(character_yaml)
        return tuple(
            self._validate_view(
                character_yaml.parent,
                entry.name,
                entry.raw,
                min_dimensions=self._min_dimensions(entry.name)
                if entry.section == "production"
                else None,
                duplicate_path=entry.duplicate_path,
                default_source_type=entry.default_source_type,
                default_production_selectable=entry.default_production_selectable,
            )
            for entry in self._reference_entries(data)
        )

    def validate_production_references(
        self,
        *,
        project: str,
        character: str,
    ) -> tuple[ReferenceImageValidation, ...]:
        """Validate production-selectable native HD or generated variant references."""
        character_yaml = self._character_yaml(project, character)
        data = self._load_character(character_yaml)
        entries = [
            entry for entry in self._reference_entries(data) if entry.section == "production"
        ]
        present = {entry.name for entry in entries}
        validations = [
            self._validate_view(
                character_yaml.parent,
                entry.name,
                entry.raw,
                min_dimensions=self._min_dimensions(entry.name),
                duplicate_path=entry.duplicate_path,
                default_source_type=entry.default_source_type,
                default_production_selectable=entry.default_production_selectable,
            )
            for entry in entries
        ]
        for required in REQUIRED_PRODUCTION_REFERENCES:
            if required not in present:
                min_width, min_height = self._min_dimensions(required)
                validations.append(
                    ReferenceImageValidation(
                        name=required,
                        exists=False,
                        readable=False,
                        source_type=ReferenceSourceType.NATIVE_HIGH_RESOLUTION,
                        source_type_valid=True,
                        production_selectable=True,
                        min_width=min_width,
                        min_height=min_height,
                        reason="required production reference missing",
                    ),
                )
        return tuple(sorted(validations, key=lambda item: item.name))

    def register_production_reference(
        self,
        *,
        project: str,
        character: str,
        reference_type: str,
        path: Path,
        source_type: ReferenceSourceType = ReferenceSourceType.NATIVE_HIGH_RESOLUTION,
    ) -> Path:
        """Register a separately generated production reference image."""
        reference_type = reference_type.strip()
        if reference_type not in PRODUCTION_REFERENCE_TYPES:
            allowed = ", ".join(PRODUCTION_REFERENCE_TYPES)
            msg = (
                f"Unsupported production reference type '{reference_type}'. "
                f"Use one of: {allowed}."
            )
            raise ReferenceSheetError(msg)
        if source_type not in PRODUCTION_SELECTABLE_SOURCE_TYPES:
            msg = f"Production references must use source type '{source_type.value}'."
            raise ReferenceSheetError(msg)

        character_yaml = self._character_yaml(project, character)
        data = self._load_character(character_yaml)
        resolved_path = path if path.is_absolute() else self._repo_root / path
        relative_path = _relative_to(character_yaml.parent, resolved_path)
        reference_images = _ensure_mapping(data, "reference_images")
        production = _ensure_mapping(reference_images, "production")
        current = production.get(reference_type)
        if not isinstance(current, dict):
            current = {}
        current.update(
            {
                "path": relative_path,
                "source_type": source_type.value,
                "production_selectable": True,
                "status": current.get("status") or ReferenceStatus.PENDING_REVIEW.value,
                "approved": current.get("approved") is True,
            },
        )
        current.setdefault("tags", _tags_for_reference_type(reference_type))
        current.setdefault("shot_types", _shot_types_for_reference_type(reference_type))
        current.setdefault("camera_angles", _camera_angles_for_reference_type(reference_type))
        current.setdefault("priority", _priority_for_reference_type(reference_type))
        production[reference_type] = current
        self._write_character_yaml(character_yaml, data)
        return character_yaml

    def production_readiness(self, *, project: str, character: str) -> ProductionReadiness:
        """Return production readiness based on approved native HD production refs."""
        validations = self.validate_production_references(project=project, character=character)
        validation_by_name = {validation.name: validation for validation in validations}
        ready: list[str] = []
        missing: list[str] = []
        invalid: list[str] = []
        for reference_name in REQUIRED_PRODUCTION_REFERENCES:
            validation = validation_by_name.get(reference_name)
            if validation is None or not validation.exists:
                missing.append(reference_name)
                continue
            if (
                validation.is_valid
                and validation.approved
                and validation.production_selectable
                and validation.source_type in PRODUCTION_SELECTABLE_SOURCE_TYPES
            ):
                ready.append(reference_name)
            else:
                invalid.append(reference_name)
        return ProductionReadiness(
            character_id=character,
            production_ready=len(ready) == len(REQUIRED_PRODUCTION_REFERENCES),
            required_references=REQUIRED_PRODUCTION_REFERENCES,
            ready_references=tuple(ready),
            missing_references=tuple(missing),
            invalid_references=tuple(invalid),
        )

    def migrate_cropped_references(self, *, project: str, character: str) -> Path:
        """Move cropped references to legacy preview metadata without deleting files."""
        character_yaml = self._character_yaml(project, character)
        data = self._load_character(character_yaml)
        reference_images = _ensure_mapping(data, "reference_images")
        master_sheet = reference_images.get("master_sheet")
        if isinstance(master_sheet, dict):
            master_sheet["source_type"] = ReferenceSourceType.MASTER_SHEET.value
            master_sheet["production_selectable"] = False

        legacy_crops = _ensure_mapping(reference_images, "legacy_crops")
        for key in ("views", "legacy_crops"):
            current = reference_images.get(key)
            if not isinstance(current, dict):
                continue
            for name, raw_reference in current.items():
                if not isinstance(raw_reference, dict):
                    continue
                migrated = dict(raw_reference)
                migrated["source_type"] = ReferenceSourceType.CROPPED_PREVIEW.value
                migrated["production_selectable"] = False
                legacy_crops[str(name)] = migrated
            if key == "views":
                reference_images.pop("views", None)

        production = _ensure_mapping(reference_images, "production")
        for reference_name in PRODUCTION_REFERENCE_TYPES:
            production.setdefault(
                reference_name,
                {
                    "path": f"references/production/{reference_name}.png",
                    "source_type": ReferenceSourceType.NATIVE_HIGH_RESOLUTION.value,
                    "production_selectable": True,
                    "status": ReferenceStatus.PENDING_REVIEW.value,
                    "approved": False,
                    "tags": _tags_for_reference_type(reference_name),
                    "shot_types": _shot_types_for_reference_type(reference_name),
                    "camera_angles": _camera_angles_for_reference_type(reference_name),
                    "priority": _priority_for_reference_type(reference_name),
                },
            )
        data["production_ready"] = False
        self._write_character_yaml(character_yaml, data)
        self._sync_manifest_statuses(character_yaml, data)
        return character_yaml

    def validate_reference(
        self,
        *,
        project: str,
        character: str,
        reference: str,
    ) -> ReferenceImageValidation:
        """Validate a single mapped reference view."""
        character_yaml = self._character_yaml(project, character)
        data = self._load_character(character_yaml)
        entry = self._find_reference_entry(data, reference)
        if entry is None:
            msg = f"Reference '{reference}' was not found for character '{character}'."
            raise ReferenceSheetError(msg)
        source_type, _ = _source_type(
            entry.raw,
            default=entry.default_source_type,
        )
        min_dimensions = (
            self._min_dimensions(reference)
            if source_type in PRODUCTION_SELECTABLE_SOURCE_TYPES
            else None
        )
        return self._validate_view(
            character_yaml.parent,
            reference,
            entry.raw,
            min_dimensions=min_dimensions,
            duplicate_path=entry.duplicate_path,
            default_source_type=(
                source_type
                if source_type is not None
                else entry.default_source_type
            ),
            default_production_selectable=entry.default_production_selectable,
        )

    def approve_valid_references(
        self,
        *,
        project: str,
        character: str,
        references: tuple[str, ...],
    ) -> tuple[ReferenceImageValidation, ...]:
        """Approve named references only after image validation passes."""
        character_yaml = self._character_yaml(project, character)
        data = self._load_character(character_yaml)
        validations: list[ReferenceImageValidation] = []
        changed = False
        for reference in references:
            entry = self._find_reference_entry(data, reference)
            if entry is None:
                validations.append(
                    ReferenceImageValidation(
                        name=reference,
                        exists=False,
                        readable=False,
                        reason="reference is missing from character.yaml",
                    ),
                )
                continue

            source_type, _ = _source_type(
                entry.raw,
                default=entry.default_source_type,
            )
            validation = self._validate_view(
                character_yaml.parent,
                reference,
                entry.raw,
                min_dimensions=(
                    self._min_dimensions(reference)
                    if source_type in PRODUCTION_SELECTABLE_SOURCE_TYPES
                    else None
                ),
                duplicate_path=entry.duplicate_path,
                default_source_type=(
                    source_type
                    if source_type is not None
                    else entry.default_source_type
                ),
                default_production_selectable=entry.default_production_selectable,
            )
            validations.append(validation)
            if not validation.is_valid:
                continue
            entry.raw["status"] = ReferenceStatus.APPROVED.value
            entry.raw["approved"] = True
            entry.raw.pop("rejection_reason", None)
            changed = True

        if changed:
            self._write_character_yaml(character_yaml, data)
            self._sync_manifest_statuses(character_yaml, data)
        return tuple(validations)

    def sync_manifest_statuses(self, *, project: str, character: str) -> None:
        """Sync the reference sheet manifest status fields from character YAML."""
        character_yaml = self._character_yaml(project, character)
        data = self._load_character(character_yaml)
        self._sync_manifest_statuses(character_yaml, data)

    def _validate_view(
        self,
        character_dir: Path,
        name: str,
        raw_view: dict[str, Any],
        *,
        min_dimensions: tuple[int, int] | None = None,
        duplicate_path: bool = False,
        default_source_type: ReferenceSourceType = ReferenceSourceType.NATIVE_HIGH_RESOLUTION,
        default_production_selectable: bool = True,
    ) -> ReferenceImageValidation:
        path_value = raw_view.get("path")
        status = _status(raw_view)
        source_type, source_type_valid = _source_type(raw_view, default=default_source_type)
        production_selectable = _production_selectable(
            raw_view,
            source_type=source_type,
            default=default_production_selectable,
        )
        min_width, min_height = min_dimensions or (None, None)
        if not isinstance(path_value, str) or not path_value.strip():
            return ReferenceImageValidation(
                name=name,
                exists=False,
                readable=False,
                source_type=source_type,
                source_type_valid=source_type_valid,
                production_selectable=production_selectable,
                duplicate_path=duplicate_path,
                min_width=min_width,
                min_height=min_height,
                status=status,
                approved=raw_view.get("approved") is True,
                reason="missing reference path",
            )

        image_path = character_dir / path_value
        if not image_path.is_file():
            return ReferenceImageValidation(
                name=name,
                path=path_value,
                exists=False,
                readable=False,
                source_type=source_type,
                source_type_valid=source_type_valid,
                production_selectable=production_selectable,
                duplicate_path=duplicate_path,
                min_width=min_width,
                min_height=min_height,
                status=status,
                approved=raw_view.get("approved") is True,
                reason="image file does not exist",
            )

        try:
            with Image.open(image_path) as image:
                width, height = image.size
                image.verify()
        except (OSError, UnidentifiedImageError) as exc:
            return ReferenceImageValidation(
                name=name,
                path=path_value,
                exists=True,
                readable=False,
                source_type=source_type,
                source_type_valid=source_type_valid,
                production_selectable=production_selectable,
                duplicate_path=duplicate_path,
                min_width=min_width,
                min_height=min_height,
                status=status,
                approved=raw_view.get("approved") is True,
                reason=f"image is not readable: {exc}",
            )

        checksum = _sha256(image_path)
        expected_checksum = raw_view.get("checksum")
        checksum_matches = None
        if isinstance(expected_checksum, str) and expected_checksum.strip():
            checksum_matches = checksum == expected_checksum
        reason = "valid"
        if checksum_matches is False:
            reason = "checksum mismatch"
        if not source_type_valid:
            reason = "invalid source type"
        elif min_width is not None and source_type not in PRODUCTION_SELECTABLE_SOURCE_TYPES:
            reason = "source type is not production selectable"
        elif duplicate_path:
            reason = "duplicate production reference path"
        elif min_width is not None and width < min_width:
            reason = f"image width below minimum {min_width}"
        elif min_height is not None and height < min_height:
            reason = f"image height below minimum {min_height}"
        elif source_type in PRODUCTION_SELECTABLE_SOURCE_TYPES and not production_selectable:
            reason = "production_selectable must be true"
        return ReferenceImageValidation(
            name=name,
            path=path_value,
            exists=True,
            readable=True,
            width=width,
            height=height,
            checksum=checksum,
            expected_checksum=expected_checksum if isinstance(expected_checksum, str) else None,
            checksum_matches=checksum_matches,
            source_type=source_type,
            source_type_valid=source_type_valid,
            production_selectable=production_selectable,
            duplicate_path=duplicate_path,
            min_width=min_width,
            min_height=min_height,
            status=status,
            approved=raw_view.get("approved") is True,
            reason=reason,
        )

    def _sync_manifest_statuses(self, character_yaml: Path, data: dict[str, Any]) -> None:
        reference_images = data.get("reference_images")
        if not isinstance(reference_images, dict):
            return
        master_sheet = reference_images.get("master_sheet")
        legacy_crops = reference_images.get("legacy_crops")
        views = reference_images.get("views")
        crop_sources = []
        if isinstance(legacy_crops, dict):
            crop_sources.append(legacy_crops)
        if isinstance(views, dict):
            crop_sources.append(views)
        if not isinstance(master_sheet, dict) or not crop_sources:
            return
        manifest_path = master_sheet.get("manifest_path")
        if not isinstance(manifest_path, str) or not manifest_path.strip():
            return

        resolved_manifest = character_yaml.parent / manifest_path
        if not resolved_manifest.is_file():
            return
        try:
            manifest = json.loads(resolved_manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        for generated in manifest.get("generated_files", []):
            if not isinstance(generated, dict):
                continue
            name = generated.get("name")
            if not isinstance(name, str):
                continue
            raw_view = next(
                (
                    crop_source.get(name)
                    for crop_source in crop_sources
                    if isinstance(crop_source.get(name), dict)
                ),
                None,
            )
            if not isinstance(raw_view, dict):
                continue
            status = raw_view.get("status")
            if isinstance(status, str):
                generated["validation_status"] = status

        resolved_manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _character_yaml(self, project: str, character: str) -> Path:
        return self._repo_root / "projects" / project / "characters" / character / "character.yaml"

    def _load_character(self, character_yaml: Path) -> dict[str, Any]:
        if not character_yaml.is_file():
            msg = f"Character asset file '{character_yaml}' does not exist."
            raise ReferenceSheetError(msg)
        try:
            return self._module_loader.load_yaml_file(character_yaml)
        except Exception as exc:
            msg = f"Could not load character asset '{character_yaml}': {exc}"
            raise ReferenceSheetError(msg) from exc

    def _find_reference_entry(
        self,
        data: dict[str, Any],
        reference: str,
    ) -> _ReferenceEntry | None:
        for entry in self._reference_entries(data):
            if entry.name == reference:
                return entry
        return None

    def _reference_entries(self, data: dict[str, Any]) -> tuple[_ReferenceEntry, ...]:
        reference_images = data.get("reference_images")
        if not isinstance(reference_images, dict):
            return ()
        paths: dict[str, int] = {}
        for section_name in ("production", "legacy_crops", "views"):
            section = reference_images.get(section_name)
            if not isinstance(section, dict):
                continue
            for raw_reference in section.values():
                if not isinstance(raw_reference, dict):
                    continue
                path = raw_reference.get("path")
                if isinstance(path, str) and path.strip():
                    paths[path] = paths.get(path, 0) + 1

        entries: list[_ReferenceEntry] = []
        production = reference_images.get("production")
        if isinstance(production, dict):
            entries.extend(
                _reference_entry(
                    name=name,
                    raw_reference=raw_reference,
                    section="production",
                    default_source_type=ReferenceSourceType.NATIVE_HIGH_RESOLUTION,
                    default_production_selectable=True,
                    duplicate_path=_is_duplicate_path(raw_reference, paths),
                )
                for name, raw_reference in production.items()
                if isinstance(raw_reference, dict)
            )
        for section_name in ("legacy_crops", "views"):
            section = reference_images.get(section_name)
            if not isinstance(section, dict):
                continue
            entries.extend(
                _reference_entry(
                    name=name,
                    raw_reference=raw_reference,
                    section=section_name,
                    default_source_type=ReferenceSourceType.CROPPED_PREVIEW,
                    default_production_selectable=False,
                    duplicate_path=False,
                )
                for name, raw_reference in section.items()
                if isinstance(raw_reference, dict)
            )
        return tuple(sorted(entries, key=lambda item: (item.section, item.name)))

    @staticmethod
    def _min_dimensions(reference_name: str) -> tuple[int, int]:
        if reference_name in FULL_BODY_REFERENCE_TYPES:
            return 1024, 1536
        if reference_name in PORTRAIT_REFERENCE_TYPES:
            return 1024, 1024
        return 1024, 1024

    def _write_character_yaml(self, character_yaml: Path, data: dict[str, Any]) -> None:
        backup_path = character_yaml.with_suffix(character_yaml.suffix + ".bak")
        try:
            shutil.copy2(character_yaml, backup_path)
            character_yaml.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        except OSError as exc:
            msg = f"Could not update character asset '{character_yaml}': {exc}"
            raise ReferenceSheetError(msg) from exc


def _status(raw_view: dict[str, Any]) -> ReferenceStatus:
    status = raw_view.get("status")
    if isinstance(status, str):
        try:
            return ReferenceStatus(status)
        except ValueError:
            return ReferenceStatus.PENDING_REVIEW
    if raw_view.get("approved") is True:
        return ReferenceStatus.APPROVED
    return ReferenceStatus.PENDING_REVIEW


@dataclass(frozen=True, slots=True)
class _ReferenceEntry:
    name: str
    raw: dict[str, Any]
    section: str
    default_source_type: ReferenceSourceType
    default_production_selectable: bool
    duplicate_path: bool


def _reference_entry(
    *,
    name: object,
    raw_reference: dict[str, Any],
    section: str,
    default_source_type: ReferenceSourceType,
    default_production_selectable: bool,
    duplicate_path: bool,
) -> _ReferenceEntry:
    return _ReferenceEntry(
        name=str(name),
        raw=raw_reference,
        section=section,
        default_source_type=default_source_type,
        default_production_selectable=default_production_selectable,
        duplicate_path=duplicate_path,
    )


def _is_duplicate_path(raw_reference: dict[str, Any], paths: dict[str, int]) -> bool:
    path = raw_reference.get("path")
    return isinstance(path, str) and paths.get(path, 0) > 1


def _source_type(
    raw_reference: dict[str, Any],
    *,
    default: ReferenceSourceType,
) -> tuple[ReferenceSourceType | None, bool]:
    source_type = raw_reference.get("source_type")
    if source_type is None:
        return default, True
    if isinstance(source_type, ReferenceSourceType):
        return source_type, True
    if isinstance(source_type, str):
        try:
            return ReferenceSourceType(source_type), True
        except ValueError:
            return None, False
    return None, False


def _production_selectable(
    raw_reference: dict[str, Any],
    *,
    source_type: ReferenceSourceType | None,
    default: bool,
) -> bool:
    value = raw_reference.get("production_selectable")
    if isinstance(value, bool):
        return value
    if source_type in PRODUCTION_SELECTABLE_SOURCE_TYPES:
        return default
    return False


def _ensure_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if value is None:
        mapping: dict[str, Any] = {}
        data[key] = mapping
        return mapping
    if not isinstance(value, dict):
        msg = f"Expected '{key}' to be a mapping."
        raise ReferenceSheetError(msg)
    return value


def _relative_to(base: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _tags_for_reference_type(reference_type: str) -> list[str]:
    base = reference_type.split("_")
    tags = [reference_type, *base]
    if reference_type in PORTRAIT_REFERENCE_TYPES:
        tags.extend(["portrait", "close_up", "identity"])
    if reference_type in FULL_BODY_REFERENCE_TYPES:
        tags.extend(["full_body", "standing", "wardrobe"])
    if reference_type == "seated_front":
        tags.extend(["seated", "sitting", "pose"])
    return list(dict.fromkeys(tags))


def _shot_types_for_reference_type(reference_type: str) -> list[str]:
    if reference_type in FULL_BODY_REFERENCE_TYPES:
        return ["full_body", "wide"]
    return ["close_up", "portrait"]


def _camera_angles_for_reference_type(reference_type: str) -> list[str]:
    angle_map = {
        "front": ["front"],
        "left_profile": ["profile_left", "left"],
        "right_profile": ["profile_right", "right"],
        "three_quarter_left": ["three_quarter_left", "left"],
        "three_quarter_right": ["three_quarter_right", "right"],
        "full_body_front": ["front"],
        "full_body_back": ["back", "back_view"],
        "seated_front": ["front"],
    }
    return angle_map.get(reference_type, [reference_type])


def _priority_for_reference_type(reference_type: str) -> int:
    priority_map = {
        "front": 10,
        "left_profile": 15,
        "right_profile": 16,
        "three_quarter_left": 20,
        "three_quarter_right": 25,
        "full_body_front": 30,
        "full_body_back": 32,
        "seated_front": 40,
    }
    return priority_map.get(reference_type, 100)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
