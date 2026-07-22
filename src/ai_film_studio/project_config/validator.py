"""Reusable project configuration validator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ai_film_studio.asset_bible import IdentityLockService
from ai_film_studio.core.exceptions import AIFilmStudioError
from ai_film_studio.module_loader import ModuleLoader
from ai_film_studio.project_config.models import (
    APPROVED_SOURCE_STATES,
    SOURCE_VALIDATION_STATES,
    SUPPORTED_ADAPTER_IDS,
    ProjectConfig,
    ProjectValidationIssue,
    ProjectValidationReport,
    SourceRegistry,
)


class ProjectConfigValidator:
    """Validates reusable project configuration and research gates."""

    def __init__(self, *, repo_root: Path, module_loader: ModuleLoader | None = None) -> None:
        self._repo_root = repo_root
        self._module_loader = module_loader or ModuleLoader()

    def validate_project(self, project_root: Path) -> ProjectValidationReport:
        """Validate a single project directory."""
        resolved_project_root = self._resolve(project_root)
        config_path = resolved_project_root / "project.yaml"
        issues: list[ProjectValidationIssue] = []
        if not config_path.is_file():
            return ProjectValidationReport(
                project_id=resolved_project_root.name,
                project_root=self._repo_relative(resolved_project_root),
                issues=(
                    ProjectValidationIssue(
                        code="project.missing_config",
                        path=self._repo_relative(config_path),
                        message="Missing project.yaml.",
                    ),
                ),
            )

        raw_config = self._load_yaml(config_path, issues)
        config: ProjectConfig | None = None
        if isinstance(raw_config, dict):
            try:
                config = ProjectConfig.model_validate(raw_config)
            except ValidationError as exc:
                issues.append(
                    ProjectValidationIssue(
                        code="project.invalid_config",
                        path=self._repo_relative(config_path),
                        message=str(exc),
                    ),
                )
        else:
            issues.append(
                ProjectValidationIssue(
                    code="project.invalid_config",
                    path=self._repo_relative(config_path),
                    message="Project config must be a YAML mapping.",
                ),
            )

        if config is not None:
            issues.extend(self._validate_config(config, resolved_project_root, raw_config))

        return ProjectValidationReport(
            project_id=config.project_id if config is not None else resolved_project_root.name,
            project_root=self._repo_relative(resolved_project_root),
            issues=tuple(issues),
        )

    def validate_workspace(
        self,
        projects_root: Path = Path("projects"),
    ) -> tuple[ProjectValidationReport, ...]:
        """Validate every project under a projects directory and catch duplicate ids."""
        resolved_projects_root = self._resolve(projects_root)
        reports = [
            self.validate_project(path)
            for path in sorted(resolved_projects_root.iterdir())
            if path.is_dir()
        ]
        counts: dict[str, int] = {}
        for report in reports:
            counts[report.project_id] = counts.get(report.project_id, 0) + 1

        duplicate_ids = {project_id for project_id, count in counts.items() if count > 1}
        if not duplicate_ids:
            return tuple(reports)

        updated: list[ProjectValidationReport] = []
        for report in reports:
            issues = list(report.issues)
            if report.project_id in duplicate_ids:
                issues.append(
                    ProjectValidationIssue(
                        code="project.duplicate_id",
                        path=report.project_root,
                        message=f"Duplicate project id '{report.project_id}'.",
                    ),
                )
            updated.append(report.model_copy(update={"issues": tuple(issues)}))
        return tuple(updated)

    def _validate_config(
        self,
        config: ProjectConfig,
        project_root: Path,
        raw_config: dict[str, Any],
    ) -> tuple[ProjectValidationIssue, ...]:
        issues: list[ProjectValidationIssue] = []
        issues.extend(self._validate_adapter_ids(config, project_root))
        issues.extend(self._validate_asset_path(config, project_root))
        issues.extend(self._validate_identities(project_root))
        if config.source_validation_required:
            issues.extend(self._validate_sources(config, project_root, raw_config))
        return tuple(issues)

    def _validate_adapter_ids(
        self,
        config: ProjectConfig,
        project_root: Path,
    ) -> tuple[ProjectValidationIssue, ...]:
        issues = []
        for adapter_id in config.prompt_engines:
            if adapter_id not in SUPPORTED_ADAPTER_IDS:
                issues.append(
                    ProjectValidationIssue(
                        code="project.unsupported_adapter",
                        path=self._repo_relative(project_root / "project.yaml"),
                        message=f"Unsupported adapter '{adapter_id}'.",
                    ),
                )
        return tuple(issues)

    def _validate_asset_path(
        self,
        config: ProjectConfig,
        project_root: Path,
    ) -> tuple[ProjectValidationIssue, ...]:
        asset_path = self._repo_root / config.project_asset_path
        if asset_path.exists():
            return ()
        return (
            ProjectValidationIssue(
                code="project.broken_asset_path",
                path=self._repo_relative(project_root / "project.yaml"),
                message=f"Project asset path '{config.project_asset_path}' does not exist.",
            ),
        )

    def _validate_identities(self, project_root: Path) -> tuple[ProjectValidationIssue, ...]:
        identity_issues = IdentityLockService(
            repo_root=self._repo_root,
            module_loader=self._module_loader,
        ).validate_project(project_root)
        return tuple(
            ProjectValidationIssue(
                code=issue.code,
                path=issue.path,
                message=issue.message,
            )
            for issue in identity_issues
        )

    def _validate_sources(
        self,
        config: ProjectConfig,
        project_root: Path,
        raw_config: dict[str, Any],
    ) -> tuple[ProjectValidationIssue, ...]:
        source_validation = raw_config.get("source_validation")
        source_registry_path = "01_research/source_registry.yaml"
        if isinstance(source_validation, dict):
            raw_path = source_validation.get("source_registry")
            if isinstance(raw_path, str) and raw_path.strip():
                source_registry_path = raw_path
        registry_path = project_root / source_registry_path
        if not registry_path.is_file():
            return (
                ProjectValidationIssue(
                    code="source.missing_registry",
                    path=self._repo_relative(registry_path),
                    message="Source validation is required but source registry is missing.",
                ),
            )

        issues: list[ProjectValidationIssue] = []
        raw_registry = self._load_yaml(registry_path, issues)
        if not isinstance(raw_registry, dict):
            issues.append(
                ProjectValidationIssue(
                    code="source.invalid_registry",
                    path=self._repo_relative(registry_path),
                    message="Source registry must be a YAML mapping.",
                ),
            )
            return tuple(issues)

        try:
            registry = SourceRegistry.model_validate(raw_registry)
        except ValidationError as exc:
            issues.append(
                ProjectValidationIssue(
                    code="source.invalid_registry",
                    path=self._repo_relative(registry_path),
                    message=str(exc),
                ),
            )
            return tuple(issues)

        unsupported_states = set(registry.validation_states) - SOURCE_VALIDATION_STATES
        for state in sorted(unsupported_states):
            issues.append(
                ProjectValidationIssue(
                    code="source.invalid_state",
                    path=self._repo_relative(registry_path),
                    message=f"Unsupported source validation state '{state}'.",
                ),
            )

        has_approved_source = any(
            record.is_approved_for_production for record in registry.source_records
        )
        if not has_approved_source:
            issues.append(
                ProjectValidationIssue(
                    code="source.no_approved_records",
                    path=self._repo_relative(registry_path),
                    message=(
                        "Project requires source validation, but no source record is "
                        f"approved for script with state {sorted(APPROVED_SOURCE_STATES)}."
                    ),
                ),
            )
        return tuple(issues)

    def _load_yaml(
        self,
        path: Path,
        issues: list[ProjectValidationIssue],
    ) -> Any:
        try:
            return self._module_loader.load_yaml_file(path)
        except Exception as exc:
            issues.append(
                ProjectValidationIssue(
                    code="yaml.invalid",
                    path=self._repo_relative(path),
                    message=f"Could not load YAML: {exc}",
                ),
            )
            return None

    def _resolve(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return self._repo_root / path

    def _repo_relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self._repo_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()


def require_valid_project(report: ProjectValidationReport) -> None:
    """Raise a readable exception for invalid project validation reports."""
    if report.is_valid:
        return
    joined = "; ".join(f"{issue.code}: {issue.message}" for issue in report.issues)
    msg = f"Project validation failed for '{report.project_id}': {joined}"
    raise AIFilmStudioError(msg)
