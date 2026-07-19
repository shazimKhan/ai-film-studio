"""Smart reference selector for manually managed character assets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_film_studio.core.exceptions import ReferenceSheetError
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.reference_sheets.models import (
    ExcludedReference,
    ReferenceSelectionRequest,
    ReferenceSelectionResult,
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
        return self.explain_from_yaml(character_yaml, request).selected

    def explain_from_yaml(
        self,
        character_yaml: Path,
        request: ReferenceSelectionRequest,
    ) -> ReferenceSelectionResult:
        """Load a character asset YAML file and return explainable selection output."""
        try:
            data = self._module_loader.load_yaml_file(character_yaml)
        except Exception as exc:
            msg = f"Could not load character asset '{character_yaml}': {exc}"
            raise ReferenceSheetError(msg) from exc
        return self.explain(data, request)

    def select(
        self,
        character_asset: Mapping[str, Any],
        request: ReferenceSelectionRequest,
    ) -> tuple[SelectedReference, ...]:
        """Return best matching references for a shot request."""
        return self.explain(character_asset, request).selected

    def explain(
        self,
        character_asset: Mapping[str, Any],
        request: ReferenceSelectionRequest,
    ) -> ReferenceSelectionResult:
        """Return selected references plus exclusion reasons for a shot request."""
        character_id = str(character_asset.get("id") or "unknown")
        views = self._views(character_asset)
        compatible: list[_CandidateReference] = []
        for name, raw_view in views.items():
            if not isinstance(raw_view, Mapping):
                continue
            status = _status(raw_view)
            if status == ReferenceStatus.REJECTED:
                compatible.append(
                    _CandidateReference.skipped(
                        name=str(name),
                        path=_path(raw_view),
                        reason="rejected reference",
                        status=status,
                    ),
                )
                continue
            if request.approved_only and not _is_approved(raw_view, status):
                compatible.append(
                    _CandidateReference.skipped(
                        name=str(name),
                        path=_path(raw_view),
                        reason="not approved",
                        status=status,
                    ),
                )
                continue

            tags = _reference_tags(str(name), raw_view)
            path = _path(raw_view)
            if path is None:
                compatible.append(
                    _CandidateReference.skipped(
                        name=str(name),
                        path=None,
                        reason="missing reference path",
                        status=status,
                        tags=tags,
                    ),
                )
                continue

            compatibility = _compatibility(tags, request)
            if not compatibility.is_compatible:
                compatible.append(
                    _CandidateReference.skipped(
                        name=str(name),
                        path=path,
                        reason=compatibility.reason,
                        status=status,
                        tags=tags,
                    ),
                )
                continue

            compatible.append(
                _CandidateReference(
                    name=str(name),
                    path=path,
                    reason=compatibility.reason,
                    score=self._score(tags, raw_view, request, compatibility),
                    priority=_priority(raw_view),
                    tags=tags,
                    status=status,
                    exact=compatibility.is_exact,
                    weak=compatibility.is_weak,
                    excluded=False,
                ),
            )

        exact_matches = [item for item in compatible if not item.excluded and item.exact]
        selectable = exact_matches or [
            item for item in compatible if not item.excluded and not item.exact
        ]
        selected_candidates = sorted(
            selectable,
            key=lambda item: (-item.score, item.priority, item.name),
        )[: request.engine_reference_limit]
        selected_names = {item.name for item in selected_candidates}

        selected = tuple(item.to_selected() for item in selected_candidates)
        excluded = []
        for item in compatible:
            if item.name in selected_names:
                continue
            if exact_matches and not item.excluded:
                excluded.append(item.to_excluded("exact approved match available"))
            else:
                excluded.append(item.to_excluded())

        return ReferenceSelectionResult(
            character_id=character_id,
            selector_inputs=request,
            selected=selected,
            excluded=tuple(sorted(excluded, key=lambda item: item.name)),
            engine_reference_limit=request.engine_reference_limit,
            allow_weak_fallbacks=request.allow_weak_fallbacks,
        )

    def _score(
        self,
        tags: set[str],
        raw_view: Mapping[str, Any],
        request: ReferenceSelectionRequest,
        compatibility: _ReferenceCompatibility,
    ) -> float:
        if compatibility.is_exact:
            return 100.0
        score = 45.0 if compatibility.is_weak else 70.0
        score += _match_score(tags, request.camera_shot_type, 8.0)
        score += _match_score(tags, request.framing, 5.0)
        score += _match_score(tags, request.angle, 8.0)
        score += _match_score(tags, request.pose, 5.0)
        score += _match_score(tags, request.action, 3.0)
        for preferred_type in request.preferred_reference_types:
            score += _match_score(tags, preferred_type, 2.0)
        score += max(0.0, 10.0 - (float(_priority(raw_view)) / 10.0))
        return round(min(score, 99.0), 2)

    def _views(self, character_asset: Mapping[str, Any]) -> Mapping[str, Any]:
        reference_images = character_asset.get("reference_images")
        if not isinstance(reference_images, Mapping):
            return {}
        views = reference_images.get("views")
        if not isinstance(views, Mapping):
            return {}
        return views


@dataclass(frozen=True, slots=True)
class _ReferenceCompatibility:
    is_compatible: bool
    is_exact: bool
    is_weak: bool
    reason: str


@dataclass(frozen=True, slots=True)
class _CandidateReference:
    name: str
    path: str | None
    reason: str
    score: float
    priority: int
    tags: set[str]
    status: ReferenceStatus
    exact: bool
    weak: bool
    excluded: bool

    @classmethod
    def skipped(
        cls,
        *,
        name: str,
        path: str | None,
        reason: str,
        status: ReferenceStatus,
        tags: set[str] | None = None,
    ) -> _CandidateReference:
        return cls(
            name=name,
            path=path,
            reason=reason,
            score=0.0,
            priority=100,
            tags=tags or set(),
            status=status,
            exact=False,
            weak=False,
            excluded=True,
        )

    def to_selected(self) -> SelectedReference:
        return SelectedReference(
            name=self.name,
            path=self.path or "",
            score=self.score,
            priority=self.priority,
            reason=self.reason,
            tags=tuple(sorted(self.tags)),
            status=self.status,
        )

    def to_excluded(self, reason: str | None = None) -> ExcludedReference:
        return ExcludedReference(
            name=self.name,
            path=self.path,
            reason=reason or self.reason,
            score=self.score,
            status=self.status,
            tags=tuple(sorted(self.tags)),
        )


def _path(raw_view: Mapping[str, Any]) -> str | None:
    path = raw_view.get("path")
    if isinstance(path, str) and path.strip():
        return path
    return None


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


def _compatibility(
    tags: set[str],
    request: ReferenceSelectionRequest,
) -> _ReferenceCompatibility:
    if _is_full_body_request(request) and not _matches(tags, "full_body"):
        if request.allow_weak_fallbacks and _matches(tags, "close_up"):
            return _ReferenceCompatibility(
                is_compatible=True,
                is_exact=False,
                is_weak=True,
                reason="weak fallback allowed for full-body request",
            )
        return _ReferenceCompatibility(
            is_compatible=False,
            is_exact=False,
            is_weak=False,
            reason="weak fallback disabled: full-body requests require a full-body reference",
        )

    if request.camera_shot_type and not _matches(tags, request.camera_shot_type):
        return _ReferenceCompatibility(
            is_compatible=False,
            is_exact=False,
            is_weak=False,
            reason="incompatible shot type",
        )
    if request.framing and not _matches(tags, request.framing):
        return _ReferenceCompatibility(
            is_compatible=False,
            is_exact=False,
            is_weak=False,
            reason="incompatible framing",
        )
    if request.pose and not _matches(tags, request.pose):
        return _ReferenceCompatibility(
            is_compatible=False,
            is_exact=False,
            is_weak=False,
            reason="incompatible pose",
        )

    angle_exact = True
    used_fallback = False
    if request.angle:
        angle_exact = _matches(tags, request.angle)
        if not angle_exact:
            fallback_reason = _strong_angle_fallback_reason(tags, request)
            if fallback_reason is None:
                return _ReferenceCompatibility(
                    is_compatible=False,
                    is_exact=False,
                    is_weak=False,
                    reason="incompatible angle",
                )
            used_fallback = True
    if used_fallback:
        return _ReferenceCompatibility(
            is_compatible=True,
            is_exact=False,
            is_weak=False,
            reason=fallback_reason or "approved fallback reference",
        )
    if angle_exact:
        return _ReferenceCompatibility(
            is_compatible=True,
            is_exact=True,
            is_weak=False,
            reason=_exact_reason(request),
        )
    return _ReferenceCompatibility(
        is_compatible=True,
        is_exact=False,
        is_weak=False,
        reason="approved compatible reference",
    )


def _is_full_body_request(request: ReferenceSelectionRequest) -> bool:
    values = (request.camera_shot_type, request.framing)
    return any(value is not None and _normalize(value) == "full_body" for value in values)


def _strong_angle_fallback_reason(
    tags: set[str],
    request: ReferenceSelectionRequest,
) -> str | None:
    angle = _normalize(request.angle or "")
    if angle == "front" and _matches(tags, "three_quarter") and _matches(tags, "close_up"):
        return "approved three-quarter fallback for close-up front request"
    if angle == "profile_left" and _matches(tags, "three_quarter_left"):
        return "approved three-quarter-left fallback for profile-left request"
    return None


def _exact_reason(request: ReferenceSelectionRequest) -> str:
    matched = []
    if request.angle:
        matched.append("angle")
    if request.camera_shot_type:
        matched.append("shot")
    if request.framing:
        matched.append("framing")
    if request.pose:
        matched.append("pose")
    if not matched:
        return "approved reference match"
    return f"exact {', '.join(matched)} match"


def _matches(tags: set[str], value: str) -> bool:
    aliases = _aliases(value)
    return any(alias in tags for alias in aliases)


def _aliases(value: str) -> set[str]:
    normalized = _normalize(value)
    alias_map = {
        "face": {"face", "close_up", "closeup", "portrait"},
        "close_up": {"close_up", "closeup", "portrait"},
        "profile_left": {"profile_left", "left_profile"},
        "left_profile": {"profile_left", "left_profile"},
        "three_quarter": {"three_quarter", "threequarter"},
        "three_quarter_left": {"three_quarter_left", "threequarter_left"},
        "three_quarter_right": {"three_quarter_right", "threequarter_right"},
        "full_body": {"full_body", "wide"},
        "seated": {"seated", "sitting"},
        "sitting": {"seated", "sitting"},
        "back_view": {"back_view", "back"},
    }
    aliases = alias_map.get(normalized)
    if aliases is not None:
        return set(aliases)
    return set(_terms(normalized))


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
    aliases = _aliases(value)
    if not aliases:
        return 0.0
    if _normalize(value) in tags:
        return weight
    if any(term in tags for term in aliases):
        return weight * 0.6
    return 0.0


def _terms(value: str) -> tuple[str, ...]:
    cleaned = _normalize(value)
    if not cleaned:
        return ()
    parts = tuple(part for part in cleaned.split("_") if part)
    return (cleaned, *parts)


def _normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")
