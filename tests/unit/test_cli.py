from __future__ import annotations

from typer.testing import CliRunner

from ai_film_studio import __version__
from ai_film_studio.cli import app


def test_version_command_prints_package_version() -> None:
    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_doctor_command_builds_runtime() -> None:
    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Runtime foundation built successfully." in result.stdout


def test_compile_command_reports_missing_scene_without_traceback(tmp_path) -> None:
    missing_scene = tmp_path / "missing.yaml"

    result = CliRunner().invoke(app, ["compile", str(missing_scene), "--engine", "gemini"])

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "does not exist" in result.stdout
    assert "Traceback" not in result.stdout
