"""Reference review status updates."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from ai_film_studio.core.exceptions import ReferenceSheetError
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.reference_sheets.models import ReferenceStatus


class ReferenceApprovalService:
    """Approves and rejects extracted references in character assets."""

    def __init__(self, *, repo_root: Path, module_loader: ModuleLoader | None = None) -> None:
        self._repo_root = repo_root
        self._module_loader = module_loader or ModuleLoader()

    def approve(self, *, project: str, character: str, reference: str) -> Path:
        """Mark a reference as approved."""
        character_yaml, data, view = self._load_view(project, character, reference)
        view["status"] = ReferenceStatus.APPROVED.value
        view["approved"] = True
        view.pop("rejection_reason", None)
        self._write_character_yaml(character_yaml, data)
        return character_yaml

    def reject(self, *, project: str, character: str, reference: str, reason: str) -> Path:
        """Mark a reference as rejected with a human review reason."""
        if not reason.strip():
            msg = "A rejection reason is required."
            raise ReferenceSheetError(msg)
        character_yaml, data, view = self._load_view(project, character, reference)
        view["status"] = ReferenceStatus.REJECTED.value
        view["approved"] = False
        view["rejection_reason"] = reason.strip()
        self._write_character_yaml(character_yaml, data)
        return character_yaml

    def _load_view(
        self,
        project: str,
        character: str,
        reference: str,
    ) -> tuple[Path, dict[str, Any], dict[str, Any]]:
        character_yaml = (
            self._repo_root / "projects" / project / "characters" / character / "character.yaml"
        )
        if not character_yaml.is_file():
            msg = f"Character asset file '{character_yaml}' does not exist."
            raise ReferenceSheetError(msg)

        try:
            data = self._module_loader.load_yaml_file(character_yaml)
        except Exception as exc:
            msg = f"Could not load character asset '{character_yaml}': {exc}"
            raise ReferenceSheetError(msg) from exc

        reference_images = data.get("reference_images")
        if not isinstance(reference_images, dict):
            msg = f"Character '{character}' has no extracted reference images."
            raise ReferenceSheetError(msg)
        views = reference_images.get("views")
        if not isinstance(views, dict):
            msg = f"Character '{character}' has no extracted reference views."
            raise ReferenceSheetError(msg)
        view = views.get(reference)
        if not isinstance(view, dict):
            msg = f"Reference '{reference}' was not found for character '{character}'."
            raise ReferenceSheetError(msg)
        return character_yaml, data, view

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
