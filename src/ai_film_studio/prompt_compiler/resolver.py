"""Reusable module reference resolution for scene blueprints."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from ai_film_studio.asset_bible import IdentityLockService
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
        self._identity_locks = IdentityLockService(
            repo_root=self._repo_root,
            module_loader=self._module_loader,
        )

    def resolve(self, scene: SceneBlueprint, scene_file: Path) -> ResolvedSceneContext:
        """Resolve all reusable modules referenced by a scene blueprint."""
        scene_dir = scene_file.parent
        identity_project_root = self._identity_project_root(scene.project, scene_file)
        characters = tuple(
            self._resolve_character(reference, scene_dir, identity_project_root)
            for reference in scene.characters
        )
        world = self._resolve_world(scene.world, scene_dir)
        return ResolvedSceneContext(scene=scene, characters=characters, world=world)

    def _resolve_character(
        self,
        reference: CharacterReference,
        scene_dir: Path,
        identity_project_root: Path,
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

        identity = self._identity_locks.try_load_identity(identity_project_root, reference.id)
        if identity is None and asset.identity_locked:
            msg = (
                f"Character asset '{asset.id}' is identity_locked but no identity.yaml exists "
                f"under '{identity_project_root / '05_characters' / reference.id}'."
            )
            raise AssetNotFoundError(msg)
        if identity is None and reference.state:
            msg = (
                f"Character reference '{reference.id}' requested state "
                f"'{reference.state}' but no identity exists."
            )
            raise AssetNotFoundError(msg)

        state = self._identity_locks.resolve_state(identity, reference.state) if identity else None
        return ResolvedCharacterReference(
            reference=reference,
            asset=asset,
            identity=identity,
            state=state,
        )

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

    def _identity_project_root(self, project_id: str, scene_file: Path) -> Path:
        project_root = self._repo_root / "projects" / project_id
        if project_root.exists():
            return project_root

        parts = scene_file.resolve().parts
        try:
            projects_index = parts.index("projects")
            if parts[projects_index + 1] == project_id:
                return Path(*parts[: projects_index + 2])
        except (ValueError, IndexError):
            pass

        return self._repo_root
