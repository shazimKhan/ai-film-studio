"""Reusable module reference resolution for scene blueprints."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from ai_film_studio.core.exceptions import AssetNotFoundError, MalformedConfigurationError
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.prompt_compiler.errors import format_validation_error
from ai_film_studio.prompt_compiler.models import (
    CharacterAsset,
    CharacterReference,
    ResolvedCharacterReference,
    ResolvedSceneContext,
    ResolvedWorldReference,
    SceneBlueprint,
    WorldAsset,
    WorldReference,
)


class ModuleReferenceResolver:
    """Resolves scene references to reusable YAML or Markdown modules."""

    def __init__(
        self,
        module_loader: ModuleLoader | None = None,
        *,
        repo_root: Path | None = None,
    ) -> None:
        self._module_loader = module_loader or ModuleLoader()
        self._repo_root = repo_root or Path.cwd()

    def resolve(self, scene: SceneBlueprint, scene_file: Path) -> ResolvedSceneContext:
        """Resolve all reusable modules referenced by a scene blueprint."""
        scene_dir = scene_file.parent
        characters = tuple(
            self._resolve_character(reference, scene_dir) for reference in scene.characters
        )
        world = self._resolve_world(scene.world, scene_dir)
        return ResolvedSceneContext(scene=scene, characters=characters, world=world)

    def _resolve_character(
        self,
        reference: CharacterReference,
        scene_dir: Path,
    ) -> ResolvedCharacterReference:
        path = self._resolve_asset_path(
            reference.module,
            scene_dir,
            asset_label=f"Character asset '{reference.id}'",
        )
        module = self._module_loader.load_data_module(path)
        if not isinstance(module.data, dict):
            msg = f"Character asset '{path}' must be a YAML mapping."
            raise MalformedConfigurationError(msg)

        try:
            asset = CharacterAsset.model_validate(module.data)
        except ValidationError as exc:
            msg = format_validation_error(path, exc, "character asset")
            raise MalformedConfigurationError(msg) from exc
        if asset.id != reference.id:
            msg = (
                f"Character reference '{reference.id}' resolved to asset "
                f"'{asset.id}' in '{path}'."
            )
            raise MalformedConfigurationError(msg)
        return ResolvedCharacterReference(reference=reference, asset=asset)

    def _resolve_world(
        self,
        reference: WorldReference,
        scene_dir: Path,
    ) -> ResolvedWorldReference:
        path = self._resolve_asset_path(
            reference.module,
            scene_dir,
            asset_label=f"World asset '{reference.id}'",
        )
        module = self._module_loader.load_data_module(path)
        if not isinstance(module.data, dict):
            msg = f"World asset '{path}' must be a YAML mapping."
            raise MalformedConfigurationError(msg)

        try:
            asset = WorldAsset.model_validate(module.data)
        except ValidationError as exc:
            msg = format_validation_error(path, exc, "world asset")
            raise MalformedConfigurationError(msg) from exc
        if asset.id != reference.id:
            msg = f"World reference '{reference.id}' resolved to asset '{asset.id}' in '{path}'."
            raise MalformedConfigurationError(msg)
        return ResolvedWorldReference(reference=reference, asset=asset)

    def _resolve_asset_path(self, module_path: Path, scene_dir: Path, *, asset_label: str) -> Path:
        candidates = self._candidate_paths(module_path, scene_dir)
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        looked_for = ", ".join(str(candidate) for candidate in candidates)
        msg = f"{asset_label} not found. Looked for: {looked_for}"
        raise AssetNotFoundError(msg)

    def _candidate_paths(self, module_path: Path, scene_dir: Path) -> tuple[Path, ...]:
        if module_path.is_absolute():
            return (module_path,)

        scene_relative = scene_dir / module_path
        root_relative = self._repo_root / module_path
        if scene_relative == root_relative:
            return (scene_relative,)
        return (scene_relative, root_relative)
