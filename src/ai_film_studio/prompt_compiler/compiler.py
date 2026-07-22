"""Prompt compiler implementation."""

from __future__ import annotations

from typing import Any

from ai_film_studio.prompt_compiler.base import BasePromptCompiler
from ai_film_studio.prompt_compiler.models import (
    PromptCompilationRequest,
    PromptCompilationResult,
    ResolvedSceneContext,
)
from ai_film_studio.prompt_compiler.sections import PromptSectionBuilder


class PromptCompiler(BasePromptCompiler):
    """Compiles resolved scene context into engine-neutral prompt sections."""

    def __init__(self, section_builder: PromptSectionBuilder | None = None) -> None:
        self._section_builder = section_builder or PromptSectionBuilder()

    def compile(self, request: PromptCompilationRequest) -> PromptCompilationResult:
        """Compile a resolved scene context into structured cinematic sections."""
        sections = self._section_builder.build(request.scene_context)
        prompt = self._section_builder.render(sections)
        metadata = self._metadata_with_reference_assets(request)
        return PromptCompilationResult(
            scene=request.scene_context.scene,
            sections=sections,
            prompt=prompt,
            target_engine=request.target_engine,
            metadata=metadata,
        )

    @staticmethod
    def _metadata_with_reference_assets(
        request: PromptCompilationRequest,
    ) -> dict[str, Any]:
        metadata = dict(request.metadata)
        reference_assets = _identity_reference_assets(request.scene_context)
        character_states = _character_states(request.scene_context)
        if character_states:
            metadata["character_states"] = list(character_states)
        if not reference_assets:
            return metadata

        existing_assets = metadata.get("reference_assets", ())
        merged_assets: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        if isinstance(existing_assets, list | tuple):
            for existing_asset in existing_assets:
                if not isinstance(existing_asset, dict):
                    continue
                key = (
                    str(existing_asset.get("character_id", "")),
                    str(existing_asset.get("identity_id", "")),
                    str(existing_asset.get("path", "")),
                )
                if key in seen:
                    continue
                seen.add(key)
                merged_assets.append(dict(existing_asset))

        for reference_asset in reference_assets:
            key = (
                reference_asset["character_id"],
                reference_asset["identity_id"],
                reference_asset["path"],
            )
            if key in seen:
                continue
            seen.add(key)
            merged_assets.append(reference_asset)
        metadata["reference_assets"] = merged_assets
        return metadata


def _identity_reference_assets(context: ResolvedSceneContext) -> tuple[dict[str, Any], ...]:
    reference_assets: list[dict[str, Any]] = []
    for character in context.characters:
        identity = character.identity
        if identity is None or not identity.identity_locked or identity.reference_image is None:
            identity_asset = None
        else:
            identity_asset = {
                "character_id": identity.character_id,
                "identity_id": identity.identity_id,
                "path": identity.reference_image.path,
                "required": identity.reference_image.required,
                "identity_lock": identity.lock_level,
            }
        if identity_asset is not None:
            reference_assets.append(identity_asset)

        state = character.state
        if identity is None or state is None or state.reference_image is None:
            continue
        reference_assets.append(
            {
                "character_id": identity.character_id,
                "identity_id": identity.identity_id,
                "state_id": state.state_id,
                "path": state.reference_image.path,
                "required": state.reference_image.required,
                "identity_lock": state.lock_level,
                "reference_role": "state",
            },
        )
    return tuple(reference_assets)


def _character_states(context: ResolvedSceneContext) -> tuple[dict[str, Any], ...]:
    states: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for character in context.characters:
        identity = character.identity
        state = character.state
        if identity is None or state is None:
            continue
        key = (identity.identity_id, state.state_id)
        if key in seen:
            continue
        seen.add(key)
        states.append(
            {
                "character_id": identity.character_id,
                "identity_id": identity.identity_id,
                "state_id": state.state_id,
                "status": state.status,
                "reference_status": state.reference_status,
                "master_prompt_path": state.master_prompt_path or state.prompt_ref,
            },
        )
    return tuple(states)
