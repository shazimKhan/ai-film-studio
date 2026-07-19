"""Asset bible scanner and validator."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ai_film_studio.asset_bible.models import (
    AssetIndex,
    AssetRecord,
    AssetReferenceImage,
    AssetValidationIssue,
)
from ai_film_studio.asset_bible.standards import (
    CHARACTER_IMAGE_SLOTS,
    CHARACTER_REQUIRED_DIRS,
    CHARACTER_REQUIRED_FILES,
    ENVIRONMENT_IMAGE_SLOTS,
    ENVIRONMENT_REQUIRED_DIRS,
    ENVIRONMENT_REQUIRED_FILES,
    IMAGE_SUFFIXES,
    PROP_REQUIRED_DIRS,
    PROP_REQUIRED_FILES,
)
from ai_film_studio.module_loader import ModuleLoader


class AssetBibleScanner:
    """Scans a project asset bible into an index and validation issues."""

    def __init__(self, module_loader: ModuleLoader | None = None) -> None:
        self._module_loader = module_loader or ModuleLoader()

    def scan(self, project_root: Path) -> tuple[AssetIndex, tuple[AssetValidationIssue, ...]]:
        """Scan all supported asset types in a project root."""
        issues: list[AssetValidationIssue] = []
        characters = self._scan_assets(
            project_root=project_root,
            base_dir=project_root / "characters",
            asset_type="character",
            yaml_name="character.yaml",
            required_files=CHARACTER_REQUIRED_FILES,
            required_dirs=CHARACTER_REQUIRED_DIRS,
            image_slots=CHARACTER_IMAGE_SLOTS,
            issues=issues,
        )
        environments = self._scan_assets(
            project_root=project_root,
            base_dir=project_root / "environment",
            asset_type="environment",
            yaml_name="environment.yaml",
            required_files=ENVIRONMENT_REQUIRED_FILES,
            required_dirs=ENVIRONMENT_REQUIRED_DIRS,
            image_slots=ENVIRONMENT_IMAGE_SLOTS,
            issues=issues,
        )
        props = self._scan_assets(
            project_root=project_root,
            base_dir=project_root / "props",
            asset_type="prop",
            yaml_name="prop.yaml",
            required_files=PROP_REQUIRED_FILES,
            required_dirs=PROP_REQUIRED_DIRS,
            image_slots={},
            issues=issues,
            require_any_reference_image=True,
        )

        self._add_duplicate_id_issues(characters, "character", issues)
        self._add_duplicate_id_issues(environments, "environment", issues)
        self._add_duplicate_id_issues(props, "prop", issues)

        index = AssetIndex(
            project_root=self._relative(project_root, project_root),
            characters=tuple(characters),
            environments=tuple(environments),
            props=tuple(props),
        )
        return index, tuple(issues)

    def _scan_assets(
        self,
        *,
        project_root: Path,
        base_dir: Path,
        asset_type: str,
        yaml_name: str,
        required_files: tuple[str, ...],
        required_dirs: tuple[str, ...],
        image_slots: Mapping[str, tuple[str, ...]],
        issues: list[AssetValidationIssue],
        require_any_reference_image: bool = False,
    ) -> list[AssetRecord]:
        if not base_dir.exists():
            issues.append(
                self._issue(
                    "asset.missing_directory",
                    f"Missing {asset_type} asset directory.",
                    project_root,
                    base_dir,
                ),
            )
            return []

        records: list[AssetRecord] = []
        for asset_dir in sorted(path for path in base_dir.iterdir() if path.is_dir()):
            self._validate_required_files(asset_dir, required_files, project_root, issues)
            self._validate_required_dirs(asset_dir, required_dirs, project_root, issues)

            yaml_path = asset_dir / yaml_name
            data = self._load_yaml(yaml_path, project_root, issues)
            asset_id = str(data.get("id") or asset_dir.name) if data else asset_dir.name
            reference_status = (
                str(data.get("reference_status") or "awaiting_reference") if data else ""
            )
            if data is not None:
                self._validate_broken_paths(data, yaml_path.parent, project_root, issues)

            reference_images = self._reference_images(
                asset_dir,
                image_slots,
                project_root,
                issues,
            )
            if require_any_reference_image:
                reference_images = self._actual_reference_images(asset_dir, project_root)
                if not reference_images:
                    issues.append(
                        self._issue(
                            "asset.missing_image",
                            f"Prop asset '{asset_id}' has no reference images.",
                            project_root,
                            asset_dir / "references",
                        ),
                    )

            records.append(
                AssetRecord(
                    id=asset_id,
                    asset_type=asset_type,
                    path=self._relative(project_root, asset_dir),
                    yaml_path=self._optional_relative(project_root, yaml_path),
                    prompt_path=self._optional_relative(project_root, asset_dir / "prompt.md"),
                    notes_path=self._optional_relative(project_root, asset_dir / "notes.md"),
                    reference_status=reference_status or "missing",
                    reference_images=reference_images,
                ),
            )
        return records

    def _validate_required_files(
        self,
        asset_dir: Path,
        required_files: tuple[str, ...],
        project_root: Path,
        issues: list[AssetValidationIssue],
    ) -> None:
        for filename in required_files:
            path = asset_dir / filename
            if not path.is_file():
                issues.append(
                    self._issue(
                        _missing_file_code(filename),
                        f"Missing required file '{filename}'.",
                        project_root,
                        path,
                    ),
                )

    def _validate_required_dirs(
        self,
        asset_dir: Path,
        required_dirs: tuple[str, ...],
        project_root: Path,
        issues: list[AssetValidationIssue],
    ) -> None:
        for dirname in required_dirs:
            path = asset_dir / dirname
            if not path.is_dir():
                issues.append(
                    self._issue(
                        "asset.missing_directory",
                        f"Missing required directory '{dirname}'.",
                        project_root,
                        path,
                    ),
                )

    def _load_yaml(
        self,
        yaml_path: Path,
        project_root: Path,
        issues: list[AssetValidationIssue],
    ) -> dict[str, Any] | None:
        if not yaml_path.exists():
            return None
        try:
            return self._module_loader.load_yaml_file(yaml_path)
        except Exception as exc:
            issues.append(
                self._issue(
                    "asset.invalid_yaml",
                    f"Invalid YAML: {exc}",
                    project_root,
                    yaml_path,
                ),
            )
            return None

    def _reference_images(
        self,
        asset_dir: Path,
        image_slots: Mapping[str, tuple[str, ...]],
        project_root: Path,
        issues: list[AssetValidationIssue],
    ) -> tuple[AssetReferenceImage, ...]:
        images: list[AssetReferenceImage] = []
        for category, filenames in image_slots.items():
            for filename in filenames:
                path = asset_dir / category / filename
                exists = path.is_file()
                if not exists:
                    issues.append(
                        self._issue(
                            "asset.missing_image",
                            f"Missing reference image '{category}/{filename}'.",
                            project_root,
                            path,
                        ),
                    )
                images.append(
                    AssetReferenceImage(
                        category=category,
                        name=filename,
                        path=self._relative(project_root, path),
                        exists=exists,
                    ),
                )
        return tuple(images)

    def _actual_reference_images(
        self,
        asset_dir: Path,
        project_root: Path,
    ) -> tuple[AssetReferenceImage, ...]:
        reference_dir = asset_dir / "references"
        if not reference_dir.is_dir():
            return ()
        images = []
        for path in sorted(reference_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                images.append(
                    AssetReferenceImage(
                        category="references",
                        name=path.name,
                        path=self._relative(project_root, path),
                        exists=True,
                    ),
                )
        return tuple(images)

    def _validate_broken_paths(
        self,
        data: Mapping[str, Any],
        yaml_dir: Path,
        project_root: Path,
        issues: list[AssetValidationIssue],
    ) -> None:
        for raw_path in _iter_path_values(data):
            candidate = yaml_dir / raw_path
            if not candidate.exists():
                issues.append(
                    self._issue(
                        "asset.broken_path",
                        f"Configured path does not exist: {raw_path}",
                        project_root,
                        candidate,
                    ),
                )

    def _add_duplicate_id_issues(
        self,
        records: Iterable[AssetRecord],
        asset_type: str,
        issues: list[AssetValidationIssue],
    ) -> None:
        seen: dict[str, str] = {}
        for record in records:
            if record.id in seen:
                issues.append(
                    AssetValidationIssue(
                        code="asset.duplicate_id",
                        message=(
                            f"Duplicate {asset_type} asset id '{record.id}' also used by "
                            f"'{seen[record.id]}'."
                        ),
                        path=record.path,
                    ),
                )
            seen[record.id] = record.path

    def _issue(
        self,
        code: str,
        message: str,
        project_root: Path,
        path: Path,
    ) -> AssetValidationIssue:
        return AssetValidationIssue(
            code=code,
            message=message,
            path=self._relative(project_root, path),
        )

    def _optional_relative(self, project_root: Path, path: Path) -> str | None:
        if not path.exists():
            return None
        return self._relative(project_root, path)

    @staticmethod
    def _relative(project_root: Path, path: Path) -> str:
        try:
            return path.relative_to(project_root).as_posix()
        except ValueError:
            return path.as_posix()


def _iter_path_values(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if _is_path_key(key_text):
                yield from _coerce_path_values(item)
            yield from _iter_path_values(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _iter_path_values(item)


def _is_path_key(key: str) -> bool:
    return key in {"path", "paths"} or key.endswith(("_path", "_paths", "_file", "_files"))


def _coerce_path_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list | tuple):
        for item in value:
            if isinstance(item, str):
                yield item


def _missing_file_code(filename: str) -> str:
    if filename.endswith((".yaml", ".yml")):
        return "asset.missing_yaml"
    if filename == "prompt.md":
        return "asset.missing_prompt"
    if filename == "notes.md":
        return "asset.missing_notes"
    return "asset.missing_file"
