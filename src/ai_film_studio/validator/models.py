"""Validation data contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ValidationSeverity(StrEnum):
    """Severity levels for framework validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """A single validation issue."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: ValidationSeverity = ValidationSeverity.ERROR
    path: str | None = None


class ValidationResult(BaseModel):
    """Collection of validation issues."""

    model_config = ConfigDict(extra="forbid")

    issues: tuple[ValidationIssue, ...] = ()

    @classmethod
    def valid(cls) -> ValidationResult:
        """Return an empty successful validation result."""
        return cls()

    @property
    def is_valid(self) -> bool:
        """Return whether there are no error-level issues."""
        return all(issue.severity != ValidationSeverity.ERROR for issue in self.issues)

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Return a new result containing issues from both results."""
        return type(self)(issues=(*self.issues, *other.issues))

    def summary(self) -> str:
        """Return a compact text summary for exceptions and logs."""
        if not self.issues:
            return "Validation passed."
        return "; ".join(f"{issue.code}: {issue.message}" for issue in self.issues)

