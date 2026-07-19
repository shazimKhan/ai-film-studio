"""Load reusable reference sheet layouts and manual crop overrides."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from ai_film_studio.core.exceptions import ReferenceSheetError
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.reference_sheets.models import CropOverrideSet, ReferenceSheetLayout


class ReferenceSheetLayoutLoader:
    """Loads reference sheet YAML definitions into typed layout models."""

    def __init__(self, module_loader: ModuleLoader | None = None) -> None:
        self._module_loader = module_loader or ModuleLoader()

    def load_layout(self, layout_path: Path) -> ReferenceSheetLayout:
        """Load and validate a reference sheet layout YAML file."""
        try:
            data = self._module_loader.load_yaml_file(layout_path)
            return ReferenceSheetLayout.model_validate(data)
        except ValidationError as exc:
            msg = f"Invalid reference sheet layout '{layout_path}': {exc}"
            raise ReferenceSheetError(msg) from exc
        except ReferenceSheetError:
            raise
        except Exception as exc:
            msg = f"Could not load reference sheet layout '{layout_path}': {exc}"
            raise ReferenceSheetError(msg) from exc

    def load_overrides(self, overrides_path: Path | None) -> CropOverrideSet:
        """Load optional manual crop overrides."""
        if overrides_path is None:
            return CropOverrideSet()
        try:
            data = self._module_loader.load_yaml_file(overrides_path)
            return CropOverrideSet.model_validate(data)
        except ValidationError as exc:
            msg = f"Invalid crop overrides '{overrides_path}': {exc}"
            raise ReferenceSheetError(msg) from exc
        except Exception as exc:
            msg = f"Could not load crop overrides '{overrides_path}': {exc}"
            raise ReferenceSheetError(msg) from exc
