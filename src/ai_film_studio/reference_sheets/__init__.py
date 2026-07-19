"""Reference sheet splitting and selection services."""

from ai_film_studio.reference_sheets.approval import ReferenceApprovalService
from ai_film_studio.reference_sheets.generation_manifest import with_selected_character_references
from ai_film_studio.reference_sheets.loader import ReferenceSheetLayoutLoader
from ai_film_studio.reference_sheets.models import (
    GeneratedReference,
    NormalizedCrop,
    PixelCrop,
    PlannedCrop,
    ReferenceOutputFormat,
    ReferenceSelectionRequest,
    ReferenceSheetLayout,
    ReferenceSheetPanel,
    ReferenceSheetSplitResult,
    ReferenceStatus,
    SelectedReference,
    SplitOptions,
)
from ai_film_studio.reference_sheets.registry import ReferenceSheetLayoutRegistry
from ai_film_studio.reference_sheets.selector import ReferenceSelector
from ai_film_studio.reference_sheets.splitter import ReferenceSheetSplitter
from ai_film_studio.reference_sheets.validator import ReferenceSheetValidator

__all__ = [
    "GeneratedReference",
    "NormalizedCrop",
    "PixelCrop",
    "PlannedCrop",
    "ReferenceApprovalService",
    "ReferenceOutputFormat",
    "ReferenceSelectionRequest",
    "ReferenceSelector",
    "ReferenceSheetLayout",
    "ReferenceSheetLayoutLoader",
    "ReferenceSheetLayoutRegistry",
    "ReferenceSheetPanel",
    "ReferenceSheetSplitResult",
    "ReferenceSheetSplitter",
    "ReferenceSheetValidator",
    "ReferenceStatus",
    "SelectedReference",
    "SplitOptions",
    "with_selected_character_references",
]
