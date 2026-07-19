"""Application runtime builder."""

from __future__ import annotations

from typing import Self

from ai_film_studio.builder.runtime import StudioRuntime
from ai_film_studio.core.exceptions import BuildError
from ai_film_studio.engine_adapters.registry import EngineAdapterFactory, EngineAdapterRegistry
from ai_film_studio.module_loader.loader import ModuleLoader
from ai_film_studio.validator.base import Validator
from ai_film_studio.validator.composite import CompositeValidator


class StudioBuilder:
    """Composes framework infrastructure without owning filmmaking logic."""

    def __init__(
        self,
        *,
        engine_adapters: EngineAdapterRegistry | None = None,
        module_loader: ModuleLoader | None = None,
        validator: CompositeValidator | None = None,
    ) -> None:
        self._engine_adapters = engine_adapters or EngineAdapterRegistry()
        self._module_loader = module_loader or ModuleLoader()
        self._validator = validator or CompositeValidator()

    def with_engine_adapter(
        self,
        adapter_id: str,
        factory: EngineAdapterFactory,
    ) -> Self:
        """Register an engine adapter factory by framework id."""
        self._engine_adapters.register(adapter_id, factory)
        return self

    def with_engine_adapter_from_import(
        self,
        adapter_id: str,
        import_path: str,
    ) -> Self:
        """Load and register an engine adapter factory from ``module:object`` syntax."""
        factory = self._module_loader.load(import_path)
        if not isinstance(factory, type) and not callable(factory):
            msg = f"Imported engine adapter '{import_path}' is not callable."
            raise BuildError(msg)

        return self.with_engine_adapter(
            adapter_id,
            factory,
        )

    def with_validator(self, validator: Validator) -> Self:
        """Add a validator to the runtime build process."""
        self._validator.add(validator)
        return self

    def build(self) -> StudioRuntime:
        """Build a runtime container and run registered infrastructure validators."""
        runtime = StudioRuntime(
            engine_adapters=self._engine_adapters.copy(),
            module_loader=self._module_loader,
            validator=self._validator.copy(),
        )
        validation = self._validator.validate(runtime)
        if not validation.is_valid:
            raise BuildError(validation.summary())

        return runtime


def create_default_builder(
    *,
    engine_adapters: EngineAdapterRegistry | None = None,
    module_loader: ModuleLoader | None = None,
    validator: CompositeValidator | None = None,
) -> StudioBuilder:
    """Create a builder with default framework infrastructure."""
    return StudioBuilder(
        engine_adapters=engine_adapters,
        module_loader=module_loader,
        validator=validator,
    )
