from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from ai_film_studio.reference_sheets import ReferenceInventoryService, ReferenceSourceType


def test_low_resolution_production_reference_is_rejected(tmp_path: Path) -> None:
    repo_root = _write_character_project(tmp_path)
    _write_image(
        repo_root / "projects/demo/characters/hero/references/production/front.png",
        size=(512, 512),
    )
    _write_character_yaml(repo_root, production={"front": _production_reference("front")})

    validations = ReferenceInventoryService(repo_root=repo_root).validate_production_references(
        project="demo",
        character="hero",
    )
    front = next(validation for validation in validations if validation.name == "front")

    assert front.exists is True
    assert front.readable is True
    assert front.width == 512
    assert front.height == 512
    assert front.is_valid is False
    assert front.reason == "image width below minimum 1024"


def test_valid_approved_production_references_make_character_ready(tmp_path: Path) -> None:
    repo_root = _write_character_project(tmp_path)
    production = {}
    for reference_name in (
        "front",
        "left_profile",
        "three_quarter_left",
        "three_quarter_right",
        "full_body_front",
        "full_body_back",
        "seated_front",
    ):
        _write_image(
            repo_root
            / "projects/demo/characters/hero/references/production"
            / f"{reference_name}.png",
            size=_size_for(reference_name),
        )
        production[reference_name] = _production_reference(reference_name)
    _write_character_yaml(repo_root, production=production)

    inventory = ReferenceInventoryService(repo_root=repo_root)
    validations = inventory.validate_production_references(project="demo", character="hero")
    readiness = inventory.production_readiness(project="demo", character="hero")

    assert all(validation.is_valid for validation in validations)
    assert readiness.production_ready is True
    assert set(readiness.ready_references) == {
        "front",
        "left_profile",
        "three_quarter_left",
        "three_quarter_right",
        "full_body_front",
        "full_body_back",
        "seated_front",
    }
    assert readiness.missing_references == ()
    assert readiness.invalid_references == ()


def test_production_reference_with_cropped_preview_source_type_is_rejected(
    tmp_path: Path,
) -> None:
    repo_root = _write_character_project(tmp_path)
    _write_image(
        repo_root / "projects/demo/characters/hero/references/production/front.png",
        size=(1024, 1024),
    )
    bad_reference = _production_reference("front")
    bad_reference["source_type"] = ReferenceSourceType.CROPPED_PREVIEW.value
    _write_character_yaml(repo_root, production={"front": bad_reference})

    validations = ReferenceInventoryService(repo_root=repo_root).validate_production_references(
        project="demo",
        character="hero",
    )
    front = next(validation for validation in validations if validation.name == "front")

    assert front.is_valid is False
    assert front.reason == "source type is not production selectable"


def test_migration_preserves_cropped_paths_files_and_unknown_yaml_fields(
    tmp_path: Path,
) -> None:
    repo_root = _write_character_project(tmp_path)
    crop_path = repo_root / "projects/demo/characters/hero/references/views/front.png"
    _write_image(crop_path, size=(256, 256))
    character_yaml = repo_root / "projects/demo/characters/hero/character.yaml"
    character_yaml.write_text(
        yaml.safe_dump(
            {
                "id": "hero",
                "custom_root_field": "keep_me",
                "reference_images": {
                    "master_sheet": {
                        "path": "references/master/master_sheet.png",
                        "custom_master_field": "keep_master",
                    },
                    "views": {
                        "front": {
                            "path": "references/views/front.png",
                            "status": "approved",
                            "approved": True,
                            "custom_reference_field": "keep_reference",
                        },
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    ReferenceInventoryService(repo_root=repo_root).migrate_cropped_references(
        project="demo",
        character="hero",
    )

    migrated = yaml.safe_load(character_yaml.read_text(encoding="utf-8"))
    legacy_front = migrated["reference_images"]["legacy_crops"]["front"]
    assert crop_path.is_file()
    assert character_yaml.with_suffix(".yaml.bak").is_file()
    assert migrated["custom_root_field"] == "keep_me"
    assert migrated["reference_images"]["master_sheet"]["custom_master_field"] == "keep_master"
    assert "views" not in migrated["reference_images"]
    assert legacy_front["path"] == "references/views/front.png"
    assert legacy_front["source_type"] == "cropped_preview"
    assert legacy_front["production_selectable"] is False
    assert legacy_front["custom_reference_field"] == "keep_reference"
    assert migrated["production_ready"] is False


def _write_character_project(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    character_dir = repo_root / "projects/demo/characters/hero"
    for directory in (
        "references/master",
        "references/views",
        "references/production",
    ):
        (character_dir / directory).mkdir(parents=True, exist_ok=True)
    return repo_root


def _write_character_yaml(
    repo_root: Path,
    *,
    production: dict[str, dict[str, Any]],
) -> None:
    character_yaml = repo_root / "projects/demo/characters/hero/character.yaml"
    character_yaml.write_text(
        yaml.safe_dump(
            {
                "id": "hero",
                "reference_images": {
                    "master_sheet": {
                        "path": "references/master/master_sheet.png",
                        "source_type": "master_sheet",
                        "production_selectable": False,
                        "status": "approved",
                        "approved": True,
                    },
                    "production": production,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _production_reference(reference_name: str) -> dict[str, Any]:
    return {
        "path": f"references/production/{reference_name}.png",
        "source_type": ReferenceSourceType.NATIVE_HIGH_RESOLUTION.value,
        "production_selectable": True,
        "status": "approved",
        "approved": True,
        "tags": _tags_for(reference_name),
        "shot_types": ["full_body", "wide"]
        if reference_name.startswith("full_body") or reference_name == "seated_front"
        else ["close_up", "portrait"],
        "camera_angles": ["front"],
        "priority": 10,
    }


def _tags_for(reference_name: str) -> list[str]:
    tags = reference_name.split("_")
    if reference_name.startswith("full_body") or reference_name == "seated_front":
        return [reference_name, *tags, "full_body", "standing"]
    return [reference_name, *tags, "portrait", "close_up", "identity"]


def _size_for(reference_name: str) -> tuple[int, int]:
    if reference_name.startswith("full_body") or reference_name == "seated_front":
        return 1024, 1536
    return 1024, 1024


def _write_image(path: Path, *, size: tuple[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, "white").save(path, format="PNG")
