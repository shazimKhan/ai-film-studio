"""Prompt compiler error formatting helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError


def format_validation_error(source: Path, exc: ValidationError, label: str) -> str:
    """Format Pydantic validation errors for CLI-safe output."""
    lines = [f"Invalid {label} '{source}':"]
    for issue in exc.errors():
        location = _format_location(issue.get("loc", ()))
        message = str(issue.get("msg", "Invalid value."))
        lines.append(f"- {location}: {message}")

    return "\n".join(lines)


def _format_location(location: Any) -> str:
    if not location:
        return "<root>"
    if isinstance(location, str):
        return location
    return ".".join(str(part) for part in location)
