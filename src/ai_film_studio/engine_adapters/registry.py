"""Engine adapter registry."""

from __future__ import annotations

from collections.abc import Callable

from ai_film_studio.core.exceptions import AdapterRegistrationError
from ai_film_studio.engine_adapters.base import BaseEngineAdapter

EngineAdapterFactory = Callable[[], BaseEngineAdapter]


class EngineAdapterRegistry:
    """Stores engine adapter factories without coupling to any specific engine."""

    def __init__(self, factories: dict[str, EngineAdapterFactory] | None = None) -> None:
        self._factories: dict[str, EngineAdapterFactory] = dict(factories or {})

    def __len__(self) -> int:
        return len(self._factories)

    def __contains__(self, adapter_id: object) -> bool:
        return adapter_id in self._factories

    def register(self, adapter_id: str, factory: EngineAdapterFactory) -> None:
        """Register an adapter factory under a stable id."""
        if not adapter_id:
            msg = "Engine adapter id cannot be empty."
            raise AdapterRegistrationError(msg)
        if adapter_id in self._factories:
            msg = f"Engine adapter '{adapter_id}' is already registered."
            raise AdapterRegistrationError(msg)

        self._factories[adapter_id] = factory

    def get(self, adapter_id: str) -> BaseEngineAdapter:
        """Instantiate an adapter by id."""
        try:
            factory = self._factories[adapter_id]
        except KeyError as exc:
            msg = f"Engine adapter '{adapter_id}' is not registered."
            raise AdapterRegistrationError(msg) from exc

        adapter = factory()
        if adapter.adapter_id != adapter_id:
            msg = (
                f"Engine adapter factory for '{adapter_id}' returned "
                f"adapter '{adapter.adapter_id}'."
            )
            raise AdapterRegistrationError(msg)

        return adapter

    def list_adapter_ids(self) -> tuple[str, ...]:
        """Return registered adapter ids in deterministic order."""
        return tuple(sorted(self._factories))

    def copy(self) -> EngineAdapterRegistry:
        """Return a shallow copy of the registry."""
        return EngineAdapterRegistry(self._factories)

