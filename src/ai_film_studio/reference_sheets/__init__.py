"""Reference sheet splitting and selection services."""

from ai_film_studio.reference_sheets.approval import ReferenceApprovalService
from ai_film_studio.reference_sheets.generation_manifest import with_selected_character_references
from ai_film_studio.reference_sheets.inventory import ReferenceInventoryService
from ai_film_studio.reference_sheets.loader import ReferenceSheetLayoutLoader
from ai_film_studio.reference_sheets.models import (
    ExcludedReference,
    GeneratedReference,
    NormalizedCrop,
    PixelCrop,
    PlannedCrop,
    ProductionReadiness,
    ReferenceImageValidation,
    ReferenceOutputFormat,
    ReferenceSelectionRequest,
    ReferenceSelectionResult,
    ReferenceSelectionScene,
    ReferenceSheetLayout,
    ReferenceSheetPanel,
    ReferenceSheetSplitResult,
    ReferenceSourceType,
    ReferenceStatus,
    SceneReferenceSelectionArtifact,
    SelectedReference,
    SplitOptions,
)
from ai_film_studio.reference_sheets.registry import ReferenceSheetLayoutRegistry
from ai_film_studio.reference_sheets.selector import ReferenceSelector
from ai_film_studio.reference_sheets.service import ReferenceSelectionService
from ai_film_studio.reference_sheets.splitter import ReferenceSheetSplitter
from ai_film_studio.reference_sheets.validator import ReferenceSheetValidator

__all__ = [
    "GeneratedReference",
    "NormalizedCrop",
    "ExcludedReference",
    "PixelCrop",
    "PlannedCrop",
    "ProductionReadiness",
    "ReferenceApprovalService",
    "ReferenceImageValidation",
    "ReferenceInventoryService",
    "ReferenceOutputFormat",
    "ReferenceSelectionRequest",
    "ReferenceSelectionResult",
    "ReferenceSelectionScene",
    "ReferenceSelector",
    "ReferenceSelectionService",
    "ReferenceSheetLayout",
    "ReferenceSheetLayoutLoader",
    "ReferenceSheetLayoutRegistry",
    "ReferenceSheetPanel",
    "ReferenceSheetSplitResult",
    "ReferenceSheetSplitter",
    "ReferenceSheetValidator",
    "ReferenceSourceType",
    "ReferenceStatus",
    "SceneReferenceSelectionArtifact",
    "SelectedReference",
    "SplitOptions",
    "with_selected_character_references",
]
