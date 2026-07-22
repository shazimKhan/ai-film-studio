from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from typer.testing import CliRunner

from ai_film_studio.cli import app
from ai_film_studio.project_config import ProjectConfig, ProjectConfigValidator


def test_normal_fictional_project_can_be_validated(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path, project_id="drama_one")

    report = ProjectConfigValidator(repo_root=tmp_path).validate_project(project_root)

    assert report.is_valid


def test_islamic_research_project_requires_approved_sources(tmp_path: Path) -> None:
    project_root = _write_project(
        tmp_path,
        project_id="history_one",
        project_type="islamic_history",
        research_required=True,
        source_validation_required=True,
    )
    _write_source_registry(project_root, source_records=[])

    report = ProjectConfigValidator(repo_root=tmp_path).validate_project(project_root)

    assert not report.is_valid
    assert any(issue.code == "source.no_approved_records" for issue in report.issues)


def test_guriya_does_not_require_source_validation() -> None:
    repo_root = _repo_root()

    report = ProjectConfigValidator(repo_root=repo_root).validate_project(
        repo_root / "projects/guriya",
    )

    assert report.project_id == "guriya"
    assert report.is_valid


def test_insan_requires_source_validation() -> None:
    repo_root = _repo_root()

    report = ProjectConfigValidator(repo_root=repo_root).validate_project(
        repo_root / "projects/insan",
    )

    assert report.project_id == "insan"
    assert not report.is_valid
    assert any(issue.code == "source.no_approved_records" for issue in report.issues)


def test_engine_modules_contain_no_project_specific_data() -> None:
    repo_root = _repo_root()
    forbidden = ("guriya", "insan")
    engine_files = [
        path for path in (repo_root / "engine").rglob("*") if path.is_file()
    ]

    assert engine_files
    for path in engine_files:
        text = path.read_text(encoding="utf-8").lower()
        assert all(value not in text for value in forbidden), path


def test_project_ids_are_unique(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    _write_project(projects_root, project_id="same_id", folder_name="first")
    _write_project(projects_root, project_id="same_id", folder_name="second")

    reports = ProjectConfigValidator(repo_root=tmp_path).validate_workspace(projects_root)

    assert any(
        issue.code == "project.duplicate_id"
        for report in reports
        for issue in report.issues
    )


def test_broken_asset_references_are_detected(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path, project_id="broken_assets")
    project_yaml = project_root / "project.yaml"
    data = yaml.safe_load(project_yaml.read_text(encoding="utf-8"))
    data["project_asset_path"] = "projects/missing_assets"
    project_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    report = ProjectConfigValidator(repo_root=tmp_path).validate_project(project_root)

    assert any(issue.code == "project.broken_asset_path" for issue in report.issues)


def test_invalid_source_states_are_rejected(tmp_path: Path) -> None:
    project_root = _write_project(
        tmp_path,
        project_id="bad_states",
        project_type="islamic_history",
        research_required=True,
        source_validation_required=True,
    )
    _write_source_registry(
        project_root,
        validation_states=["unverified", "not_a_real_state"],
        source_records=[
            {
                "source_id": "src_001",
                "source_type": "quran",
                "validation_state": "approved_for_narration",
                "approved_for_script": True,
            },
        ],
    )

    report = ProjectConfigValidator(repo_root=tmp_path).validate_project(project_root)

    assert any(issue.code == "source.invalid_state" for issue in report.issues)


def test_depiction_policy_configuration_is_loaded(tmp_path: Path) -> None:
    project_root = _write_project(
        tmp_path,
        project_id="depiction_project",
        depiction_policy="sensitive_presence_policy",
    )
    data = yaml.safe_load((project_root / "project.yaml").read_text(encoding="utf-8"))

    config = ProjectConfig.model_validate(data)

    assert config.depiction_policy == "sensitive_presence_policy"


def test_templates_are_reusable() -> None:
    repo_root = _repo_root()
    template_files = [
        path for path in (repo_root / "shared/templates").rglob("*") if path.is_file()
    ]

    assert template_files
    for path in template_files:
        text = path.read_text(encoding="utf-8").lower()
        assert "guriya" not in text
        assert "insan" not in text


def test_validate_project_cli_reports_source_gate() -> None:
    repo_root = _repo_root()

    result = CliRunner().invoke(app, ["validate-project", str(repo_root / "projects/insan")])

    assert result.exit_code == 1
    assert "Project validation failed:" in result.stdout
    assert "source.no_approved_records" in result.stdout
    assert "Traceback" not in result.stdout


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_project(
    root: Path,
    *,
    project_id: str,
    folder_name: str | None = None,
    project_type: str = "fictional_drama",
    research_required: bool = False,
    source_validation_required: bool = False,
    depiction_policy: str = "standard",
) -> Path:
    project_root = root / (folder_name or project_id)
    project_root.mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": "1.0",
        "project_id": project_id,
        "project_name": project_id.replace("_", " ").title(),
        "project_type": project_type,
        "genre": ["drama"],
        "language": "urdu",
        "secondary_languages": [],
        "historical_period": "",
        "research_required": research_required,
        "source_validation_required": source_validation_required,
        "depiction_policy": depiction_policy,
        "visual_style": {"tone": "test"},
        "aspect_ratio": "16:9",
        "default_shot_duration": 6,
        "target_platforms": ["youtube"],
        "prompt_engines": ["gemini"],
        "voiceover_language": "urdu",
        "continuity_level": "standard",
        "qa_profiles": ["technical"],
        "shared_asset_access": {"enabled": True},
        "project_asset_path": project_root.relative_to(root).as_posix(),
        "export_presets": [],
    }
    (project_root / "project.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    return project_root


def _write_source_registry(
    project_root: Path,
    *,
    source_records: list[dict[str, Any]],
    validation_states: list[str] | None = None,
) -> None:
    research_root = project_root / "01_research"
    research_root.mkdir(parents=True, exist_ok=True)
    registry = {
        "schema_version": "1.0",
        "project_id": project_root.name,
        "validation_states": validation_states
        or [
            "unverified",
            "under_review",
            "verified",
            "disputed",
            "rejected",
            "approved_for_narration",
            "approved_for_visual_context",
        ],
        "source_records": source_records,
    }
    (research_root / "source_registry.yaml").write_text(
        yaml.safe_dump(registry, sort_keys=False),
        encoding="utf-8",
    )
