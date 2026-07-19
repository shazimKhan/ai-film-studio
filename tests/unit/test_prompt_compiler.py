from __future__ import annotations

from pathlib import Path

import pytest

from ai_film_studio.builder import create_default_builder
from ai_film_studio.core.exceptions import (
    AssetNotFoundError,
    InvalidYAMLError,
    MalformedConfigurationError,
    UnsupportedEngineError,
)
from ai_film_studio.prompt_compiler import PromptCompilationService
from ai_film_studio.prompt_compiler.sections import PromptSectionBuilder


def test_valid_compilation_writes_gemini_prompt(tmp_path: Path) -> None:
    project_root, scene_file = _write_project_fixture(tmp_path)
    service = _service(project_root, tmp_path / "output")

    artifact = service.compile(scene_file, "gemini")

    assert artifact.output_path == (
        tmp_path
        / "output"
        / "demo"
        / "episode_01"
        / "scene_02"
        / "clip_001"
        / "gemini_prompt_v1.txt"
    )
    assert artifact.output_path.exists()
    assert "GEMINI VIDEO PROMPT" in artifact.prompt
    assert "Project: demo" in artifact.prompt
    assert "Character identity" not in artifact.prompt
    assert "CHARACTER IDENTITY LOCK" in artifact.prompt


def test_missing_character_reference_raises_clear_error(tmp_path: Path) -> None:
    project_root, scene_file = _write_project_fixture(
        tmp_path,
        character_module="../../characters/missing.yaml",
    )
    service = _service(project_root, tmp_path / "output")

    with pytest.raises(AssetNotFoundError, match="Character asset 'hero' not found"):
        service.compile(scene_file, "gemini")


def test_invalid_yaml_raises_clear_error(tmp_path: Path) -> None:
    scene_file = tmp_path / "bad.yaml"
    scene_file.write_text("project: [unterminated\n", encoding="utf-8")
    service = _service(tmp_path, tmp_path / "output")

    with pytest.raises(InvalidYAMLError, match="Invalid YAML"):
        service.compile(scene_file, "gemini")


def test_unsupported_engine_raises_clear_error(tmp_path: Path) -> None:
    project_root, scene_file = _write_project_fixture(tmp_path)
    service = _service(project_root, tmp_path / "output")

    with pytest.raises(UnsupportedEngineError, match="Unsupported engine 'veo'"):
        service.compile(scene_file, "veo")


def test_output_versioning_does_not_overwrite(tmp_path: Path) -> None:
    project_root, scene_file = _write_project_fixture(tmp_path)
    service = _service(project_root, tmp_path / "output")

    first = service.compile(scene_file, "gemini")
    second = service.compile(scene_file, "gemini")

    assert first.output_path.name == "gemini_prompt_v1.txt"
    assert second.output_path.name == "gemini_prompt_v2.txt"
    assert first.output_path.read_text(encoding="utf-8") == second.output_path.read_text(
        encoding="utf-8",
    )


def test_generated_prompt_contains_required_sections(tmp_path: Path) -> None:
    project_root, scene_file = _write_project_fixture(tmp_path)
    service = _service(project_root, tmp_path / "output")

    artifact = service.compile(scene_file, "gemini")

    for section_title in PromptSectionBuilder.SECTION_TITLES:
        assert section_title in artifact.prompt


def test_invalid_duration_is_rejected(tmp_path: Path) -> None:
    project_root, scene_file = _write_project_fixture(tmp_path, duration=-1)
    service = _service(project_root, tmp_path / "output")

    with pytest.raises(MalformedConfigurationError, match="duration"):
        service.compile(scene_file, "gemini")


def _service(project_root: Path, output_root: Path) -> PromptCompilationService:
    runtime = create_default_builder().build()
    return PromptCompilationService.from_runtime(
        runtime,
        repo_root=project_root,
        output_root=output_root,
    )


def _write_project_fixture(
    root: Path,
    *,
    character_module: str = "../../characters/hero.yaml",
    duration: int = 6,
) -> tuple[Path, Path]:
    character_dir = root / "characters"
    world_dir = root / "worlds"
    scene_dir = root / "episode_01" / "scene_02"
    character_dir.mkdir(parents=True)
    world_dir.mkdir(parents=True)
    scene_dir.mkdir(parents=True)

    (character_dir / "hero.yaml").write_text(
        """
id: hero
name: Hero
age: "12"
appearance: "Consistent face, short dark hair, alert eyes, and a cautious expression."
wardrobe: "Plain cotton kurta and worn sandals."
hair: "Short, side-parted dark hair."
personality: "Observant, restrained, and brave under pressure."
performance_constraints:
  - "Maintain the same facial identity."
  - "Keep the performance subtle."
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (world_dir / "village.yaml").write_text(
        """
id: village
name: "Village"
period: "1980s"
location: "Rural Punjab"
description: "Dusty lane, handmade walls, and a quiet courtyard."
visual_rules:
  - "No modern devices."
textures:
  - "dust"
  - "cotton"
atmosphere: "Intimate and tense."
soundscape: "distant voices and wind through fabric"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    scene_file = scene_dir / "clip_001.yaml"
    scene_file.write_text(
        f"""
project: demo
episode: episode_01
scene: scene_02
clip: clip_001
title: "Test Clip"
duration: {duration}
action: "The hero pauses in the doorway and listens."
emotion: "contained anxiety"
characters:
  - id: hero
    module: {character_module}
    role: "primary subject"
world:
  id: village
  module: ../../worlds/village.yaml
camera:
  shot_size: "medium close-up"
  angle: "eye level"
  lens: "35mm"
  movement: "slow push-in"
  framing: "doorway frame"
  focus: "eyes sharp, background soft"
lighting:
  quality: "soft natural"
  source: "window light"
  color_temperature: "warm"
  contrast: "gentle"
  mood: "tense"
motion:
  subject: "small breath and stillness"
  environment: "dust moves in light"
  camera: "subtle push"
  pace: "slow"
continuity:
  previous_clip: "The hero heard a sound."
  visual_state: "Still in the doorway."
  prop_state: "No props move."
  emotional_state: "Anxious but controlled."
negative prompts:
  - "modern objects"
  - "text overlays"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return root, scene_file
