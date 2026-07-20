"""Scene-level reference selection integration service."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from ai_film_studio.builder.runtime import StudioRuntime
from ai_film_studio.core.exceptions import AdapterRegistrationError, ReferenceSheetError
from ai_film_studio.engine_adapters.registry import EngineAdapterRegistry
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.reference_sheets.inventory import ReferenceInventoryService
from ai_film_studio.reference_sheets.models import (
    ReferenceImageValidation,
    ReferenceSelectionRequest,
    ReferenceSelectionResult,
    ReferenceSelectionScene,
    SceneReferenceSelectionArtifact,
)
from ai_film_studio.reference_sheets.selector import ReferenceSelector


class ReferenceSelectionService:
    """Compiles selector test scenes into generation manifests with local references."""

    def __init__(
        self,
        *,
        repo_root: Path,
        engine_adapters: EngineAdapterRegistry,
        module_loader: ModuleLoader | None = None,
        selector: ReferenceSelector | None = None,
        inventory: ReferenceInventoryService | None = None,
        output_root: Path = Path("output"),
    ) -> None:
        self._repo_root = repo_root
        self._engine_adapters = engine_adapters
        self._module_loader = module_loader or ModuleLoader()
        self._selector = selector or ReferenceSelector(self._module_loader)
        self._inventory = inventory or ReferenceInventoryService(
            repo_root=repo_root,
            module_loader=self._module_loader,
        )
        self._output_root = output_root

    @classmethod
    def from_runtime(
        cls,
        runtime: StudioRuntime,
        *,
        repo_root: Path,
        output_root: Path = Path("output"),
    ) -> ReferenceSelectionService:
        """Create the service from a built framework runtime."""
        return cls(
            repo_root=repo_root,
            engine_adapters=runtime.engine_adapters,
            module_loader=runtime.module_loader,
            output_root=output_root,
        )

    def compile_scene(
        self,
        scene_file: Path,
        *,
        engine: str,
        allow_weak_fallbacks: bool = False,
        allow_preview_references: bool = False,
    ) -> SceneReferenceSelectionArtifact:
        """Run reference selection for a scene file and write its generation manifest."""
        resolved_scene_file = self._resolve_repo_path(scene_file)
        scene = self._load_scene(resolved_scene_file)
        try:
            adapter = self._engine_adapters.get(engine)
        except AdapterRegistrationError as exc:
            msg = f"Engine adapter '{engine}' is not registered."
            raise ReferenceSheetError(msg) from exc

        capabilities = adapter.reference_capabilities
        request = ReferenceSelectionRequest(
            camera_shot_type=scene.camera.shot_type,
            angle=scene.camera.angle,
            framing=scene.camera.framing,
            pose=scene.camera.pose,
            action=scene.action,
            approved_only=True,
            engine_reference_limit=capabilities.max_character_reference_images,
            preferred_reference_types=capabilities.preferred_reference_types,
            allow_weak_fallbacks=allow_weak_fallbacks,
            allow_preview_references=allow_preview_references,
        )
        character_yaml = (
            self._repo_root
            / "projects"
            / scene.project
            / "characters"
            / scene.character
            / "character.yaml"
        )
        result = self._selector.explain_from_yaml(character_yaml, request)
        validations = self._inventory.validate_character(
            project=scene.project,
            character=scene.character,
        )
        output_path = self._output_path(scene, resolved_scene_file)
        manifest = self._manifest(
            scene=scene,
            scene_file=resolved_scene_file,
            engine=engine,
            result=result,
            validations=validations,
            output_path=output_path,
        )
        self._write_manifest(manifest, output_path)
        return SceneReferenceSelectionArtifact(
            scene_file=self._repo_relative(resolved_scene_file),
            output_path=self._repo_relative(output_path),
            result=result,
            validations=validations,
        )

    def _load_scene(self, scene_file: Path) -> ReferenceSelectionScene:
        if not scene_file.is_file():
            msg = f"Reference selection scene file '{scene_file}' does not exist."
            raise ReferenceSheetError(msg)
        try:
            data = self._module_loader.load_yaml_file(scene_file)
            return ReferenceSelectionScene.model_validate(data)
        except ValidationError as exc:
            msg = f"Invalid reference selection scene '{scene_file}': {exc}"
            raise ReferenceSheetError(msg) from exc
        except Exception as exc:
            msg = f"Could not load reference selection scene '{scene_file}': {exc}"
            raise ReferenceSheetError(msg) from exc

    def _output_path(self, scene: ReferenceSelectionScene, scene_file: Path) -> Path:
        return (
            self._repo_root
            / self._output_root
            / scene.project
            / "reference_selection"
            / scene_file.stem
            / "generation_manifest.json"
        )

    def _manifest(
        self,
        *,
        scene: ReferenceSelectionScene,
        scene_file: Path,
        engine: str,
        result: ReferenceSelectionResult,
        validations: tuple[ReferenceImageValidation, ...],
        output_path: Path,
    ) -> dict[str, object]:
        return {
            "project": scene.project,
            "character_id": scene.character,
            "title": scene.title,
            "scene_file": self._repo_relative(scene_file),
            "engine": engine,
            "generated_at": datetime.now(UTC).isoformat(),
            "output_path": self._repo_relative(output_path),
            "selector_inputs": result.selector_inputs.model_dump(mode="json"),
            "engine_reference_limit": result.engine_reference_limit,
            "allow_weak_fallbacks": result.allow_weak_fallbacks,
            "allow_preview_references": result.selector_inputs.allow_preview_references,
            "expected_reference": scene.expected_reference,
            "primary_reference": result.selected[0].name if result.selected else None,
            "selected_references": [
                {
                    "name": reference.name,
                    "path": reference.path,
                    "score": reference.score,
                    "reason": reference.reason,
                    "source_type": (
                        reference.source_type.value if reference.source_type is not None else None
                    ),
                    "production_selectable": reference.production_selectable,
                    "priority": reference.priority,
                    "tags": list(reference.tags),
                    "status": reference.status.value,
                }
                for reference in result.selected
            ],
            "excluded_references": [
                {
                    "name": reference.name,
                    "path": reference.path,
                    "reason": reference.reason,
                    "source_type": (
                        reference.source_type.value if reference.source_type is not None else None
                    ),
                    "production_selectable": reference.production_selectable,
                    "score": reference.score,
                    "status": reference.status.value,
                    "tags": list(reference.tags),
                }
                for reference in result.excluded
            ],
            "reference_validation": [
                {
                    "name": validation.name,
                    "path": validation.path,
                    "valid": validation.is_valid,
                    "exists": validation.exists,
                    "readable": validation.readable,
                    "width": validation.width,
                    "height": validation.height,
                    "checksum": validation.checksum,
                    "checksum_matches": validation.checksum_matches,
                    "source_type": (
                        validation.source_type.value if validation.source_type is not None else None
                    ),
                    "source_type_valid": validation.source_type_valid,
                    "production_selectable": validation.production_selectable,
                    "duplicate_path": validation.duplicate_path,
                    "min_width": validation.min_width,
                    "min_height": validation.min_height,
                    "status": validation.status.value,
                    "approved": validation.approved,
                    "reason": validation.reason,
                }
                for validation in validations
            ],
            "verification": {
                "expected_first_reference": scene.expected_reference,
                "actual_first_reference": result.selected[0].name if result.selected else None,
                "matches_expected": (
                    bool(result.selected)
                    and scene.expected_reference is not None
                    and result.selected[0].name == scene.expected_reference
                ),
            },
        }

    def _write_manifest(self, manifest: dict[str, object], output_path: Path) -> None:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            msg = f"Could not write generation manifest '{output_path}': {exc}"
            raise ReferenceSheetError(msg) from exc

    def _resolve_repo_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return self._repo_root / path

    def _repo_relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self._repo_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()
