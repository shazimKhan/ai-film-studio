"""Asset bible filesystem standards."""

from __future__ import annotations

from typing import Final

CHARACTER_REQUIRED_FILES: Final[tuple[str, ...]] = (
    "character.yaml",
    "prompt.md",
    "notes.md",
)
CHARACTER_REQUIRED_DIRS: Final[tuple[str, ...]] = (
    "references",
    "poses",
    "expressions",
    "wardrobe",
    "voice",
)
CHARACTER_IMAGE_SLOTS: Final[dict[str, tuple[str, ...]]] = {
    "references": (
        "front.png",
        "back.png",
        "left.png",
        "right.png",
        "three_quarter.png",
        "full_body.png",
        "closeup.png",
    ),
    "expressions": (
        "neutral.png",
        "happy.png",
        "sad.png",
        "crying.png",
        "angry.png",
        "thinking.png",
        "worried.png",
        "dua.png",
        "smile.png",
    ),
    "poses": (
        "standing.png",
        "walking.png",
        "sitting.png",
        "running.png",
        "working.png",
        "holding_child.png",
        "sewing.png",
        "cooking.png",
    ),
    "wardrobe": (
        "default.png",
        "dress_01.png",
        "dress_02.png",
        "winter.png",
        "wedding.png",
        "sleep.png",
    ),
}

ENVIRONMENT_REQUIRED_FILES: Final[tuple[str, ...]] = (
    "environment.yaml",
    "prompt.md",
)
ENVIRONMENT_REQUIRED_DIRS: Final[tuple[str, ...]] = (
    "references",
    "lighting",
    "angles",
)
ENVIRONMENT_IMAGE_SLOTS: Final[dict[str, tuple[str, ...]]] = {
    "references": (
        "front_day.png",
        "front_evening.png",
        "front_night.png",
        "back_day.png",
        "back_evening.png",
        "back_night.png",
    ),
    "angles": (
        "front.png",
        "back.png",
        "left.png",
        "right.png",
        "top.png",
        "drone.png",
        "inside_to_outside.png",
        "outside_to_inside.png",
    ),
    "lighting": (
        "morning.png",
        "afternoon.png",
        "golden_hour.png",
        "evening.png",
        "night.png",
        "rain.png",
    ),
}

PROP_REQUIRED_FILES: Final[tuple[str, ...]] = (
    "prop.yaml",
    "prompt.md",
)
PROP_REQUIRED_DIRS: Final[tuple[str, ...]] = ("references",)
IMAGE_SUFFIXES: Final[tuple[str, ...]] = (".png", ".jpg", ".jpeg", ".webp")
