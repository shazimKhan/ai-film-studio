"""Gemini local prompt formatting adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_film_studio.engine_adapters.base import BaseEngineAdapter
from ai_film_studio.engine_adapters.models import EngineRequest, EngineResult

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

    def format_prompt(self, compiled_prompt: PromptCompilationResult) -> str:
        """Format structured prompt sections for Gemini video generation."""
        rendered_sections = "\n\n".join(
            f"{section.title}\n{section.content}" for section in compiled_prompt.sections
        )
        return (
            "GEMINI VIDEO PROMPT\n"
            "Use the following structured cinematic brief as the full generation instruction. "
            "Respect section order, identity locks, period rules, continuity, and negative "
            "constraints exactly.\n\n"
            f"{rendered_sections}"
        )

    def submit(self, request: EngineRequest) -> EngineResult:
        """Return a local dry-run result; Gemini API submission is outside this milestone."""
        return EngineResult(metadata={"prompt": request.prompt, "mode": "local_compile_only"})
