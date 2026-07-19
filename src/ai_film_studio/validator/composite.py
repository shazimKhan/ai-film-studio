"""Composite validator implementation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ai_film_studio.validator.base import Validator
from ai_film_studio.validator.models import ValidationResult


class CompositeValidator:
    """Runs a collection of validators as one validator."""

    name = "composite"

    def __init__(self, validators: Iterable[Validator] | None = None) -> None:
        self._validators: list[Validator] = list(validators or [])

    def __len__(self) -> int:
        return len(self._validators)

    def add(self, validator: Validator) -> None:
        """Add a validator to the composite."""
        self._validators.append(validator)

    def validate(self, target: Any) -> ValidationResult:
        """Run all validators against a target and aggregate issues."""
        result = ValidationResult.valid()
        for validator in self._validators:
            result = result.merge(validator.validate(target))
        return result

    def copy(self) -> CompositeValidator:
        """Return a shallow copy of the composite."""
        return CompositeValidator(self._validators)

