"""Gemini local prompt formatting adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_film_studio.engine_adapters.base import BaseEngineAdapter
from ai_film_studio.engine_adapters.models import (
    EngineReferenceCapabilities,
    EngineRequest,
    EngineResult,
)

if TYPE_CHECKING:
    from ai_film_studio.prompt_compiler.models import PromptCompilationResult

GEMINI_ADAPTER_ID = "gemini"


class GeminiAdapter(BaseEngineAdapter):
    """Formats compiled prompt sections for Gemini without making API calls."""

    @property
    def adapter_id(self) -> str:
        return GEMINI_ADAPTER_ID

    @property
    def display_name(self) -> str:
        return "Gemini"

    @property
    def capabilities(self) -> tuple[str, ...]:
        return ("prompt_formatting", "video_prompt")

    @property
    def reference_capabilities(self) -> EngineReferenceCapabilities:
        return EngineReferenceCapabilities(
            max_character_reference_images=4,
            supports_multiple_references=True,
            supports_reference_manifest=True,
            preferred_reference_types=(
                "front",
                "three_quarter",
                "profile",
                "full_body",
            ),
        )

    def format_prompt(self, compiled_prompt: PromptCompilationResult) -> str:
        """Format structured prompt sections for Gemini video generation."""
        rendered_sections = "\n\n".join(
            f"{section.title}\n{section.content}" for section in compiled_prompt.sections
        )
        reference_block = _reference_asset_block(
            compiled_prompt.metadata.get("reference_assets"),
        )
        body = f"{reference_block}\n\n{rendered_sections}" if reference_block else rendered_sections
        return (
            "GEMINI VIDEO PROMPT\n"
            "Use the following structured cinematic brief as the full generation instruction. "
            "Respect section order, identity locks, period rules, continuity, and negative "
            "constraints exactly.\n\n"
            f"{body}"
        )

    def submit(self, request: EngineRequest) -> EngineResult:
        """Return a local dry-run result; Gemini API submission is outside this milestone."""
        return EngineResult(metadata={"prompt": request.prompt, "mode": "local_compile_only"})


def _reference_asset_block(reference_assets: Any) -> str:
    if not isinstance(reference_assets, list | tuple) or not reference_assets:
        return ""

    lines = ["MANDATORY REFERENCE ASSETS"]
    for reference_asset in reference_assets:
        if not isinstance(reference_asset, dict):
            continue
        character_id = reference_asset.get("character_id", "unknown_character")
        identity_id = reference_asset.get("identity_id", "unknown_identity")
        path = reference_asset.get("path", "")
        required = "required" if reference_asset.get("required", False) else "optional"
        lock_level = reference_asset.get("identity_lock", "standard")
        lines.append(
            f"- {character_id} / {identity_id}: {path} ({required}, identity lock: {lock_level})",
        )
    if len(lines) == 1:
        return ""
    return "\n".join(lines)
