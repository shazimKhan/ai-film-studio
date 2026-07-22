from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ai_film_studio.asset_bible import IdentityLockService
from ai_film_studio.builder import create_default_builder
from ai_film_studio.cli import app
from ai_film_studio.prompt_compiler import PromptCompilationService

PRE_REFERENCE = "projects/demo/assets/iblis_pre_rebellion_master.png"
POST_REFERENCE = "projects/demo/assets/iblis_post_expulsion_master.png"


def test_character_state_resolves_default_state(tmp_path: Path) -> None:
    _write_state_fixture(tmp_path)

    identity = IdentityLockService(repo_root=tmp_path).load_identity(
        Path("projects/demo"),
        "iblis",
    )
    state = IdentityLockService(repo_root=tmp_path).resolve_state(identity)

    assert state is not None
    assert state.state_id == "pre_rebellion"
    assert state.reference_image is not None
    assert state.reference_image.path == PRE_REFERENCE


def test_character_state_resolves_explicit_state(tmp_path: Path) -> None:
    _write_state_fixture(tmp_path)

    state = IdentityLockService(repo_root=tmp_path).load_state(
        Path("projects/demo"),
        "iblis",
        "post_expulsion",
    )

    assert state is not None
    assert state.state_id == "post_expulsion"
    assert state.reference_image is not None
    assert state.reference_image.path == POST_REFERENCE


def test_prompt_compiler_injects_character_state_continuity(tmp_path: Path) -> None:
    scene_file = _write_compiler_fixture(tmp_path, state="post_expulsion")
    artifact = _service(tmp_path, tmp_path / "output").compile(scene_file, "gemini")

    assert "CHARACTER IDENTITY CONTINUITY — MANDATORY" in artifact.prompt
    assert "CHARACTER STATE CONTINUITY — MANDATORY" in artifact.prompt
    assert "State ID: post_expulsion" in artifact.prompt
    assert "Use Iblis after expulsion." in artifact.prompt
    assert "Do not return to pre-rebellion radiance." in artifact.prompt
    assert artifact.compiled.metadata["character_states"] == [
        {
            "character_id": "iblis",
            "identity_id": "demo_iblis_v1",
            "state_id": "post_expulsion",
            "status": "approved",
            "reference_status": "approved",
            "master_prompt_path": "projects/demo/prompts/iblis_post.yaml",
        },
    ]
    assert {
        "character_id": "iblis",
        "identity_id": "demo_iblis_v1",
        "state_id": "post_expulsion",
        "path": POST_REFERENCE,
        "required": True,
        "identity_lock": "strict",
        "reference_role": "state",
    } in artifact.compiled.metadata["reference_assets"]


def test_prompt_compiler_uses_default_state_when_omitted(tmp_path: Path) -> None:
    scene_file = _write_compiler_fixture(tmp_path, state=None)
    artifact = _service(tmp_path, tmp_path / "output").compile(scene_file, "gemini")

    assert "State ID: pre_rebellion" in artifact.prompt
    assert artifact.compiled.metadata["character_states"][0]["state_id"] == "pre_rebellion"


def test_character_state_cli_status_and_validate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_state_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    status = runner.invoke(
        app,
        ["character-state", "status", "--project", "demo", "--character", "iblis"],
    )
    validate = runner.invoke(
        app,
        ["character-state", "validate", "--project", "demo", "--character", "iblis"],
    )

    assert status.exit_code == 0
    assert "Default state: pre_rebellion" in status.stdout
    assert "post_expulsion" in status.stdout
    assert validate.exit_code == 0
    assert "States: 2" in validate.stdout
    assert "Validation: passed" in validate.stdout


def _service(repo_root: Path, output_root: Path) -> PromptCompilationService:
    runtime = create_default_builder().build()
    return PromptCompilationService.from_runtime(
        runtime,
        repo_root=repo_root,
        output_root=output_root,
    )


