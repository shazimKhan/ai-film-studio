"""Base engine adapter contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection
from typing import TYPE_CHECKING

from ai_film_studio.engine_adapters.models import EngineRequest, EngineResult

if TYPE_CHECKING:
    from ai_film_studio.prompt_compiler.models import PromptCompilationResult


class BaseEngineAdapter(ABC):
    """Engine-neutral adapter base class.

    Concrete adapters belong in extension modules and should encapsulate all
    vendor-specific behavior behind this contract.
    """

    @property
    @abstractmethod
    def adapter_id(self) -> str:
        """Stable framework id for the adapter."""

    @property
    def display_name(self) -> str:
        """Human-friendly adapter name."""
        return self.adapter_id

    @property
    def capabilities(self) -> Collection[str]:
        """Capability names supported by this adapter."""
        return ()

    def supports(self, capability: str) -> bool:
        """Return whether the adapter advertises a framework capability."""
        return capability in self.capabilities

    def format_prompt(self, compiled_prompt: PromptCompilationResult) -> str:
        """Format an engine-neutral compiled prompt for this adapter."""
        return compiled_prompt.prompt

    @abstractmethod
    def submit(self, request: EngineRequest) -> EngineResult:
        """Submit an engine-neutral request to the backing engine."""
