from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from ai_film_studio.builder import create_default_builder
from ai_film_studio.cli import app
from ai_film_studio.reference_sheets import (
    ReferenceSelectionRequest,
    ReferenceSelectionService,
    ReferenceSelector,
)


def test_guriya_reference_selection_scenes_select_expected_first(tmp_path: Path) -> None:
    repo_root = _repo_root()
    service = ReferenceSelectionService.from_runtime(
        create_default_builder().build(),
        repo_root=repo_root,
        output_root=tmp_path,
    )

    scenarios = {
        "close_up_front": "front",
        "profile_left": "left_profile",
        "full_body_standing": "full_body_front",
    }
    for scene_name, expected_reference in scenarios.items():
        artifact = service.compile_scene(
            repo_root / f"projects/guriya/tests/reference_selection/{scene_name}.yaml",
            engine="gemini",
        )
        manifest = json.loads(Path(artifact.output_path).read_text(encoding="utf-8"))

        assert artifact.result.selected[0].name == expected_reference
        assert artifact.result.selected[0].score == 100
        assert len(artifact.result.selected) <= artifact.result.engine_reference_limit
        assert manifest["verification"]["matches_expected"] is True
        assert manifest["primary_reference"] == expected_reference


def test_select_references_cli_prints_debug_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_root()
    monkeypatch.chdir(repo_root)

    result = CliRunner().invoke(
        app,
        [
            "select-references",
            "projects/guriya/tests/reference_selection/close_up_front.yaml",
            "--engine",
            "gemini",
        ],
    )

    assert result.exit_code == 0
    assert "Character: guriya" in result.stdout
    assert "Shot: close_up" in result.stdout
    assert "Angle: front" in result.stdout
    assert "Score: 100" in result.stdout
    assert "Reason:" in result.stdout
    assert "Excluded:" in result.stdout
    assert "Engine reference limit: 4" in result.stdout


def test_rejected_and_unapproved_references_are_not_selected() -> None:
    asset = _selection_asset()
    asset["reference_images"]["views"]["front"]["status"] = "rejected"
    asset["reference_images"]["views"]["front"]["approved"] = False
    asset["reference_images"]["views"]["left_profile"]["status"] = "pending_review"
    asset["reference_images"]["views"]["left_profile"]["approved"] = False

    result = ReferenceSelector().explain(
        asset,
        ReferenceSelectionRequest(
            camera_shot_type="close_up",
            angle="front",
            framing="face",
            engine_reference_limit=4,
        ),
    )

    assert all(item.name != "front" for item in result.selected)
    assert all(item.name != "left_profile" for item in result.selected)
    assert any(
        item.name == "front" and item.reason == "rejected reference"
        for item in result.excluded
    )
    assert any(
        item.name == "left_profile" and item.reason == "not approved"
        for item in result.excluded
    )


def test_exact_missing_close_up_front_falls_back_to_three_quarter() -> None:
    asset = _selection_asset()
    asset["reference_images"]["views"]["front"]["approved"] = False
    asset["reference_images"]["views"]["front"]["status"] = "pending_review"

    result = ReferenceSelector().explain(
        asset,
        ReferenceSelectionRequest(
            camera_shot_type="close_up",
            angle="front",
            framing="face",
            engine_reference_limit=4,
        ),
    )

    assert result.selected[0].name == "three_quarter_left"
    assert "fallback" in result.selected[0].reason


def test_exact_missing_profile_left_falls_back_to_three_quarter_left() -> None:
    asset = _selection_asset()
    asset["reference_images"]["views"]["left_profile"]["approved"] = False
    asset["reference_images"]["views"]["left_profile"]["status"] = "pending_review"

    result = ReferenceSelector().explain(
        asset,
        ReferenceSelectionRequest(
            camera_shot_type="close_up",
            angle="profile_left",
            framing="face",
            engine_reference_limit=4,
        ),
    )

    assert result.selected[0].name == "three_quarter_left"
    assert "fallback" in result.selected[0].reason


def test_full_body_does_not_use_portrait_fallback_without_flag() -> None:
    asset = _selection_asset()
    asset["reference_images"]["views"]["full_body_front"]["approved"] = False
    asset["reference_images"]["views"]["full_body_front"]["status"] = "pending_review"

    strict = ReferenceSelector().explain(
        asset,
        ReferenceSelectionRequest(
            camera_shot_type="full_body",
            angle="front",
            framing="full_body",
            pose="standing",
            engine_reference_limit=4,
        ),
    )
    weak = ReferenceSelector().explain(
        asset,
        ReferenceSelectionRequest(
            camera_shot_type="full_body",
            angle="front",
            framing="full_body",
            pose="standing",
            engine_reference_limit=4,
            allow_weak_fallbacks=True,
        ),
    )

    assert strict.selected == ()
    assert weak.selected[0].name == "front"
    assert "weak fallback allowed" in weak.selected[0].reason


def test_reference_selection_scene_files_have_expected_shape() -> None:
    for path in (
        "close_up_front.yaml",
        "profile_left.yaml",
        "full_body_standing.yaml",
    ):
        data = yaml.safe_load(
            (_repo_root() / "projects/guriya/tests/reference_selection" / path).read_text(
                encoding="utf-8",
            ),
        )
        assert data["project"] == "guriya"
        assert data["character"] == "guriya"
        assert data["expected_reference"]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _selection_asset() -> dict[str, Any]:
    def view(
        *,
        path: str,
        tags: list[str],
        shot_types: list[str],
        camera_angles: list[str],
        priority: int,
    ) -> dict[str, Any]:
        return {
            "path": path,
            "tags": tags,
            "shot_types": shot_types,
            "camera_angles": camera_angles,
            "priority": priority,
            "approved": True,
            "status": "approved",
        }

    return {
        "id": "guriya",
        "reference_images": {
            "views": {
                "front": view(
                    path="references/views/front.png",
                    tags=["front", "portrait", "close_up", "identity"],
                    shot_types=["close_up", "portrait"],
                    camera_angles=["front"],
                    priority=10,
                ),
                "left_profile": view(
                    path="references/views/left_profile.png",
                    tags=["left", "profile", "profile_left", "close_up"],
                    shot_types=["close_up", "portrait", "profile"],
                    camera_angles=["left", "profile_left"],
                    priority=15,
                ),
                "three_quarter_left": view(
                    path="references/views/three_quarter_left.png",
                    tags=["three_quarter", "three_quarter_left", "left", "close_up"],
                    shot_types=["close_up", "portrait", "three_quarter"],
                    camera_angles=["three_quarter_left", "left"],
                    priority=20,
                ),
                "three_quarter_right": view(
                    path="references/views/three_quarter_right.png",
                    tags=["three_quarter", "three_quarter_right", "right", "close_up"],
                    shot_types=["close_up", "portrait", "three_quarter"],
                    camera_angles=["three_quarter_right", "right"],
                    priority=25,
                ),
                "full_body_front": view(
                    path="references/views/full_body_front.png",
                    tags=["full_body", "standing", "front", "wardrobe"],
                    shot_types=["full_body", "wide"],
                    camera_angles=["front"],
                    priority=30,
                ),
            },
        },
    }
