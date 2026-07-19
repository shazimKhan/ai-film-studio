"""Reference image inventory validation and guarded approval."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, UnidentifiedImageError

from ai_film_studio.core.exceptions import ReferenceSheetError
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.reference_sheets.models import (
    ReferenceImageValidation,
    ReferenceStatus,
)


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
        """Validate all mapped reference views for a character."""
        character_yaml = self._character_yaml(project, character)
        data = self._load_character(character_yaml)
        views = self._views(data, character)
        return tuple(
            self._validate_view(character_yaml.parent, name, raw_view)
            for name, raw_view in sorted(views.items())
            if isinstance(raw_view, dict)
        )

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
        views = self._views(data, character)
        raw_view = views.get(reference)
        if not isinstance(raw_view, dict):
            msg = f"Reference '{reference}' was not found for character '{character}'."
            raise ReferenceSheetError(msg)
        return self._validate_view(character_yaml.parent, reference, raw_view)

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
        views = self._views(data, character)
        validations: list[ReferenceImageValidation] = []
        changed = False
        for reference in references:
            raw_view = views.get(reference)
            if not isinstance(raw_view, dict):
                validations.append(
                    ReferenceImageValidation(
                        name=reference,
                        exists=False,
                        readable=False,
                        reason="reference is missing from character.yaml",
                    ),
                )
                continue

            validation = self._validate_view(character_yaml.parent, reference, raw_view)
            validations.append(validation)
            if not validation.is_valid:
                continue
            raw_view["status"] = ReferenceStatus.APPROVED.value
            raw_view["approved"] = True
            raw_view.pop("rejection_reason", None)
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
    ) -> ReferenceImageValidation:
        path_value = raw_view.get("path")
        status = _status(raw_view)
        if not isinstance(path_value, str) or not path_value.strip():
            return ReferenceImageValidation(
                name=name,
                exists=False,
                readable=False,
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
            status=status,
            approved=raw_view.get("approved") is True,
            reason=reason,
        )

    def _sync_manifest_statuses(self, character_yaml: Path, data: dict[str, Any]) -> None:
        reference_images = data.get("reference_images")
        if not isinstance(reference_images, dict):
            return
        master_sheet = reference_images.get("master_sheet")
        views = reference_images.get("views")
        if not isinstance(master_sheet, dict) or not isinstance(views, dict):
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
            raw_view = views.get(name)
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

    def _views(self, data: dict[str, Any], character: str) -> dict[str, Any]:
        reference_images = data.get("reference_images")
        if not isinstance(reference_images, dict):
            msg = f"Character '{character}' has no extracted reference images."
            raise ReferenceSheetError(msg)
        views = reference_images.get("views")
        if not isinstance(views, dict):
            msg = f"Character '{character}' has no extracted reference views."
            raise ReferenceSheetError(msg)
        return views

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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
