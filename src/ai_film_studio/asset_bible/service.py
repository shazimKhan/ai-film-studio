"""Asset bible validation service."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from ai_film_studio.asset_bible.models import AssetIndex, AssetValidationReport
from ai_film_studio.asset_bible.scanner import AssetBibleScanner
from ai_film_studio.core.exceptions import AssetBibleError


class AssetBibleService:
    """Validates project asset bibles and writes an asset index."""

    def __init__(self, scanner: AssetBibleScanner | None = None) -> None:
        self._scanner = scanner or AssetBibleScanner()

    def validate(self, project_root: Path, index_path: Path | None = None) -> AssetValidationReport:
        """Validate a project asset bible and write ``asset_index.json``."""
        if not project_root.exists():
            msg = f"Project root '{project_root}' does not exist."
            raise AssetBibleError(msg)
        if not project_root.is_dir():
            msg = f"Project root '{project_root}' is not a directory."
            raise AssetBibleError(msg)

        index, issues = self._scanner.scan(project_root)
        resolved_index_path = index_path or project_root / "asset_index.json"
        self._write_index(index, resolved_index_path)
        return AssetValidationReport(
            index_path=resolved_index_path.as_posix(),
            index=index,
            issues=issues,
        )

    @staticmethod
    def _write_index(index: AssetIndex, index_path: Path) -> None:
        try:
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(
                json.dumps(index.model_dump(), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except (OSError, TypeError, ValidationError) as exc:
            msg = f"Could not write asset index '{index_path}': {exc}"
            raise AssetBibleError(msg) from exc
