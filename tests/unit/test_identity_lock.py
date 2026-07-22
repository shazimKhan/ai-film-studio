from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_film_studio.asset_bible import IdentityLockService
from ai_film_studio.builder import create_default_builder
from ai_film_studio.cli import app
from ai_film_studio.core.exceptions import MalformedConfigurationError
from ai_film_studio.prompt_compiler import PromptCompilationService

CANONICAL_TEST_REFERENCE = "projects/demo/assets/storyteller_master.png"


def test_approved_strict_identity_loads(tmp_path: Path) -> None:
    project_root = _write_identity_fixture(tmp_path)

    identity = IdentityLockService(repo_root=tmp_path).load_identity(
        Path("projects/demo"),
        "storyteller",
    )

    assert identity.identity_id == "demo_storyteller_v1"
    assert identity.status == "approved"
    assert identity.lock_level == "strict"
    assert identity.reference_image is not None
    assert identity.reference_image.path == CANONICAL_TEST_REFERENCE
    assert project_root.exists()


def test_locked_identity_missing_reference_fails(tmp_path: Path) -> None:
    _write_identity_fixture(tmp_path, create_reference=False)

    with pytest.raises(MalformedConfigurationError, match="identity.reference_missing"):
        IdentityLockService(repo_root=tmp_path).load_identity(
            Path("projects/demo"),
            "storyteller",
        )


def test_locked_unapproved_identity_fails(tmp_path: Path) -> None:
    _write_identity_fixture(tmp_path, status="under_review")

    with pytest.raises(MalformedConfigurationError, match="identity.locked_unapproved"):
        IdentityLockService(repo_root=tmp_path).load_identity(
            Path("projects/demo"),
            "storyteller",
        )


def test_strict_identity_without_immutable_attributes_fails(tmp_path: Path) -> None:
    _write_identity_fixture(tmp_path, immutable_attributes=())

    with pytest.raises(MalformedConfigurationError, match="identity.missing_immutable_attributes"):
        IdentityLockService(repo_root=tmp_path).load_identity(
            Path("projects/demo"),
            "storyteller",
        )


def test_strict_identity_without_continuity_prompt_fails(tmp_path: Path) -> None:
    _write_identity_fixture(tmp_path, continuity_prompt=None)

    with pytest.raises(MalformedConfigurationError, match="identity.missing_continuity_prompt"):
        IdentityLockService(repo_root=tmp_path).load_identity(
            Path("projects/demo"),
            "storyteller",
        )


def test_duplicate_identity_ids_fail_project_validation(tmp_path: Path) -> None:
    _write_identity_fixture(tmp_path, character_id="storyteller")
    _write_identity_fixture(tmp_path, character_id="narrator")

    issues = IdentityLockService(repo_root=tmp_path).validate_project(Path("projects/demo"))

    assert [issue.code for issue in issues] == ["identity.duplicate_id"]


def test_prompt_compiler_injects_identity_lock_and_reference_metadata(tmp_path: Path) -> None:
    scene_file = _write_compiler_fixture(tmp_path, duplicate_character=True)
    service = _service(tmp_path, tmp_path / "output")

    artifact = service.compile(scene_file, "gemini")

    assert artifact.prompt.count("CHARACTER IDENTITY CONTINUITY — MANDATORY") == 1
    assert "Use the approved Storyteller master identity reference exactly." in artifact.prompt
    assert "Do not change the Storyteller face" in artifact.prompt
    assert "MANDATORY REFERENCE ASSETS" in artifact.prompt
    assert artifact.compiled.metadata["reference_assets"] == [
        {
            "character_id": "storyteller",
            "identity_id": "demo_storyteller_v1",
            "path": CANONICAL_TEST_REFERENCE,
            "required": True,
            "identity_lock": "strict",
        },
    ]
    assert artifact.engine_request.metadata["reference_assets"] == artifact.compiled.metadata[
        "reference_assets"
    ]
    assert artifact.engine_request.assets["reference_assets"] == artifact.compiled.metadata[
        "reference_assets"
    ]


def test_unlocked_characters_do_not_get_identity_metadata(tmp_path: Path) -> None:
    scene_file = _write_compiler_fixture(tmp_path, include_identity=False)
    service = _service(tmp_path, tmp_path / "output")

    artifact = service.compile(scene_file, "gemini")

    assert "CHARACTER IDENTITY CONTINUITY — MANDATORY" not in artifact.prompt
    assert "reference_assets" not in artifact.compiled.metadata
    assert artifact.engine_request.assets == {}


def test_validate_identity_cli_reports_canonical_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_identity_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        app,
        ["validate-identity", "--project", "demo", "--character", "storyteller"],
    )

    assert result.exit_code == 0
    assert "Character: storyteller" in result.stdout
    assert "Identity: demo_storyteller_v1" in result.stdout
    assert f"Reference image: {CANONICAL_TEST_REFERENCE}" in result.stdout
    assert "Validation: passed" in result.stdout


