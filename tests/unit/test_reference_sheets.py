from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from PIL import Image, ImageDraw
from typer.testing import CliRunner

from ai_film_studio.cli import app
from ai_film_studio.core.exceptions import ReferenceSheetError
from ai_film_studio.engine_adapters.gemini import GeminiAdapter
from ai_film_studio.reference_sheets import (
    ReferenceApprovalService,
    ReferenceOutputFormat,
    ReferenceSelectionRequest,
    ReferenceSelector,
    ReferenceSheetSplitter,
    SplitOptions,
)


def test_successful_4x2_split_writes_files_manifest_preview_and_yaml(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)
    source_checksum = _sha256(source)

    result = ReferenceSheetSplitter(repo_root=repo_root).split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(min_width=50, min_height=50),
    )

    assert _sha256(source) == source_checksum
    assert len(result.generated_files) == 8
    assert {Path(item.path).name for item in result.generated_files} == {
        "front.png",
        "left_profile.png",
        "three_quarter_left.png",
        "three_quarter_right.png",
        "full_body_front.png",
        "full_body_back_left.png",
        "full_body_back.png",
        "seated_front.png",
    }
    front = next(item for item in result.generated_files if item.name == "front")
    assert front.pixel_crop.left == 0
    assert front.pixel_crop.top == 0
    assert front.pixel_crop.right == 200
    assert front.pixel_crop.bottom == 200
    assert front.width == 200
    assert front.height == 200
    assert (repo_root / result.preview_path).is_file()
    assert (repo_root / result.manifest_path).is_file()

    manifest = json.loads((repo_root / result.manifest_path).read_text(encoding="utf-8"))
    assert manifest["panel_count"] == 8
    assert manifest["source_checksum"] == _sha256(
        repo_root / "projects/demo/characters/hero/references/master/master_sheet.png",
    )
    assert manifest["checksums"]["crops"]["front"] == front.checksum
    assert all(not Path(item["path"]).is_absolute() for item in manifest["generated_files"])

    character_yaml = repo_root / "projects/demo/characters/hero/character.yaml"
    assert character_yaml.with_suffix(".yaml.bak").is_file()
    character_data = yaml.safe_load(character_yaml.read_text(encoding="utf-8"))
    assert character_data["custom_field"] == "keep_me"
    assert character_data["reference_images"]["master_sheet"]["approved"] is False
    assert character_data["reference_images"]["views"]["front"]["status"] == "pending_review"
    front_path = character_data["reference_images"]["views"]["front"]["path"]
    assert front_path == "references/views/front.png"


def test_split_reference_sheet_cli_runs_from_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, source = _write_reference_project(tmp_path)
    monkeypatch.chdir(repo_root)

    result = CliRunner().invoke(
        app,
        [
            "split-reference-sheet",
            str(source.relative_to(repo_root)),
            "--project",
            "demo",
            "--character",
            "hero",
            "--layout",
            "test_grid",
            "--min-width",
            "50",
            "--min-height",
            "50",
        ],
    )

    assert result.exit_code == 0
    assert "Reference manifest written to:" in result.stdout
    assert "front" in result.stdout
    assert (repo_root / "projects/demo/characters/hero/references/views/front.png").is_file()


def test_dry_run_does_not_write_crop_files(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)

    result = ReferenceSheetSplitter(repo_root=repo_root).split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(min_width=50, min_height=50, dry_run=True),
    )

    assert result.dry_run is True
    assert result.generated_files == ()
    assert result.planned_crops
    assert not (repo_root / "projects/demo/characters/hero/references/views").exists()
    manifest_path = (
        repo_root / "projects/demo/characters/hero/references/reference_sheet_manifest.json"
    )
    assert not manifest_path.exists()


def test_preview_command_path_creates_preview_without_crops(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)

    result = ReferenceSheetSplitter(repo_root=repo_root).preview(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(min_width=50, min_height=50),
    )

    assert result.preview_path == (
        "projects/demo/characters/hero/references/master/master_sheet_preview.png"
    )
    assert (repo_root / result.preview_path).is_file()
    assert not (repo_root / "projects/demo/characters/hero/references/views").exists()


def test_invalid_layout_is_reported(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)

    with pytest.raises(ReferenceSheetError, match="was not found"):
        ReferenceSheetSplitter(repo_root=repo_root).split(
            source,
            project="demo",
            character="hero",
            layout_id="missing_layout",
            options=SplitOptions(min_width=50, min_height=50),
        )


def test_crop_outside_bounds_is_rejected(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)
    _write_layout(
        repo_root,
        """
id: bad_crop
rows: 1
columns: 1
panels:
  - name: outside
    output_filename: outside.png
    crop:
      x: 0.9
      y: 0
      width: 0.2
      height: 1
""",
    )

    with pytest.raises(ReferenceSheetError, match="Invalid reference sheet layout"):
        ReferenceSheetSplitter(repo_root=repo_root).split(
            source,
            project="demo",
            character="hero",
            layout_id="bad_crop",
            options=SplitOptions(min_width=50, min_height=50),
        )


