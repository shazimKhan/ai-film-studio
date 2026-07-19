from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ai_film_studio.asset_bible import AssetBibleService
from ai_film_studio.cli import app


def test_asset_validation_writes_index_and_reports_missing_images(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)

    report = AssetBibleService().validate(project_root)

    assert Path(report.index_path).exists()
    assert len(report.index.characters) == 1
    assert len(report.index.environments) == 1
    assert len(report.index.props) == 1
    assert any(issue.code == "asset.missing_image" for issue in report.issues)
    assert not report.is_valid


def test_asset_validation_detects_duplicate_character_ids(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)
    _write_character(project_root, "hero_copy", asset_id="hero")

    report = AssetBibleService().validate(project_root)

    assert any(issue.code == "asset.duplicate_id" for issue in report.issues)


def test_asset_validation_detects_broken_yaml_paths(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)
    character_yaml = project_root / "characters" / "hero" / "character.yaml"
    character_yaml.write_text(
        """
id: hero
asset_type: character
reference_status: awaiting_reference
source_path: missing/source.png
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = AssetBibleService().validate(project_root)

    assert any(issue.code == "asset.broken_path" for issue in report.issues)


def test_asset_validation_detects_missing_yaml(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)
    (project_root / "props" / "radio" / "prop.yaml").unlink()

    report = AssetBibleService().validate(project_root)

    assert any(issue.code == "asset.missing_yaml" for issue in report.issues)


def test_validate_assets_cli_writes_index_without_traceback(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)

    result = CliRunner().invoke(app, ["validate-assets", "--project-root", str(project_root)])

    assert result.exit_code == 1
    assert "Asset index written to:" in result.stdout
    assert "asset.missing_image" in result.stdout
    assert "Traceback" not in result.stdout


def _write_project(root: Path) -> Path:
    project_root = root / "project"
    _write_character(project_root, "hero")
    _write_environment(project_root, "house")
    _write_prop(project_root, "radio")
    return project_root


def _write_character(project_root: Path, folder: str, *, asset_id: str | None = None) -> None:
    asset_dir = project_root / "characters" / folder
    for child in ("references", "poses", "expressions", "wardrobe", "voice"):
        (asset_dir / child).mkdir(parents=True, exist_ok=True)
    (asset_dir / "character.yaml").write_text(
        f"""
id: {asset_id or folder}
asset_type: character
reference_status: awaiting_reference
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (asset_dir / "prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (asset_dir / "notes.md").write_text("# Notes\n", encoding="utf-8")


def _write_environment(project_root: Path, folder: str) -> None:
    asset_dir = project_root / "environment" / folder
    for child in ("references", "lighting", "angles"):
        (asset_dir / child).mkdir(parents=True, exist_ok=True)
    (asset_dir / "environment.yaml").write_text(
        f"""
id: {folder}
asset_type: environment
reference_status: awaiting_reference
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (asset_dir / "prompt.md").write_text("# Prompt\n", encoding="utf-8")


def _write_prop(project_root: Path, folder: str) -> None:
    asset_dir = project_root / "props" / folder / "references"
    asset_dir.mkdir(parents=True, exist_ok=True)
    prop_dir = asset_dir.parent
    (prop_dir / "prop.yaml").write_text(
        f"""
id: {folder}
asset_type: prop
reference_status: awaiting_reference
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (prop_dir / "prompt.md").write_text("# Prompt\n", encoding="utf-8")
