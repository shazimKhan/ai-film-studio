"""Prompt compiler implementation."""

from __future__ import annotations

from ai_film_studio.prompt_compiler.base import BasePromptCompiler
from ai_film_studio.prompt_compiler.models import (
    PromptCompilationRequest,
    PromptCompilationResult,
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
        return PromptCompilationResult(
            scene=request.scene_context.scene,
            sections=sections,
            prompt=prompt,
            target_engine=request.target_engine,
            metadata=request.metadata,
        )
