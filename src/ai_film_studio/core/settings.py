"""Shared framework settings and extension points."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EntryPointGroups:
    """Python entry point groups used for framework extension discovery."""

    engine_adapters: str = "ai_film_studio.engine_adapters"
    modules: str = "ai_film_studio.modules"


DEFAULT_ENTRY_POINT_GROUPS = EntryPointGroups()

