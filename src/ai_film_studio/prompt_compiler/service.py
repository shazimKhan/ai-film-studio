"""Prompt compilation orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_film_studio.builder.runtime import StudioRuntime
from ai_film_studio.core.exceptions import UnsupportedEngineError
from ai_film_studio.engine_adapters.base import BaseEngineAdapter
from ai_film_studio.engine_adapters.registry import EngineAdapterRegistry
from ai_film_studio.prompt_compiler.compiler import PromptCompiler
from ai_film_studio.prompt_compiler.loader import SceneBlueprintLoader
from ai_film_studio.prompt_compiler.models import PromptCompilationRequest, PromptCompilationResult
from ai_film_studio.prompt_compiler.output import VersionedPromptWriter
from ai_film_studio.prompt_compiler.resolver import ModuleReferenceResolver


@dataclass(frozen=True, slots=True)
class CompilationArtifact:
    """Result of local prompt compilation."""

    output_path: Path
    prompt: str
    compiled: PromptCompilationResult


class PromptCompilationService:
    """Coordinates scene loading, prompt compilation, adapter formatting, and output."""

    def __init__(
        self,
        *,
        scene_loader: SceneBlueprintLoader,
        resolver: ModuleReferenceResolver,
        compiler: PromptCompiler,
        engine_adapters: EngineAdapterRegistry,
        writer: VersionedPromptWriter,
    ) -> None:
        self._scene_loader = scene_loader
        self._resolver = resolver
        self._compiler = compiler
        self._engine_adapters = engine_adapters
        self._writer = writer

    @classmethod
    def from_runtime(
        cls,
        runtime: StudioRuntime,
        *,
        repo_root: Path,
        output_root: Path,
    ) -> PromptCompilationService:
        """Create the service from an existing runtime container."""
        module_loader = runtime.module_loader
        return cls(
            scene_loader=SceneBlueprintLoader(module_loader),
            resolver=ModuleReferenceResolver(module_loader, repo_root=repo_root),
            compiler=PromptCompiler(),
            engine_adapters=runtime.engine_adapters,
            writer=VersionedPromptWriter(output_root),
        )

    def compile(self, scene_file: Path, engine_id: str) -> CompilationArtifact:
        """Compile a scene blueprint locally for a target engine."""
        scene = self._scene_loader.load(scene_file)
        adapter = self._adapter_for(engine_id)
        context = self._resolver.resolve(scene, scene_file)
        compiled = self._compiler.compile(
            PromptCompilationRequest(
                scene_context=context,
                target_engine=adapter.adapter_id,
            ),
        )
        prompt = adapter.format_prompt(compiled)
        output_path = self._writer.write(scene, adapter.adapter_id, prompt)
        return CompilationArtifact(output_path=output_path, prompt=prompt, compiled=compiled)

    def _adapter_for(self, engine_id: str) -> BaseEngineAdapter:
        if engine_id not in self._engine_adapters:
            available = ", ".join(self._engine_adapters.list_adapter_ids()) or "none"
            msg = f"Unsupported engine '{engine_id}'. Available engines: {available}."
            raise UnsupportedEngineError(msg)
        return self._engine_adapters.get(engine_id)
