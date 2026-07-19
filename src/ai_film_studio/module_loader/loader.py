"""Dynamic module loader."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import EntryPoint, entry_points
from typing import Any

from ai_film_studio.core.exceptions import ModuleLoadError
from ai_film_studio.module_loader.models import ModuleSpec


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

    @staticmethod
    def _coerce_spec(spec: ModuleSpec | str) -> ModuleSpec:
        if isinstance(spec, ModuleSpec):
            return spec

        import_path, separator, attribute = spec.partition(":")
        return ModuleSpec(
            import_path=import_path,
            attribute=attribute if separator else None,
        )