def test_min_resolution_is_enforced(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)

    with pytest.raises(ReferenceSheetError, match="below minimum"):
        ReferenceSheetSplitter(repo_root=repo_root).split(
            source,
            project="demo",
            character="hero",
            layout_id="test_grid",
            options=SplitOptions(min_width=250, min_height=50),
        )


def test_output_versioning_and_overwrite(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)
    splitter = ReferenceSheetSplitter(repo_root=repo_root)
    splitter.split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(min_width=50, min_height=50),
    )

    versioned = splitter.split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(min_width=50, min_height=50),
    )
    assert any(Path(item.path).name == "front_v2.png" for item in versioned.generated_files)

    overwritten = splitter.split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(min_width=50, min_height=50, overwrite=True),
    )
    assert any(Path(item.path).name == "front.png" for item in overwritten.generated_files)


def test_approval_rejection_and_selector_behaviour(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)
    ReferenceSheetSplitter(repo_root=repo_root).split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(min_width=50, min_height=50),
    )
    approvals = ReferenceApprovalService(repo_root=repo_root)
    approvals.approve(project="demo", character="hero", reference="front")
    approvals.approve(project="demo", character="hero", reference="three_quarter_left")
    approvals.reject(
        project="demo",
        character="hero",
        reference="three_quarter_right",
        reason="blurred edge",
    )

    character_yaml = repo_root / "projects/demo/characters/hero/character.yaml"
    selector = ReferenceSelector()
    selected = selector.select_from_yaml(
        character_yaml,
        ReferenceSelectionRequest(
            camera_shot_type="close_up",
            angle="front",
            engine_reference_limit=3,
        ),
    )

    assert [item.name for item in selected] == ["front", "three_quarter_left"]
    rejected_data = yaml.safe_load(character_yaml.read_text(encoding="utf-8"))
    assert rejected_data["reference_images"]["views"]["three_quarter_right"]["status"] == "rejected"


def test_selector_matches_profiles_full_body_back_and_seated(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)
    ReferenceSheetSplitter(repo_root=repo_root).split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(min_width=50, min_height=50),
    )
    approvals = ReferenceApprovalService(repo_root=repo_root)
    for reference in (
        "left_profile",
        "full_body_front",
        "full_body_back_left",
        "full_body_back",
        "seated_front",
    ):
        approvals.approve(project="demo", character="hero", reference=reference)

    character_yaml = repo_root / "projects/demo/characters/hero/character.yaml"
    selector = ReferenceSelector()

    profile = selector.select_from_yaml(
        character_yaml,
        ReferenceSelectionRequest(angle="profile_left", engine_reference_limit=2),
    )
    full_body = selector.select_from_yaml(
        character_yaml,
        ReferenceSelectionRequest(camera_shot_type="full_body", pose="standing"),
    )
    back = selector.select_from_yaml(
        character_yaml,
        ReferenceSelectionRequest(angle="back_view", engine_reference_limit=2),
    )
    seated = selector.select_from_yaml(
        character_yaml,
        ReferenceSelectionRequest(pose="seated"),
    )

    assert profile[0].name == "left_profile"
    assert full_body[0].name == "full_body_front"
    assert [item.name for item in back] == ["full_body_back", "full_body_back_left"]
    assert seated[0].name == "seated_front"


def test_selector_respects_engine_reference_count(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)
    ReferenceSheetSplitter(repo_root=repo_root).split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(min_width=50, min_height=50),
    )
    approvals = ReferenceApprovalService(repo_root=repo_root)
    for reference in ("front", "left_profile", "three_quarter_left", "three_quarter_right"):
        approvals.approve(project="demo", character="hero", reference=reference)

    engine_capabilities = GeminiAdapter().reference_capabilities
    selected = ReferenceSelector().select_from_yaml(
        repo_root / "projects/demo/characters/hero/character.yaml",
        ReferenceSelectionRequest(
            camera_shot_type="close_up",
            engine_reference_limit=min(2, engine_capabilities.max_character_reference_images),
            preferred_reference_types=engine_capabilities.preferred_reference_types,
        ),
    )

    assert engine_capabilities.supports_multiple_references is True
    assert len(selected) == 2


