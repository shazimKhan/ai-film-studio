"""Dynamic module loader."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
from typing import Any, cast

import yaml
from yaml import YAMLError

from ai_film_studio.core.exceptions import (
    InvalidYAMLError,
    MalformedConfigurationError,
    ModuleLoadError,
)
from ai_film_studio.module_loader.models import LoadedDataModule, ModuleSpec

YAML_SUFFIXES = {".yaml", ".yml"}
MARKDOWN_SUFFIXES = {".md", ".markdown"}


class ModuleLoader:
    """Loads framework modules by import path or Python entry point group."""

    def load(self, spec: ModuleSpec | str) -> Any:
        """Load a module or attribute."""
        module_spec = self._coerce_spec(spec)
        try:
            module = import_module(module_spec.import_path)
        except ImportError as exc:
            msg = f"Could not import module '{module_spec.import_path}'."
            raise ModuleLoadError(msg) from exc

        if module_spec.attribute is None:
            return module

        try:
            return getattr(module, module_spec.attribute)
        except AttributeError as exc:
            msg = (
                f"Module '{module_spec.import_path}' does not expose "
                f"'{module_spec.attribute}'."
            )
            raise ModuleLoadError(msg) from exc

    def iter_entry_points(self, group: str) -> tuple[EntryPoint, ...]:
        """Return entry points for an extension group."""
        return tuple(entry_points().select(group=group))

    def load_entry_points(self, group: str) -> dict[str, Any]:
        """Load all entry points for an extension group keyed by entry point name."""
        loaded: dict[str, Any] = {}
        for entry_point in self.iter_entry_points(group):
            try:
                loaded[entry_point.name] = entry_point.load()
            except Exception as exc:
                msg = f"Could not load entry point '{entry_point.name}' from group '{group}'."
                raise ModuleLoadError(msg) from exc

        return loaded

    def load_data_module(self, path: Path) -> LoadedDataModule:
        """Load a reusable YAML or Markdown module from disk."""
        suffix = path.suffix.lower()
        if suffix in YAML_SUFFIXES:
            return LoadedDataModule(path=path, kind="yaml", data=self.load_yaml_file(path))
        if suffix in MARKDOWN_SUFFIXES:
            return LoadedDataModule(path=path, kind="markdown", data=self.load_markdown_file(path))

        supported = ", ".join(sorted((*YAML_SUFFIXES, *MARKDOWN_SUFFIXES)))
        msg = f"Unsupported module file type for '{path}'. Supported types: {supported}."
        raise ModuleLoadError(msg)

    def load_yaml_file(self, path: Path) -> dict[str, Any]:
        """Load a YAML mapping from disk."""
        text = self._read_text(path)
        try:
            data = yaml.safe_load(text)
        except YAMLError as exc:
            msg = f"Invalid YAML in '{path}': {exc}"
            raise InvalidYAMLError(msg) from exc

        if data is None:
            msg = f"YAML module '{path}' is empty."
            raise MalformedConfigurationError(msg)
        if not isinstance(data, dict):
            msg = f"YAML module '{path}' must contain a mapping at the top level."
            raise MalformedConfigurationError(msg)

        return cast(dict[str, Any], data)

    def load_markdown_file(self, path: Path) -> str:
        """Load a Markdown module from disk."""
        text = self._read_text(path)
        if not text.strip():
            msg = f"Markdown module '{path}' is empty."
            raise MalformedConfigurationError(msg)
        return text

    @staticmethod
    def _coerce_spec(spec: ModuleSpec | str) -> ModuleSpec:
        if isinstance(spec, ModuleSpec):
            return spec

        import_path, separator, attribute = spec.partition(":")
        return ModuleSpec(
            import_path=import_path,
            attribute=attribute if separator else None,
        )

    @staticmethod
    def _read_text(path: Path) -> str:
        if not path.exists():
            msg = f"Module file '{path}' does not exist."
            raise ModuleLoadError(msg)
        if not path.is_file():
            msg = f"Module path '{path}' is not a file."
            raise ModuleLoadError(msg)

        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"Could not read module file '{path}': {exc}"
            raise ModuleLoadError(msg) from exc