def _service(repo_root: Path, output_root: Path) -> PromptCompilationService:
    runtime = create_default_builder().build()
    return PromptCompilationService.from_runtime(
        runtime,
        repo_root=repo_root,
        output_root=output_root,
    )


def _write_compiler_fixture(
    root: Path,
    *,
    include_identity: bool = True,
    duplicate_character: bool = False,
) -> Path:
    project_root = root / "projects" / "demo"
    character_dir = project_root / "characters"
    world_dir = project_root / "worlds"
    scene_dir = project_root / "episode_01" / "scene_01"
    character_dir.mkdir(parents=True)
    world_dir.mkdir(parents=True)
    scene_dir.mkdir(parents=True)

    if include_identity:
        _write_identity_fixture(root)

    (character_dir / "storyteller.yaml").write_text(
        """
id: storyteller
name: Storyteller
age: "30 to 35"
appearance: "Mature thoughtful face, neatly trimmed beard, and composed eyes."
wardrobe: "Charcoal kurta and simple waistcoat."
hair: "Neatly kept dark hair."
personality: "Calm, reflective, and restrained."
performance_constraints:
  - "Maintain the approved narrator identity."
  - "Keep the expression controlled."
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (world_dir / "studio.yaml").write_text(
        """
id: studio
name: "Storyteller Studio"
period: "modern documentary"
location: "controlled studio"
description: "Wooden desk, warm light, and unreadable books."
visual_rules:
  - "No readable text."
textures:
  - "wood"
  - "paper"
atmosphere: "Serious and reflective."
soundscape: "quiet room tone"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    character_entries = """
  - id: storyteller
    module: ../../characters/storyteller.yaml
    role: "primary narrator"
""".rstrip()
    if duplicate_character:
        character_entries += """
  - id: storyteller
    module: ../../characters/storyteller.yaml
    role: "same narrator alternate framing"
""".rstrip()

    scene_file = scene_dir / "clip_001.yaml"
    scene_file.write_text(
        f"""
project: demo
episode: episode_01
scene: scene_01
clip: clip_001
title: "Identity Lock Test"
duration: 6
action: "The storyteller looks into camera."
emotion: "serious reflection"
characters:
{character_entries}
world:
  id: studio
  module: ../../worlds/studio.yaml
camera:
  shot_size: "close-up"
  angle: "front"
  lens: "50mm"
  movement: "locked-off"
  framing: "face and shoulders"
  focus: "eyes sharp"
lighting:
  quality: "soft"
  source: "desk lamp"
  color_temperature: "warm"
  contrast: "gentle"
  mood: "reflective"
motion:
  subject: "subtle breathing"
  environment: "still"
  camera: "static"
  pace: "slow"
continuity:
  previous_clip: "Opening."
  visual_state: "Same desk."
  prop_state: "Books remain unreadable."
  emotional_state: "Composed."
negative prompts:
  - "readable text"
  - "plastic skin"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return scene_file


def _write_identity_fixture(
    root: Path,
    *,
    character_id: str = "storyteller",
    status: str = "approved",
    create_reference: bool = True,
    immutable_attributes: tuple[str, ...] = ("Mature thoughtful face.",),
    continuity_prompt: str | None = (
        "Use the approved Storyteller master identity reference exactly."
    ),
) -> Path:
    project_root = root / "projects" / "demo"
    identity_dir = project_root / "05_characters" / character_id
    reference_path = root / CANONICAL_TEST_REFERENCE
    identity_dir.mkdir(parents=True, exist_ok=True)
    reference_path.parent.mkdir(parents=True, exist_ok=True)
    if create_reference:
        reference_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    immutable_yaml = "\n".join(f"  - {item}" for item in immutable_attributes)
    continuity_yaml = (
        f"continuity_prompt: >\n  {continuity_prompt}\n"
        if continuity_prompt is not None
        else ""
    )
    (identity_dir / "identity.yaml").write_text(
        f"""
schema_version: "1.0"
project_id: demo
character_id: {character_id}
identity_id: demo_storyteller_v1
status: {status}
identity_locked: true
lock_level: strict
validation_status: approved
canonical_reference:
  path: {CANONICAL_TEST_REFERENCE}
  filename: storyteller_master.png
  version: v1
reference_image:
  path: {CANONICAL_TEST_REFERENCE}
  filename: storyteller_master.png
  required: true
immutable_attributes:
{immutable_yaml}
mutable_attributes:
  - Camera angle.
{continuity_yaml}negative_continuity_prompt: >
  Do not change the Storyteller face.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return project_root
