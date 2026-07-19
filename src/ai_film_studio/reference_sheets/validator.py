"""Validation helpers for reference sheet splitting."""

from __future__ import annotations

from pathlib import Path

from ai_film_studio.core.exceptions import ReferenceSheetError
from ai_film_studio.reference_sheets.models import (
    NormalizedCrop,
    PixelCrop,
    PlannedCrop,
    ReferenceSheetLayout,
    SplitOptions,
)

SUPPORTED_SOURCE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class ReferenceSheetValidator:
    """Validates source files, layouts, and planned crop geometry."""

    def validate_source_path(self, image_path: Path) -> None:
        """Validate that a source image path exists and has a supported extension."""
        if not image_path.exists():
            msg = f"Reference sheet source image '{image_path}' does not exist."
            raise ReferenceSheetError(msg)
        if not image_path.is_file():
            msg = f"Reference sheet source image '{image_path}' is not a file."
            raise ReferenceSheetError(msg)
        if image_path.suffix.lower() not in SUPPORTED_SOURCE_SUFFIXES:
            supported = ", ".join(sorted(SUPPORTED_SOURCE_SUFFIXES))
            msg = f"Unsupported reference sheet image type '{image_path.suffix}'. Use {supported}."
            raise ReferenceSheetError(msg)

    def build_crop_plan(
        self,
        *,
        layout: ReferenceSheetLayout,
        overrides: dict[str, NormalizedCrop],
        image_width: int,
        image_height: int,
        output_paths: dict[str, Path],
        options: SplitOptions,
    ) -> tuple[PlannedCrop, ...]:
        """Resolve and validate all required panel crops."""
        if image_width <= 0 or image_height <= 0:
            msg = "Reference sheet source image has invalid dimensions."
            raise ReferenceSheetError(msg)

        planned: list[PlannedCrop] = []
        for panel in layout.panels:
            crop = layout.crop_for_panel(panel, overrides)
            padded_crop = self._apply_padding(crop, options.padding + panel.padding, panel.name)
            pixel_crop = self.to_pixel_crop(padded_crop, image_width, image_height, panel.name)
            if pixel_crop.width < options.min_width or pixel_crop.height < options.min_height:
                msg = (
                    f"Panel '{panel.name}' crop is {pixel_crop.width}x{pixel_crop.height}, "
                    f"below minimum {options.min_width}x{options.min_height}."
                )
                raise ReferenceSheetError(msg)
            planned.append(
                PlannedCrop(
                    panel=panel,
                    normalized_crop=padded_crop,
                    pixel_crop=pixel_crop,
                    output_path=output_paths[panel.name].as_posix(),
                    width=pixel_crop.width,
                    height=pixel_crop.height,
                ),
            )
        return tuple(planned)

    def to_pixel_crop(
        self,
        crop: NormalizedCrop,
        image_width: int,
        image_height: int,
        panel_name: str,
    ) -> PixelCrop:
        """Convert a normalized crop to source pixel coordinates."""
        left = round(crop.x * image_width)
        top = round(crop.y * image_height)
        right = round((crop.x + crop.width) * image_width)
        bottom = round((crop.y + crop.height) * image_height)
        if left < 0 or top < 0 or right > image_width or bottom > image_height:
            msg = f"Panel '{panel_name}' crop is outside the source image."
            raise ReferenceSheetError(msg)
        if right <= left or bottom <= top:
            msg = f"Panel '{panel_name}' crop is empty."
            raise ReferenceSheetError(msg)
        return PixelCrop(left=left, top=top, right=right, bottom=bottom)

    def _apply_padding(
        self,
        crop: NormalizedCrop,
        padding: float,
        panel_name: str,
    ) -> NormalizedCrop:
        if padding == 0:
            return crop
        try:
            return crop.with_padding(padding)
        except ValueError as exc:
            msg = f"Panel '{panel_name}' padding moves the crop outside the source bounds."
            raise ReferenceSheetError(msg) from exc
