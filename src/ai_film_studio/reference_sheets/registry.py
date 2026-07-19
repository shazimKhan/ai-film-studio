"""Reference sheet layout registry."""

from __future__ import annotations

from pathlib import Path

from ai_film_studio.core.exceptions import ReferenceSheetError
from ai_film_studio.reference_sheets.loader import ReferenceSheetLayoutLoader
from ai_film_studio.reference_sheets.models import ReferenceSheetLayout


class ReferenceSheetLayoutRegistry:
    """Resolves layout ids to reusable layout YAML files."""

    def __init__(
        self,
        *,
        repo_root: Path,
        templates_dir: Path | None = None,
        loader: ReferenceSheetLayoutLoader | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._templates_dir = templates_dir or Path("templates/reference_sheet_layouts")
        self._loader = loader or ReferenceSheetLayoutLoader()

    def get(self, layout_id: str) -> ReferenceSheetLayout:
        """Load a layout by stable id."""
        if not layout_id.strip():
            msg = "Reference sheet layout id cannot be empty."
            raise ReferenceSheetError(msg)
        if "/" in layout_id or "\\" in layout_id:
            msg = "Reference sheet layout id must not contain path separators."
            raise ReferenceSheetError(msg)

        layout_path = self._repo_root / self._templates_dir / f"{layout_id}.yaml"
        if not layout_path.is_file():
            msg = f"Reference sheet layout '{layout_id}' was not found at '{layout_path}'."
            raise ReferenceSheetError(msg)

        layout = self._loader.load_layout(layout_path)
        if layout.id != layout_id:
            msg = (
                f"Reference sheet layout file '{layout_path}' declares id "
                f"'{layout.id}', expected '{layout_id}'."
            )
            raise ReferenceSheetError(msg)
        return layout
