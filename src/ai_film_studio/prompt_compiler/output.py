"""Versioned prompt output writing."""

from __future__ import annotations

import re
from pathlib import Path

from ai_film_studio.core.exceptions import OutputWriteError
from ai_film_studio.prompt_compiler.models import SceneBlueprint


class VersionedPromptWriter:
    """Writes prompts without silently overwriting existing files."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root

    def write(self, scene: SceneBlueprint, engine_id: str, prompt: str) -> Path:
        """Write a prompt to the next versioned filename."""
        output_dir = self._scene_output_dir(scene)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            msg = f"Could not create output directory '{output_dir}': {exc}"
            raise OutputWriteError(msg) from exc

        output_path = self._next_prompt_path(output_dir, engine_id)
        try:
            output_path.write_text(prompt.rstrip() + "\n", encoding="utf-8")
        except OSError as exc:
            msg = f"Could not write prompt '{output_path}': {exc}"
            raise OutputWriteError(msg) from exc

        return output_path

    def _scene_output_dir(self, scene: SceneBlueprint) -> Path:
        return (
            self._output_root
            / _slug(scene.project)
            / _slug(scene.episode)
            / _slug(scene.scene)
            / _slug(scene.clip)
        )

    @staticmethod
    def _next_prompt_path(output_dir: Path, engine_id: str) -> Path:
        version = 1
        engine_slug = _slug(engine_id)
        while True:
            candidate = output_dir / f"{engine_slug}_prompt_v{version}.txt"
            if not candidate.exists():
                return candidate
            version += 1


def _slug(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9._-]+", "_", lowered)
    return slug.strip("_") or "untitled"
