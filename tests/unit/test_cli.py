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

