"""Engine adapter contracts and registry."""

from ai_film_studio.engine_adapters.base import BaseEngineAdapter
from ai_film_studio.engine_adapters.gemini import GEMINI_ADAPTER_ID, GeminiAdapter
from ai_film_studio.engine_adapters.models import (
    EngineArtifact,
    EngineReferenceCapabilities,
    EngineRequest,
    EngineResult,
)
from ai_film_studio.engine_adapters.registry import EngineAdapterFactory, EngineAdapterRegistry

__all__ = [
    "BaseEngineAdapter",
    "EngineAdapterFactory",
    "EngineAdapterRegistry",
    "EngineArtifact",
    "EngineReferenceCapabilities",
    "EngineRequest",
    "EngineResult",
    "GEMINI_ADAPTER_ID",
    "GeminiAdapter",
]
