"""Runtime container shared by framework entry points."""

from __future__ import annotations

from dataclasses import dataclass

from ai_film_studio.engine_adapters.registry import EngineAdapterRegistry
from ai_film_studio.module_loader.loader import ModuleLoader
from ai_film_studio.validator.composite import CompositeValidator


@dataclass(frozen=True, slots=True)
class StudioRuntime:
    """Built framework infrastructure.

    The runtime intentionally contains infrastructure services only. Pipeline-specific
    filmmaking behavior belongs in independently registered modules.
    """

    engine_adapters: EngineAdapterRegistry
    module_loader: ModuleLoader
    validator: CompositeValidator

