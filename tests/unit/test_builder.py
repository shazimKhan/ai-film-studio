from __future__ import annotations

import pytest

from ai_film_studio.builder import create_default_builder
from ai_film_studio.core.exceptions import BuildError
from ai_film_studio.validator.models import ValidationIssue, ValidationResult


class FailingValidator:
    name = "failing"

    def validate(self, target: object) -> ValidationResult:
        return ValidationResult(
            issues=(
                ValidationIssue(
                    code="foundation.invalid",
                    message="Invalid foundation.",
                ),
            ),
        )


def test_default_builder_creates_runtime() -> None:
    runtime = create_default_builder().build()

    assert runtime.engine_adapters.list_adapter_ids() == ("gemini",)


def test_builder_raises_for_validation_errors() -> None:
    builder = create_default_builder().with_validator(FailingValidator())

    with pytest.raises(BuildError, match="foundation.invalid"):
        builder.build()
