"""Deterministic reference sheet splitter using Pillow."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw, UnidentifiedImageError
from pydantic import ValidationError

from ai_film_studio.core.exceptions import ReferenceSheetError
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.reference_sheets.loader import ReferenceSheetLayoutLoader
from ai_film_studio.reference_sheets.models import (
    GeneratedReference,
    PixelCrop,
    ReferenceOutputFormat,
    ReferenceSheetSplitResult,
    ReferenceStatus,
    SplitOptions,
)
from ai_film_studio.reference_sheets.registry import ReferenceSheetLayoutRegistry
from ai_film_studio.reference_sheets.validator import ReferenceSheetValidator

MASTER_SHEET_FILENAME = "master_sheet.png"
PREVIEW_FILENAME = "master_sheet_preview.png"
MANIFEST_FILENAME = "reference_sheet_manifest.json"


class ReferenceSheetSplitter:
    """Splits manually generated reference sheets by deterministic layout templates."""

    def __init__(
        self,
        *,
        repo_root: Path,
        registry: ReferenceSheetLayoutRegistry | None = None,
        layout_loader: ReferenceSheetLayoutLoader | None = None,
        validator: ReferenceSheetValidator | None = None,
        module_loader: ModuleLoader | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._registry = registry or ReferenceSheetLayoutRegistry(repo_root=repo_root)
        self._layout_loader = layout_loader or ReferenceSheetLayoutLoader()
        self._validator = validator or ReferenceSheetValidator()
        self._module_loader = module_loader or ModuleLoader()

    def split(
        self,
        image_path: Path,
        *,
        project: str,
        character: str,
        layout_id: str,
        options: SplitOptions | None = None,
        overrides_path: Path | None = None,
    ) -> ReferenceSheetSplitResult:
        """Split a reference sheet into validated view images."""
        resolved_options = options or SplitOptions()
        source_path = self._resolve_repo_path(image_path)
        self._validator.validate_source_path(source_path)

        layout = self._registry.get(layout_id)
        overrides = self._layout_loader.load_overrides(
            self._resolve_repo_path(overrides_path) if overrides_path is not None else None,
        )
        character_dir = self._character_dir(project, character)
        character_yaml = character_dir / "character.yaml"
        if not character_yaml.is_file():
            msg = f"Character asset file '{character_yaml}' does not exist."
            raise ReferenceSheetError(msg)

        references_dir = character_dir / "references"
        master_dir = references_dir / "master"
        views_dir = references_dir / "views"
        master_sheet_path = master_dir / MASTER_SHEET_FILENAME
        preview_path = master_dir / PREVIEW_FILENAME
        manifest_path = references_dir / MANIFEST_FILENAME

        source_checksum = _sha256(source_path)
        source_width, source_height = self._read_source_dimensions(source_path)
        output_paths = {
            panel.name: self._resolve_output_path(
                views_dir=views_dir,
                output_filename=panel.output_filename,
                output_format=resolved_options.output_format,
                overwrite=resolved_options.overwrite,
            )
            for panel in layout.panels
        }
        planned_crops = self._validator.build_crop_plan(
            layout=layout,
            overrides=overrides.panels,
            image_width=source_width,
            image_height=source_height,
            output_paths=output_paths,
            options=resolved_options,
        )

        if resolved_options.dry_run:
            return ReferenceSheetSplitResult(
                project=project,
                character=character,
                layout_id=layout_id,
                source_image=self._repo_relative(source_path),
                source_checksum=source_checksum,
                source_width=source_width,
                source_height=source_height,
                preview_path=self._repo_relative(preview_path),
                planned_crops=planned_crops,
                dry_run=True,
            )

        master_dir.mkdir(parents=True, exist_ok=True)
        views_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_master_copy(
            source_path=source_path,
            master_sheet_path=master_sheet_path,
            source_checksum=source_checksum,
        )

        generated = self._write_crops(
            source_path=source_path,
            planned_crops=planned_crops,
            output_format=resolved_options.output_format,
        )
        self._write_preview(
            source_path=source_path,
            output_path=preview_path,
            planned_crops=planned_crops,
            source_width=source_width,
            source_height=source_height,
        )

        manifest = self._build_manifest(
            project=project,
            character=character,
            layout_id=layout_id,
            source_path=master_sheet_path,
            original_source_path=source_path,
            source_checksum=_sha256(master_sheet_path),
            source_width=source_width,
            source_height=source_height,
            preview_path=preview_path,
            output_format=resolved_options.output_format,
            generated=generated,
        )
        self._write_manifest(manifest, manifest_path)
        self._update_character_yaml(
            character_yaml=character_yaml,
            master_sheet_path=master_sheet_path,
            manifest_path=manifest_path,
            layout_id=layout_id,
            source_checksum=_sha256(master_sheet_path),
            generated=generated,
        )

        return ReferenceSheetSplitResult(
            project=project,
            character=character,
            layout_id=layout_id,
            source_image=self._repo_relative(master_sheet_path),
            source_checksum=_sha256(master_sheet_path),
            source_width=source_width,
            source_height=source_height,
            preview_path=self._repo_relative(preview_path),
            manifest_path=self._repo_relative(manifest_path),
            generated_files=generated,
            planned_crops=planned_crops,
        )

    def preview(
        self,
        image_path: Path,
        *,
        project: str,
        character: str,
        layout_id: str,
        options: SplitOptions | None = None,
        overrides_path: Path | None = None,
    ) -> ReferenceSheetSplitResult:
        """Generate a crop preview without writing split crop images."""
        preview_options = (options or SplitOptions()).model_copy(update={"dry_run": True})
        plan = self.split(
            image_path,
            project=project,
            character=character,
            layout_id=layout_id,
            options=preview_options,
            overrides_path=overrides_path,
        )
        source_path = self._resolve_repo_path(image_path)
        character_dir = self._character_dir(project, character)
        preview_path = character_dir / "references" / "master" / PREVIEW_FILENAME
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_preview(
            source_path=source_path,
            output_path=preview_path,
            planned_crops=plan.planned_crops,
            source_width=plan.source_width,
            source_height=plan.source_height,
        )
        return plan.model_copy(update={"preview_path": self._repo_relative(preview_path)})

    def _read_source_dimensions(self, source_path: Path) -> tuple[int, int]:
        try:
            with Image.open(source_path) as image:
                width, height = image.size
        except UnidentifiedImageError as exc:
            msg = f"Reference sheet source image '{source_path}' is not a readable image."
            raise ReferenceSheetError(msg) from exc
        except OSError as exc:
            msg = f"Could not read source image '{source_path}': {exc}"
            raise ReferenceSheetError(msg) from exc

        if width <= 0 or height <= 0:
            msg = f"Reference sheet source image '{source_path}' has invalid dimensions."
            raise ReferenceSheetError(msg)
        return width, height

    def _write_crops(
        self,
        *,
        source_path: Path,
        planned_crops: tuple[Any, ...],
        output_format: ReferenceOutputFormat,
    ) -> tuple[GeneratedReference, ...]:
        generated: list[GeneratedReference] = []
        try:
            with Image.open(source_path) as source:
                for planned in planned_crops:
                    output_path = Path(planned.output_path)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    box = (
                        planned.pixel_crop.left,
                        planned.pixel_crop.top,
                        planned.pixel_crop.right,
                        planned.pixel_crop.bottom,
                    )
                    crop_image = source.crop(box)
                    if output_format == ReferenceOutputFormat.JPG and crop_image.mode != "RGB":
                        crop_image = crop_image.convert("RGB")
                    self._save_crop(crop_image, output_path, output_format)
                    self._validate_generated_image(output_path, planned.pixel_crop)
                    generated.append(
                        GeneratedReference(
                            name=planned.panel.name,
                            path=self._repo_relative(output_path),
                            normalized_crop=planned.normalized_crop,
                            pixel_crop=planned.pixel_crop,
                            width=planned.width,
                            height=planned.height,
                            tags=planned.panel.tags,
                            shot_types=planned.panel.shot_types,
                            camera_angles=planned.panel.camera_angles,
                            priority=planned.panel.priority,
                            checksum=_sha256(output_path),
                        ),
                    )
        except ReferenceSheetError:
            raise
        except OSError as exc:
            msg = f"Could not write reference crops: {exc}"
            raise ReferenceSheetError(msg) from exc
        return tuple(generated)

    def _write_preview(
        self,
        *,
        source_path: Path,
        output_path: Path,
        planned_crops: tuple[Any, ...],
        source_width: int,
        source_height: int,
    ) -> None:
        try:
            with Image.open(source_path) as source:
                preview = source.convert("RGBA")
                draw = ImageDraw.Draw(preview)
                for index, planned in enumerate(planned_crops, start=1):
                    color = _preview_color(index)
                    box = (
                        planned.pixel_crop.left,
                        planned.pixel_crop.top,
                        planned.pixel_crop.right,
                        planned.pixel_crop.bottom,
                    )
                    draw.rectangle(box, outline=color, width=max(3, source_width // 320))
                    label = f"{planned.panel.name} ({planned.width}x{planned.height})"
                    label_box = (
                        planned.pixel_crop.left + 4,
                        planned.pixel_crop.top + 4,
                        planned.pixel_crop.left + 8 + (len(label) * 7),
                        planned.pixel_crop.top + 24,
                    )
                    draw.rectangle(label_box, fill=(0, 0, 0, 180))
                    draw.text(
                        (planned.pixel_crop.left + 8, planned.pixel_crop.top + 7),
                        label,
                        fill=(255, 255, 255, 255),
                    )
                dimensions_label = f"source: {source_width}x{source_height}"
                draw.rectangle((4, 4, 190, 28), fill=(0, 0, 0, 180))
                draw.text((10, 9), dimensions_label, fill=(255, 255, 255, 255))
                output_path.parent.mkdir(parents=True, exist_ok=True)
                preview.save(output_path, format="PNG", compress_level=6)
        except OSError as exc:
            msg = f"Could not write crop preview '{output_path}': {exc}"
            raise ReferenceSheetError(msg) from exc

    def _save_crop(
        self,
        crop_image: Any,
        output_path: Path,
        output_format: ReferenceOutputFormat,
    ) -> None:
        if output_format == ReferenceOutputFormat.PNG:
            crop_image.save(output_path, format="PNG", compress_level=0)
            return
        if output_format == ReferenceOutputFormat.JPG:
            crop_image.save(output_path, format="JPEG", quality=95, subsampling=0)
            return
        if output_format == ReferenceOutputFormat.WEBP:
            crop_image.save(output_path, format="WEBP", lossless=True)
            return

        msg = f"Unsupported output format '{output_format}'."
        raise ReferenceSheetError(msg)

    def _validate_generated_image(self, output_path: Path, expected_crop: PixelCrop) -> None:
        try:
            with Image.open(output_path) as generated:
                width, height = generated.size
                generated.verify()
        except OSError as exc:
            msg = f"Generated file '{output_path}' is not readable: {exc}"
            raise ReferenceSheetError(msg) from exc

        if width != expected_crop.width or height != expected_crop.height:
            msg = (
                f"Generated file '{output_path}' has dimensions {width}x{height}, "
                f"expected {expected_crop.width}x{expected_crop.height}."
            )
            raise ReferenceSheetError(msg)

    def _build_manifest(
        self,
        *,
        project: str,
        character: str,
        layout_id: str,
        source_path: Path,
        original_source_path: Path,
        source_checksum: str,
        source_width: int,
        source_height: int,
        preview_path: Path,
        output_format: ReferenceOutputFormat,
        generated: tuple[GeneratedReference, ...],
    ) -> dict[str, Any]:
        return {
            "project": project,
            "character": character,
            "layout_id": layout_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "source_image": self._repo_relative(source_path),
            "original_source_image": self._repo_relative(original_source_path),
            "source_dimensions": {"width": source_width, "height": source_height},
            "source_checksum": source_checksum,
            "output_format": output_format.value,
            "preview_path": self._repo_relative(preview_path),
            "panel_count": len(generated),
            "generated_files": [
                {
                    "name": reference.name,
                    "path": reference.path,
                    "normalized_crop": reference.normalized_crop.model_dump(mode="json"),
                    "pixel_crop": reference.pixel_crop.model_dump(mode="json"),
                    "dimensions": {"width": reference.width, "height": reference.height},
                    "tags": list(reference.tags),
                    "shot_types": list(reference.shot_types),
                    "camera_angles": list(reference.camera_angles),
                    "priority": reference.priority,
                    "validation_status": reference.validation_status.value,
                    "checksum": reference.checksum,
                }
                for reference in generated
            ],
            "checksums": {
                "source": source_checksum,
                "crops": {reference.name: reference.checksum for reference in generated},
            },
        }

    def _write_manifest(self, manifest: dict[str, Any], manifest_path: Path) -> None:
        try:
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            msg = f"Could not write reference manifest '{manifest_path}': {exc}"
            raise ReferenceSheetError(msg) from exc

    def _update_character_yaml(
        self,
        *,
        character_yaml: Path,
        master_sheet_path: Path,
        manifest_path: Path,
        layout_id: str,
        source_checksum: str,
        generated: tuple[GeneratedReference, ...],
    ) -> None:
        try:
            data = self._module_loader.load_yaml_file(character_yaml)
        except Exception as exc:
            msg = f"Could not load character asset '{character_yaml}': {exc}"
            raise ReferenceSheetError(msg) from exc

        backup_path = character_yaml.with_suffix(character_yaml.suffix + ".bak")
        try:
            shutil.copy2(character_yaml, backup_path)
        except OSError as exc:
            msg = f"Could not create character asset backup '{backup_path}': {exc}"
            raise ReferenceSheetError(msg) from exc

        reference_images = _ensure_mapping(data, "reference_images")
        reference_images["master_sheet"] = {
            "path": _relative_to(character_yaml.parent, master_sheet_path),
            "manifest_path": _relative_to(character_yaml.parent, manifest_path),
            "layout_id": layout_id,
            "checksum": source_checksum,
            "approved": False,
            "status": ReferenceStatus.PENDING_REVIEW.value,
        }
        views = _ensure_mapping(reference_images, "views")
        for reference in generated:
            output_path = self._repo_root / reference.path
            views[reference.name] = {
                "path": _relative_to(character_yaml.parent, output_path),
                "tags": list(reference.tags),
                "shot_types": list(reference.shot_types),
                "camera_angles": list(reference.camera_angles),
                "priority": reference.priority,
                "approved": False,
                "status": ReferenceStatus.PENDING_REVIEW.value,
                "width": reference.width,
                "height": reference.height,
                "checksum": reference.checksum,
            }

        try:
            character_yaml.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        except (OSError, ValidationError) as exc:
            msg = f"Could not update character asset '{character_yaml}': {exc}"
            raise ReferenceSheetError(msg) from exc

    def _ensure_master_copy(
        self,
        *,
        source_path: Path,
        master_sheet_path: Path,
        source_checksum: str,
    ) -> None:
        if source_path.resolve() == master_sheet_path.resolve():
            return
        if master_sheet_path.exists():
            if _sha256(master_sheet_path) == source_checksum:
                return
            msg = (
                f"Master sheet '{master_sheet_path}' already exists with different content. "
                "Refusing to overwrite the preserved original."
            )
            raise ReferenceSheetError(msg)
        try:
            shutil.copy2(source_path, master_sheet_path)
        except OSError as exc:
            msg = f"Could not preserve master sheet at '{master_sheet_path}': {exc}"
            raise ReferenceSheetError(msg) from exc

    def _resolve_output_path(
        self,
        *,
        views_dir: Path,
        output_filename: str,
        output_format: ReferenceOutputFormat,
        overwrite: bool,
    ) -> Path:
        stem = Path(output_filename).stem
        base_path = views_dir / f"{stem}.{output_format.value}"
        if overwrite or not base_path.exists():
            return base_path

        version = 2
        while True:
            candidate = views_dir / f"{stem}_v{version}.{output_format.value}"
            if not candidate.exists():
                return candidate
            version += 1

    def _character_dir(self, project: str, character: str) -> Path:
        if not project.strip() or not character.strip():
            msg = "Project and character ids are required."
            raise ReferenceSheetError(msg)
        return self._repo_root / "projects" / project / "characters" / character

    def _resolve_repo_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return self._repo_root / path

    def _repo_relative(self, path: Path) -> str:
        return _relative_to(self._repo_root, path)


def _ensure_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if value is None:
        nested: dict[str, Any] = {}
        data[key] = nested
        return nested
    if not isinstance(value, dict):
        msg = f"Expected '{key}' to be a mapping in character asset YAML."
        raise ReferenceSheetError(msg)
    return value


def _relative_to(base: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _preview_color(index: int) -> tuple[int, int, int, int]:
    palette = (
        (255, 64, 64, 255),
        (64, 180, 255, 255),
        (255, 196, 64, 255),
        (96, 220, 140, 255),
        (220, 96, 255, 255),
        (255, 128, 64, 255),
        (80, 255, 220, 255),
        (255, 96, 160, 255),
    )
    return palette[(index - 1) % len(palette)]
