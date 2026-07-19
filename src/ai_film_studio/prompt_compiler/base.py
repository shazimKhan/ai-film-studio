"""Base prompt compiler contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai_film_studio.prompt_compiler.models import (
    PromptCompilationRequest,
    PromptCompilationResult,
)


class BasePromptCompiler(ABC):
    """Transforms scene context into engine-neutral prompts."""

    @abstractmethod
    def compile(self, request: PromptCompilationRequest) -> PromptCompilationResult:
        """Compile a prompt request into a prompt result."""

