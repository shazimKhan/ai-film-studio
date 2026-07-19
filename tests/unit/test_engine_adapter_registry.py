from __future__ import annotations

import pytest

from ai_film_studio.core.exceptions import AdapterRegistrationError
from ai_film_studio.engine_adapters import (
    BaseEngineAdapter,
    EngineRequest,
    EngineResult,
)
from ai_film_studio.engine_adapters.registry import EngineAdapterRegistry


class DummyAdapter(BaseEngineAdapter):
    @property
    def adapter_id(self) -> str:
        return "dummy"

    @property
    def capabilities(self) -> tuple[str, ...]:
        return ("text_to_video",)

    def submit(self, request: EngineRequest) -> EngineResult:
        return EngineResult(metadata={"prompt": request.prompt})


class MismatchedAdapter(DummyAdapter):
    @property
    def adapter_id(self) -> str:
        return "other"


def test_registry_registers_and_resolves_adapter_factory() -> None:
    registry = EngineAdapterRegistry()

    registry.register("dummy", DummyAdapter)

    adapter = registry.get("dummy")
    assert registry.list_adapter_ids() == ("dummy",)
    assert adapter.supports("text_to_video")


def test_registry_rejects_duplicate_adapter_id() -> None:
    registry = EngineAdapterRegistry()
    registry.register("dummy", DummyAdapter)

    with pytest.raises(AdapterRegistrationError, match="already registered"):
        registry.register("dummy", DummyAdapter)


def test_registry_rejects_mismatched_adapter_factory() -> None:
    registry = EngineAdapterRegistry()
    registry.register("dummy", MismatchedAdapter)

    with pytest.raises(AdapterRegistrationError, match="returned adapter 'other'"):
        registry.get("dummy")

