"""Scene blueprint loader."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from ai_film_studio.core.exceptions import MalformedConfigurationError, SceneFileError
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.prompt_compiler.errors import format_validation_error
from ai_film_studio.prompt_compiler.models import SceneBlueprint


class SceneBlueprintLoader:
    """Loads and validates scene blueprint YAML files."""

    def __init__(self, module_loader: ModuleLoader | None = None) -> None:
        self._module_loader = module_loader or ModuleLoader()

    def load(self, scene_file: Path) -> SceneBlueprint:
        """Load a scene blueprint from disk."""
        if not scene_file.exists():
            msg = f"Scene file '{scene_file}' does not exist."
            raise SceneFileError(msg)
        if not scene_file.is_file():
            msg = f"Scene path '{scene_file}' is not a file."
            raise SceneFileError(msg)

        data = self._module_loader.load_yaml_file(scene_file)
        try:
            return SceneBlueprint.model_validate(data)
        except ValidationError as exc:
            msg = format_validation_error(scene_file, exc, "scene blueprint")
            raise MalformedConfigurationError(msg) from exc
