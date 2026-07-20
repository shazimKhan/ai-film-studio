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


def test_guriya_reference_selection_scenes_ignore_legacy_crops_by_default(
    tmp_path: Path,
) -> None:
    repo_root = _repo_root()
    service = ReferenceSelectionService.from_runtime(
        create_default_builder().build(),
        repo_root=repo_root,
        output_root=tmp_path,
    )

    for scene_name in ("close_up_front", "profile_left", "full_body_standing"):
        artifact = service.compile_scene(
            repo_root / f"projects/guriya/tests/reference_selection/{scene_name}.yaml",
            engine="gemini",
        )
        manifest = json.loads(Path(artifact.output_path).read_text(encoding="utf-8"))

        assert artifact.result.selected == ()
        assert len(artifact.result.selected) <= artifact.result.engine_reference_limit
        assert manifest["verification"]["matches_expected"] is False
        assert manifest["primary_reference"] is None
        assert any(
            reference.reason == "preview references disabled"
            for reference in artifact.result.excluded
        )


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
    assert "Allow preview references: False" in result.stdout
    assert "- none" in result.stdout
    assert "preview references disabled" in result.stdout
    assert "Excluded:" in result.stdout
    assert "Engine reference limit: 4" in result.stdout


def test_rejected_and_unapproved_references_are_not_selected() -> None:
    asset = _selection_asset()
    asset["reference_images"]["production"]["front"]["status"] = "rejected"
    asset["reference_images"]["production"]["front"]["approved"] = False
    asset["reference_images"]["production"]["left_profile"]["status"] = "pending_review"
    asset["reference_images"]["production"]["left_profile"]["approved"] = False

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
    asset["reference_images"]["production"]["front"]["approved"] = False
    asset["reference_images"]["production"]["front"]["status"] = "pending_review"

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
    asset["reference_images"]["production"]["left_profile"]["approved"] = False
    asset["reference_images"]["production"]["left_profile"]["status"] = "pending_review"

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
    asset["reference_images"]["production"]["full_body_front"]["approved"] = False
    asset["reference_images"]["production"]["full_body_front"]["status"] = "pending_review"

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


def test_master_sheet_is_ignored_by_default() -> None:
    result = ReferenceSelector().explain(
        {
            "id": "guriya",
            "reference_images": {
                "master_sheet": {
                    "path": "references/master/master_sheet.png",
                    "source_type": "master_sheet",
                    "production_selectable": False,
                    "approved": True,
                    "status": "approved",
                },
            },
        },
        ReferenceSelectionRequest(camera_shot_type="close_up", angle="front", framing="face"),
    )

    assert result.selected == ()
    assert any(
        item.name == "master_sheet"
        and item.reason == "master sheets are identity review only"
        for item in result.excluded
    )


def test_cropped_preview_allowed_only_with_debug_flag() -> None:
    asset = _selection_asset(include_production=False, include_legacy=True)

    default = ReferenceSelector().explain(
        asset,
        ReferenceSelectionRequest(camera_shot_type="close_up", angle="front", framing="face"),
    )
    debug = ReferenceSelector().explain(
        asset,
        ReferenceSelectionRequest(
            camera_shot_type="close_up",
            angle="front",
            framing="face",
            allow_preview_references=True,
        ),
    )

    assert default.selected == ()
    assert any(
        item.name == "front" and item.reason == "preview references disabled"
        for item in default.excluded
    )
    assert debug.selected[0].name == "front"
    assert debug.selected[0].source_type == "cropped_preview"
    assert debug.selected[0].production_selectable is False


def test_approved_hd_front_selected_for_close_up() -> None:
    result = ReferenceSelector().explain(
        _selection_asset(),
        ReferenceSelectionRequest(
            camera_shot_type="close_up",
            angle="front",
            framing="face",
            engine_reference_limit=4,
        ),
    )

    assert result.selected[0].name == "front"
    assert result.selected[0].score == 100
    assert result.selected[0].source_type == "native_high_resolution"
    assert result.selected[0].production_selectable is True


def test_engine_reference_limit_is_respected_for_production_references() -> None:
    result = ReferenceSelector().explain(
        _selection_asset(),
        ReferenceSelectionRequest(camera_shot_type="close_up", engine_reference_limit=2),
    )

    assert len(result.selected) == 2


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


def _selection_asset(
    *,
    include_production: bool = True,
    include_legacy: bool = False,
) -> dict[str, Any]:
    def reference(
        *,
        path: str,
        tags: list[str],
        shot_types: list[str],
        camera_angles: list[str],
        priority: int,
        source_type: str,
        production_selectable: bool,
    ) -> dict[str, Any]:
        return {
            "path": path,
            "tags": tags,
            "shot_types": shot_types,
            "camera_angles": camera_angles,
            "priority": priority,
            "approved": True,
            "status": "approved",
            "source_type": source_type,
            "production_selectable": production_selectable,
        }

    production = {
        "front": reference(
            path="references/production/front.png",
            tags=["front", "portrait", "close_up", "identity"],
            shot_types=["close_up", "portrait"],
            camera_angles=["front"],
            priority=10,
            source_type="native_high_resolution",
            production_selectable=True,
        ),
        "left_profile": reference(
            path="references/production/left_profile.png",
            tags=["left", "profile", "profile_left", "close_up"],
            shot_types=["close_up", "portrait", "profile"],
            camera_angles=["left", "profile_left"],
            priority=15,
            source_type="native_high_resolution",
            production_selectable=True,
        ),
        "three_quarter_left": reference(
            path="references/production/three_quarter_left.png",
            tags=["three_quarter", "three_quarter_left", "left", "close_up"],
            shot_types=["close_up", "portrait", "three_quarter"],
            camera_angles=["three_quarter_left", "left"],
            priority=20,
            source_type="native_high_resolution",
            production_selectable=True,
        ),
        "three_quarter_right": reference(
            path="references/production/three_quarter_right.png",
            tags=["three_quarter", "three_quarter_right", "right", "close_up"],
            shot_types=["close_up", "portrait", "three_quarter"],
            camera_angles=["three_quarter_right", "right"],
            priority=25,
            source_type="native_high_resolution",
            production_selectable=True,
        ),
        "full_body_front": reference(
            path="references/production/full_body_front.png",
            tags=["full_body", "standing", "front", "wardrobe"],
            shot_types=["full_body", "wide"],
            camera_angles=["front"],
            priority=30,
            source_type="native_high_resolution",
            production_selectable=True,
        ),
    }
    legacy_crops = {
        "front": reference(
            path="references/views/front.png",
            tags=["front", "portrait", "close_up", "identity"],
            shot_types=["close_up", "portrait"],
            camera_angles=["front"],
            priority=10,
            source_type="cropped_preview",
            production_selectable=False,
        ),
    }
    reference_images: dict[str, Any] = {
        "master_sheet": {
            "path": "references/master/master_sheet.png",
            "source_type": "master_sheet",
            "production_selectable": False,
            "approved": True,
            "status": "approved",
        },
    }
    if include_production:
        reference_images["production"] = production
    if include_legacy:
        reference_images["legacy_crops"] = legacy_crops

    return {
        "id": "guriya",
        "reference_images": reference_images,
    }
