from __future__ import annotations

import math

import pytest

from ai_film_studio.core.exceptions import InvalidYAMLError, ModuleLoadError
from ai_film_studio.module_loader import ModuleLoader, ModuleSpec


def test_loader_imports_module() -> None:
    loaded = ModuleLoader().load(ModuleSpec(import_path="math"))

    assert loaded is math


def test_loader_imports_attribute_from_colon_path() -> None:
    loaded = ModuleLoader().load("math:sqrt")

    assert loaded(9) == 3


def test_loader_wraps_missing_attribute() -> None:
    with pytest.raises(ModuleLoadError, match="does not expose"):
        ModuleLoader().load("math:not_real")


def test_loader_reads_yaml_data_module(tmp_path) -> None:
    path = tmp_path / "module.yaml"
    path.write_text("name: Example\nitems:\n  - one\n", encoding="utf-8")

    loaded = ModuleLoader().load_data_module(path)

    assert loaded.kind == "yaml"
    assert loaded.data == {"name": "Example", "items": ["one"]}


def test_loader_reads_markdown_data_module(tmp_path) -> None:
    path = tmp_path / "module.md"
    path.write_text("# Notes\n\nA reusable module.\n", encoding="utf-8")

    loaded = ModuleLoader().load_data_module(path)

    assert loaded.kind == "markdown"
    assert loaded.data.startswith("# Notes")


def test_loader_raises_clear_error_for_invalid_yaml(tmp_path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("name: [unterminated\n", encoding="utf-8")

    with pytest.raises(InvalidYAMLError, match="Invalid YAML"):
        ModuleLoader().load_yaml_file(path)
