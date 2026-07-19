from __future__ import annotations

from ai_film_studio.prompt_compiler import (
    BasePromptCompiler,
    PromptCompilationRequest,
    PromptCompilationResult,
)


class DummyPromptCompiler(BasePromptCompiler):
    def compile(self, request: PromptCompilationRequest) -> PromptCompilationResult:
        return PromptCompilationResult(
            prompt=f"{request.template_name}:{request.project_id}",
            target_engine=request.target_engine,
        )


def test_prompt_compiler_contract_can_be_implemented() -> None:
    request = PromptCompilationRequest(
        project_id="demo",
        template_name="scene",
        target_engine="dummy",
    )

    result = DummyPromptCompiler().compile(request)

    assert result.prompt == "scene:demo"
    assert result.target_engine == "dummy"