def test_manual_overrides_take_priority_over_grid(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)
    overrides = repo_root / "overrides.yaml"
    overrides.write_text(
        """
panels:
  front:
    x: 0.25
    y: 0
    width: 0.25
    height: 0.5
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = ReferenceSheetSplitter(repo_root=repo_root).split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(min_width=50, min_height=50),
        overrides_path=overrides,
    )

    front = next(item for item in result.generated_files if item.name == "front")
    assert front.pixel_crop.left == 200
    assert front.pixel_crop.right == 400


def test_jpg_and_webp_output_formats_are_supported(tmp_path: Path) -> None:
    repo_root, source = _write_reference_project(tmp_path)
    splitter = ReferenceSheetSplitter(repo_root=repo_root)
    jpg = splitter.split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(
            output_format=ReferenceOutputFormat.JPG,
            min_width=50,
            min_height=50,
        ),
    )
    assert all(Path(item.path).suffix == ".jpg" for item in jpg.generated_files)

    webp = splitter.split(
        source,
        project="demo",
        character="hero",
        layout_id="test_grid",
        options=SplitOptions(
            output_format=ReferenceOutputFormat.WEBP,
            min_width=50,
            min_height=50,
        ),
    )
    assert all(Path(item.path).suffix == ".webp" for item in webp.generated_files)


def _write_reference_project(root: Path) -> tuple[Path, Path]:
    repo_root = root / "repo"
    _write_layout(repo_root, _layout_yaml())
    character_dir = repo_root / "projects/demo/characters/hero"
    (character_dir / "references/master").mkdir(parents=True, exist_ok=True)
    for child in ("poses", "expressions", "wardrobe", "voice"):
        (character_dir / child).mkdir(parents=True, exist_ok=True)
    (character_dir / "character.yaml").write_text(
        """
id: hero
asset_type: character
reference_status: awaiting_reference
custom_field: keep_me
""".strip()
        + "\n",
        encoding="utf-8",
    )
    source = character_dir / "references/master/source.png"
    _write_grid_image(source)
    return repo_root, source


def _write_layout(repo_root: Path, content: str) -> None:
    layout_dir = repo_root / "templates/reference_sheet_layouts"
    layout_dir.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load(content)
    layout_id = data["id"]
    (layout_dir / f"{layout_id}.yaml").write_text(content.strip() + "\n", encoding="utf-8")


def _write_grid_image(path: Path) -> None:
    image = Image.new("RGB", (800, 400), "white")
    draw = ImageDraw.Draw(image)
    colors = (
        "red",
        "green",
        "blue",
        "purple",
        "orange",
        "yellow",
        "cyan",
        "magenta",
    )
    for index, color in enumerate(colors):
        row = index // 4
        column = index % 4
        draw.rectangle(
            (column * 200, row * 200, (column + 1) * 200 - 1, (row + 1) * 200 - 1),
            fill=color,
        )
    image.save(path, format="PNG")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _layout_yaml() -> str:
    panels: list[dict[str, Any]] = [
        {
            "name": "front",
            "output_filename": "front.png",
            "row": 0,
            "column": 0,
            "tags": ["front", "portrait", "close_up"],
            "shot_types": ["close_up", "portrait"],
            "camera_angles": ["front"],
            "priority": 10,
        },
        {
            "name": "left_profile",
            "output_filename": "left_profile.png",
            "row": 0,
            "column": 1,
            "tags": ["left", "profile", "profile_left", "close_up"],
            "shot_types": ["close_up", "profile"],
            "camera_angles": ["profile_left", "left"],
            "priority": 15,
        },
        {
            "name": "three_quarter_left",
            "output_filename": "three_quarter_left.png",
            "row": 0,
            "column": 2,
            "tags": ["three_quarter", "three_quarter_left", "left", "close_up"],
            "shot_types": ["close_up", "three_quarter"],
            "camera_angles": ["three_quarter_left", "left"],
            "priority": 20,
        },
        {
            "name": "three_quarter_right",
            "output_filename": "three_quarter_right.png",
            "row": 0,
            "column": 3,
            "tags": ["three_quarter", "three_quarter_right", "right", "close_up"],
            "shot_types": ["close_up", "three_quarter"],
            "camera_angles": ["three_quarter_right", "right"],
            "priority": 25,
        },
        {
            "name": "full_body_front",
            "output_filename": "full_body_front.png",
            "row": 1,
            "column": 0,
            "tags": ["full_body", "standing", "front"],
            "shot_types": ["full_body", "wide"],
            "camera_angles": ["front"],
            "priority": 30,
        },
        {
            "name": "full_body_back_left",
            "output_filename": "full_body_back_left.png",
            "row": 1,
            "column": 1,
            "tags": ["full_body", "back", "back_left", "standing"],
            "shot_types": ["full_body", "wide"],
            "camera_angles": ["back_left", "back_view"],
            "priority": 35,
        },
        {
            "name": "full_body_back",
            "output_filename": "full_body_back.png",
            "row": 1,
            "column": 2,
            "tags": ["full_body", "back", "back_view", "standing"],
            "shot_types": ["full_body", "wide"],
            "camera_angles": ["back", "back_view"],
            "priority": 32,
        },
        {
            "name": "seated_front",
            "output_filename": "seated_front.png",
            "row": 1,
            "column": 3,
            "tags": ["seated", "sitting", "front"],
            "shot_types": ["medium", "full_body"],
            "camera_angles": ["front"],
            "priority": 40,
        },
    ]
    return yaml.safe_dump(
        {"id": "test_grid", "rows": 2, "columns": 4, "panels": panels},
        sort_keys=False,
    )
