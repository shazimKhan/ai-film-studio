"""Validation contract."""

from __future__ import annotations

from typing import Any, Protocol

from ai_film_studio.validator.models import ValidationResult


class Validator(Protocol):
    """Protocol for pluggable framework validators."""

    name: str

    def validate(self, target: Any) -> ValidationResult:
        """Validate a target object."""

