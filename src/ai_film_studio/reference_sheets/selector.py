"""Smart reference selector for manually managed character assets."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ai_film_studio.core.exceptions import ReferenceSheetError
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.reference_sheets.models import (
    ReferenceSelectionRequest,
    ReferenceStatus,
    SelectedReference,
)


class ReferenceSelector:
    """Selects the best character references from asset metadata."""

    def __init__(self, module_loader: ModuleLoader | None = None) -> None:
        self._module_loader = module_loader or ModuleLoader()

    def select_from_yaml(
        self,
        character_yaml: Path,
        request: ReferenceSelectionRequest,
    ) -> tuple[SelectedReference, ...]:
        """Load a character asset YAML file and select matching references."""
        try:
            data = self._module_loader.load_yaml_file(character_yaml)
        except Exception as exc:
            msg = f"Could not load character asset '{character_yaml}': {exc}"
            raise ReferenceSheetError(msg) from exc
        return self.select(data, request)

    def select(
        self,
        character_asset: Mapping[str, Any],
        request: ReferenceSelectionRequest,
    ) -> tuple[SelectedReference, ...]:
        """Return best matching references for a shot request."""
        views = self._views(character_asset)
        scored: list[SelectedReference] = []
        for name, raw_view in views.items():
            if not isinstance(raw_view, Mapping):
                continue
            status = _status(raw_view)
            if status == ReferenceStatus.REJECTED:
                continue
            if request.approved_only and not _is_approved(raw_view, status):
                continue

            tags = _reference_tags(str(name), raw_view)
            score = self._score(tags, raw_view, request)
            if score <= 0:
                continue
            path = raw_view.get("path")
            if not isinstance(path, str) or not path.strip():
                continue
            scored.append(
                SelectedReference(
                    name=str(name),
                    path=path,
                    score=score,
                    priority=_priority(raw_view),
                    tags=tuple(sorted(tags)),
                    status=status,
                ),
            )

        return tuple(
            sorted(scored, key=lambda item: (-item.score, item.priority, item.name))[
                : request.engine_reference_limit
            ],
        )

    def _score(
        self,
        tags: set[str],
        raw_view: Mapping[str, Any],
        request: ReferenceSelectionRequest,
    ) -> float:
        score = max(0.0, 100.0 - float(_priority(raw_view))) / 10.0
        score += _match_score(tags, request.camera_shot_type, 40.0)
        score += _match_score(tags, request.framing, 35.0)
        score += _match_score(tags, request.angle, 40.0)
        score += _match_score(tags, request.pose, 30.0)
        score += _match_score(tags, request.action, 20.0)
        for preferred_type in request.preferred_reference_types:
            score += _match_score(tags, preferred_type, 10.0)
        return score

    def _views(self, character_asset: Mapping[str, Any]) -> Mapping[str, Any]:
        reference_images = character_asset.get("reference_images")
        if not isinstance(reference_images, Mapping):
            return {}
        views = reference_images.get("views")
        if not isinstance(views, Mapping):
            return {}
        return views


def _status(raw_view: Mapping[str, Any]) -> ReferenceStatus:
    raw_status = raw_view.get("status")
    if isinstance(raw_status, str):
        try:
            return ReferenceStatus(raw_status)
        except ValueError:
            return ReferenceStatus.PENDING_REVIEW
    if raw_view.get("approved") is True:
        return ReferenceStatus.APPROVED
    return ReferenceStatus.PENDING_REVIEW


def _is_approved(raw_view: Mapping[str, Any], status: ReferenceStatus) -> bool:
    return status == ReferenceStatus.APPROVED or raw_view.get("approved") is True


def _priority(raw_view: Mapping[str, Any]) -> int:
    raw_priority = raw_view.get("priority", 100)
    if isinstance(raw_priority, int):
        return raw_priority
    try:
        return int(str(raw_priority))
    except ValueError:
        return 100


def _reference_tags(name: str, raw_view: Mapping[str, Any]) -> set[str]:
    tags = set(_terms(name))
    for key in ("tags", "shot_types", "camera_angles"):
        tags.update(_terms_from_value(raw_view.get(key)))
    return tags


def _terms_from_value(value: Any) -> set[str]:
    terms: set[str] = set()
    if isinstance(value, str):
        terms.update(_terms(value))
        return terms
    if isinstance(value, list | tuple | set):
        for item in value:
            terms.update(_terms(str(item)))
    return terms


def _match_score(tags: set[str], value: str | None, weight: float) -> float:
    if value is None:
        return 0.0
    terms = _terms(value)
    if not terms:
        return 0.0
    if terms[0] in tags:
        return weight
    if any(term in tags for term in terms[1:]):
        return weight * 0.6
    return 0.0


def _terms(value: str) -> tuple[str, ...]:
    cleaned = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not cleaned:
        return ()
    parts = tuple(part for part in cleaned.split("_") if part)
    return (cleaned, *parts)
