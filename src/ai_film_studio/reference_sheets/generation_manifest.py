"""Helpers for adding selected references to generation manifests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ai_film_studio.reference_sheets.models import SelectedReference


def with_selected_character_references(
    manifest: Mapping[str, Any],
    *,
    character_id: str,
    references: Sequence[SelectedReference],
) -> dict[str, Any]:
    """Return a generation manifest copy extended with selected character references."""
    updated = dict(manifest)
    selected = list(updated.get("selected_character_references", []))
    selected.append(
        {
            "character_id": character_id,
            "references": [
                {
                    "name": reference.name,
                    "path": reference.path,
                    "score": reference.score,
                    "priority": reference.priority,
                    "tags": list(reference.tags),
                    "status": reference.status.value,
                }
                for reference in references
            ],
        },
    )
    updated["selected_character_references"] = selected
    return updated
