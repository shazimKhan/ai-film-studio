from __future__ import annotations

import math

import pytest

from ai_film_studio.core.exceptions import ModuleLoadError
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