def _write_compiler_fixture(root: Path, *, state: str | None) -> Path:
    _write_state_fixture(root)
    project_root = root / "projects" / "demo"
    character_dir = project_root / "characters"
    world_dir = project_root / "worlds"
    scene_dir = project_root / "episode_01" / "scene_01"
    character_dir.mkdir(parents=True, exist_ok=True)
    world_dir.mkdir(parents=True, exist_ok=True)
    scene_dir.mkdir(parents=True, exist_ok=True)

    (character_dir / "iblis.yaml").write_text(
        """
id: iblis
name: Iblis
age: "unseen"
appearance: "Symbolic jinn presence with hidden face."
wardrobe: "State-specific symbolic robes."
hair: "Hidden."
personality: "Disciplined before rebellion and disgraced after expulsion."
performance_constraints:
  - "Iblis is jinn, not angel."
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (world_dir / "realm.yaml").write_text(
        """
id: realm
name: "Unseen Realm"
period: "pre-earth"
location: "abstract unseen realm"
description: "Source-less light and vast space."
visual_rules:
  - "No outer space."
textures:
  - "light"
  - "shadow"
atmosphere: "Reverent."
soundscape: "deep silence"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    state_line = f"\n    state: {state}" if state else ""
    scene_file = scene_dir / "clip_001.yaml"
    scene_file.write_text(
        f"""
project: demo
episode: episode_01
scene: scene_01
clip: clip_001
title: "State Test"
duration: 6
action: "Iblis remains still."
emotion: "solemn tension"
characters:
  - id: iblis
    module: ../../characters/iblis.yaml{state_line}
world:
  id: realm
  module: ../../worlds/realm.yaml
camera:
  shot_size: "medium"
  angle: "front"
  lens: "65mm"
  movement: "locked-off"
  framing: "symbolic figure"
  focus: "silhouette"
lighting:
  quality: "soft"
  source: "source-less light"
  color_temperature: "white-gold"
  contrast: "controlled"
  mood: "reverent"
motion:
  subject: "stillness"
  environment: "particles drift"
  camera: "static"
  pace: "slow"
continuity:
  previous_clip: "Assembly."
  visual_state: "State-aware continuity."
  prop_state: "No props."
  emotional_state: "Controlled."
negative prompts:
  - "horns"
  - "tail"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return scene_file


def _write_state_fixture(root: Path) -> None:
    project_root = root / "projects" / "demo"
    identity_dir = project_root / "05_characters" / "iblis"
    pre_state_dir = identity_dir / "states" / "pre_rebellion"
    post_state_dir = identity_dir / "states" / "post_expulsion"
    pre_reference = root / PRE_REFERENCE
    post_reference = root / POST_REFERENCE
    pre_state_dir.mkdir(parents=True, exist_ok=True)
    post_state_dir.mkdir(parents=True, exist_ok=True)
    pre_reference.parent.mkdir(parents=True, exist_ok=True)
    pre_reference.write_bytes(b"\x89PNG\r\n\x1a\n")
    post_reference.write_bytes(b"\x89PNG\r\n\x1a\n")

    (identity_dir / "identity.yaml").write_text(
        """
schema_version: "1.0"
project_id: demo
character_id: iblis
identity_id: demo_iblis_v1
status: stateful_identity_defined
identity_locked: false
lock_level: state_family
default_state: pre_rebellion
immutable_attributes:
  - Iblis is jinn, not angel.
continuity_prompt: >
  Preserve one Iblis identity family across all states.
negative_continuity_prompt: >
  Do not show Iblis as an angel or Western devil.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    _write_state_file(
        pre_state_dir / "state.yaml",
        state_id="pre_rebellion",
        reference=PRE_REFERENCE,
        prompt="projects/demo/prompts/iblis_pre.yaml",
        continuity="Use Iblis before rebellion.",
        negative="Do not show corruption.",
    )
    _write_state_file(
        post_state_dir / "state.yaml",
        state_id="post_expulsion",
        reference=POST_REFERENCE,
        prompt="projects/demo/prompts/iblis_post.yaml",
        continuity="Use Iblis after expulsion.",
        negative="Do not return to pre-rebellion radiance.",
    )


def _write_state_file(
    path: Path,
    *,
    state_id: str,
    reference: str,
    prompt: str,
    continuity: str,
    negative: str,
) -> None:
    path.write_text(
        f"""
schema_version: "1.0"
project_id: demo
character_id: iblis
identity_id: demo_iblis_v1
state_id: {state_id}
status: approved
identity_locked: true
lock_level: strict
reference_status: approved
master_prompt_path: {prompt}
reference_image:
  path: {reference}
  filename: {Path(reference).name}
  required: true
immutable_attributes:
  - Hidden face.
mutable_attributes:
  - Camera angle.
continuity_prompt: >
  {continuity}
negative_continuity_prompt: >
  {negative}
""".strip()
        + "\n",
        encoding="utf-8",
    )
