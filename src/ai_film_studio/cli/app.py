"""Typer command-line interface for AI Film Studio."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

from ai_film_studio import __version__
from ai_film_studio.asset_bible import AssetBibleService, IdentityLockService
from ai_film_studio.builder import create_default_builder
from ai_film_studio.core.exceptions import AIFilmStudioError
from ai_film_studio.core.logging import configure_logging
from ai_film_studio.project_config import ProjectConfigValidator, ProjectValidationReport
from ai_film_studio.prompt_compiler import PromptCompilationService
from ai_film_studio.reference_sheets import (
    ProductionReadiness,
    ReferenceApprovalService,
    ReferenceImageValidation,
    ReferenceInventoryService,
    ReferenceOutputFormat,
    ReferenceSelectionService,
    ReferenceSheetSplitter,
    ReferenceSourceType,
    SplitOptions,
)

console = Console()

app = typer.Typer(
    help="AI Film Studio framework tools.",
    no_args_is_help=True,
)
adapters_app = typer.Typer(help="Inspect engine adapter registrations.")
modules_app = typer.Typer(help="Inspect loadable framework modules.")

app.add_typer(adapters_app, name="adapters")
app.add_typer(modules_app, name="modules")


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging."),
    ] = False,
) -> None:
    """Configure shared CLI behavior."""
    configure_logging("DEBUG" if verbose else "INFO")


@app.command()
def version() -> None:
    """Print the installed framework version."""
    console.print(__version__)


@app.command()
def doctor() -> None:
    """Check that the framework foundation can build a runtime."""
    runtime = create_default_builder().build()
    console.print("[green]Runtime foundation built successfully.[/green]")
    console.print(f"Registered engine adapters: {len(runtime.engine_adapters)}")


@app.command("validate-project")
def validate_project(
    project_root: Annotated[
        Path,
        typer.Argument(help="Project root containing project.yaml."),
    ],
) -> None:
    """Validate reusable project configuration and research gates."""
    try:
        report = ProjectConfigValidator(repo_root=Path.cwd()).validate_project(project_root)
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    _print_project_validation_report(report)
    if not report.is_valid:
        raise typer.Exit(1)


@app.command("validate-identity")
def validate_identity(
    project: Annotated[
        str,
        typer.Option("--project", help="Project id under projects/."),
    ],
    character: Annotated[
        str,
        typer.Option("--character", help="Character id under 05_characters/."),
    ],
) -> None:
    """Validate one project-local character identity lock."""
    try:
        identity = IdentityLockService(repo_root=Path.cwd()).load_identity(
            Path("projects") / project,
            character,
        )
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    reference_path = identity.reference_image.path if identity.reference_image else "-"
    console.print(f"Character: {identity.character_id}")
    console.print(f"Identity: {identity.identity_id}")
    console.print(f"Status: {identity.status}")
    console.print(f"Lock: {identity.lock_level}")
    console.print(f"Reference image: {reference_path}")
    console.print("[green]Validation: passed[/green]")


@app.command("create-project")
def create_project(
    project_id: Annotated[
        str,
        typer.Option("--project-id", help="Lowercase snake_case project id."),
    ],
    project_name: Annotated[
        str,
        typer.Option("--project-name", help="Human-readable project name."),
    ],
    genre: Annotated[
        str,
        typer.Option("--genre", help="Primary genre label."),
    ],
    project_type: Annotated[
        str,
        typer.Option("--project-type", help="Reusable project type."),
    ] = "fictional_drama",
    language: Annotated[
        str,
        typer.Option("--language", help="Primary language."),
    ] = "urdu",
    research_required: Annotated[
        bool,
        typer.Option("--research-required/--no-research-required"),
    ] = False,
    source_validation_required: Annotated[
        bool,
        typer.Option("--source-validation-required/--no-source-validation-required"),
    ] = False,
    depiction_policy: Annotated[
        str,
        typer.Option("--depiction-policy", help="Depiction policy id."),
    ] = "standard",
    visual_style: Annotated[
        str,
        typer.Option("--visual-style", help="Short visual style description."),
    ] = "project_defined",
    target_platform: Annotated[
        str,
        typer.Option("--target-platform", help="Initial target platform."),
    ] = "youtube",
) -> None:
    """Create a small project scaffold from reusable defaults."""
    project_root = Path("projects") / project_id
    project_yaml = project_root / "project.yaml"
    readme = project_root / "README.md"
    if project_yaml.exists() or readme.exists():
        console.print(f"[red]Error:[/red] Project '{project_id}' already has starter files.")
        raise typer.Exit(1)

    config = {
        "schema_version": "1.0",
        "project_id": project_id,
        "project_name": project_name,
        "project_type": project_type,
        "genre": [genre],
        "language": language,
        "secondary_languages": [],
        "historical_period": "",
        "research_required": research_required,
        "source_validation_required": source_validation_required,
        "depiction_policy": depiction_policy,
        "visual_style": {"description": visual_style},
        "aspect_ratio": "16:9",
        "default_shot_duration": 6,
        "target_platforms": [target_platform],
        "prompt_engines": ["gemini"],
        "voiceover_language": language,
        "continuity_level": "standard",
        "qa_profiles": ["technical"],
        "shared_asset_access": {"enabled": True},
        "project_asset_path": project_root.as_posix(),
        "export_presets": [],
    }
    try:
        project_root.mkdir(parents=True, exist_ok=False)
        project_yaml.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        readme.write_text(
            f"# {project_name}\n\nProject scaffold for `{project_id}`.\n",
            encoding="utf-8",
        )
    except OSError as exc:
        console.print(f"[red]Error:[/red] Could not create project '{project_id}': {exc}")
        raise typer.Exit(1) from None

    console.print(f"Project created at: {project_root}")


@app.command("compile")
def compile_scene(
    scene_file: Annotated[
        Path,
        typer.Argument(help="Path to a scene blueprint YAML file."),
    ],
    engine: Annotated[
        str,
        typer.Option("--engine", "-e", help="Target engine adapter id."),
    ],
) -> None:
    """Compile a scene blueprint into a local engine-ready prompt."""
    try:
        runtime = create_default_builder().build()
        service = PromptCompilationService.from_runtime(
            runtime,
            repo_root=Path.cwd(),
            output_root=Path("output"),
        )
        artifact = service.compile(scene_file, engine)
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    console.print(f"Prompt written to: {artifact.output_path}")


@app.command("validate-assets")
def validate_assets(
    project_root: Annotated[
        Path,
        typer.Option(
            "--project-root",
            "-p",
            help="Project asset root to validate.",
        ),
    ] = Path("projects/guriya"),
    index_path: Annotated[
        Path | None,
        typer.Option(
            "--index-path",
            help="Optional asset index output path.",
        ),
    ] = None,
    max_issues: Annotated[
        int,
        typer.Option(
            "--max-issues",
            min=1,
            help="Maximum number of validation issues to print.",
        ),
    ] = 50,
) -> None:
    """Validate production asset bibles and generate an asset index."""
    try:
        report = AssetBibleService().validate(project_root, index_path)
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    console.print(f"Asset index written to: {report.index_path}")
    if report.is_valid:
        console.print("[green]Asset validation passed.[/green]")
        return

    console.print(f"[red]Asset validation found {len(report.issues)} issue(s).[/red]")
    table = Table(title="Asset Validation Issues")
    table.add_column("Code")
    table.add_column("Path")
    table.add_column("Message")
    shown_issues = report.issues[:max_issues]
    for issue in shown_issues:
        table.add_row(issue.code, issue.path, issue.message)
    console.print(table)
    remaining = len(report.issues) - len(shown_issues)
    if remaining > 0:
        console.print(f"... {remaining} more issue(s) not shown. Re-run with --max-issues.")
    raise typer.Exit(1)


@app.command("split-reference-sheet")
def split_reference_sheet(
    image_path: Annotated[
        Path,
        typer.Argument(help="Path to a manually generated character reference sheet image."),
    ],
    project: Annotated[
        str,
        typer.Option("--project", help="Project id under projects/."),
    ],
    character: Annotated[
        str,
        typer.Option(
            "--character",
            help="Character asset id under projects/<project>/characters/.",
        ),
    ],
    layout: Annotated[
        str,
        typer.Option("--layout", help="Reference sheet layout id."),
    ],
    output_format: Annotated[
        ReferenceOutputFormat,
        typer.Option("--output-format", help="Crop output format."),
    ] = ReferenceOutputFormat.PNG,
    padding: Annotated[
        float,
        typer.Option("--padding", min=0.0, max=0.25, help="Normalized crop padding."),
    ] = 0.0,
    min_width: Annotated[
        int,
        typer.Option("--min-width", min=1, help="Minimum generated crop width."),
    ] = 128,
    min_height: Annotated[
        int,
        typer.Option("--min-height", min=1, help="Minimum generated crop height."),
    ] = 128,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing crop files instead of versioning."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Validate and print crop plan without writing files."),
    ] = False,
    overrides: Annotated[
        Path | None,
        typer.Option("--overrides", help="Optional manual crop override YAML."),
    ] = None,
) -> None:
    """Split a deterministic reference sheet into reviewable view images."""
    try:
        result = ReferenceSheetSplitter(repo_root=Path.cwd()).split(
            image_path,
            project=project,
            character=character,
            layout_id=layout,
            options=SplitOptions(
                output_format=output_format,
                padding=padding,
                min_width=min_width,
                min_height=min_height,
                overwrite=overwrite,
                dry_run=dry_run,
            ),
            overrides_path=overrides,
        )
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    if result.dry_run:
        console.print("[yellow]Dry run only. No reference files were written.[/yellow]")
    else:
        console.print(f"Reference manifest written to: {result.manifest_path}")
        console.print(f"Crop preview written to: {result.preview_path}")

    table = Table(title="Reference Sheet Crops")
    table.add_column("Reference")
    table.add_column("Output")
    table.add_column("Size")
    if result.generated_files:
        for reference in result.generated_files:
            table.add_row(
                reference.name,
                reference.path,
                f"{reference.width}x{reference.height}",
            )
    else:
        for crop in result.planned_crops:
            table.add_row(
                crop.panel.name,
                crop.output_path,
                f"{crop.width}x{crop.height}",
            )
    console.print(table)


@app.command("preview-reference-sheet")
def preview_reference_sheet(
    image_path: Annotated[
        Path,
        typer.Argument(help="Path to a manually generated character reference sheet image."),
    ],
    layout: Annotated[
        str,
        typer.Option("--layout", help="Reference sheet layout id."),
    ],
    overrides: Annotated[
        Path | None,
        typer.Option("--overrides", help="Optional manual crop override YAML."),
    ] = None,
    project: Annotated[
        str | None,
        typer.Option(
            "--project",
            help="Project id. Inferred from project asset paths when omitted.",
        ),
    ] = None,
    character: Annotated[
        str | None,
        typer.Option(
            "--character",
            help="Character id. Inferred from project asset paths when omitted.",
        ),
    ] = None,
    padding: Annotated[
        float,
        typer.Option("--padding", min=0.0, max=0.25, help="Normalized crop padding."),
    ] = 0.0,
    min_width: Annotated[
        int,
        typer.Option("--min-width", min=1, help="Minimum planned crop width."),
    ] = 128,
    min_height: Annotated[
        int,
        typer.Option("--min-height", min=1, help="Minimum planned crop height."),
    ] = 128,
) -> None:
    """Generate a crop rectangle preview without writing split crop images."""
    try:
        resolved_project, resolved_character = _resolve_project_character(
            image_path,
            project,
            character,
        )
        result = ReferenceSheetSplitter(repo_root=Path.cwd()).preview(
            image_path,
            project=resolved_project,
            character=resolved_character,
            layout_id=layout,
            options=SplitOptions(
                padding=padding,
                min_width=min_width,
                min_height=min_height,
                dry_run=True,
            ),
            overrides_path=overrides,
        )
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    console.print(f"Crop preview written to: {result.preview_path}")


@app.command("approve-reference")
def approve_reference(
    project: Annotated[
        str,
        typer.Option("--project", help="Project id under projects/."),
    ],
    character: Annotated[
        str,
        typer.Option("--character", help="Character asset id."),
    ],
    reference: Annotated[
        str,
        typer.Option("--reference", help="Reference view name to approve."),
    ],
) -> None:
    """Approve an extracted reference for automatic selection."""
    try:
        path = ReferenceApprovalService(repo_root=Path.cwd()).approve(
            project=project,
            character=character,
            reference=reference,
        )
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    console.print(f"Approved reference '{reference}' in: {path}")


@app.command("reject-reference")
def reject_reference(
    project: Annotated[
        str,
        typer.Option("--project", help="Project id under projects/."),
    ],
    character: Annotated[
        str,
        typer.Option("--character", help="Character asset id."),
    ],
    reference: Annotated[
        str,
        typer.Option("--reference", help="Reference view name to reject."),
    ],
    reason: Annotated[
        str,
        typer.Option("--reason", help="Human review reason for rejection."),
    ],
) -> None:
    """Reject an extracted reference so it is not selected automatically."""
    try:
        path = ReferenceApprovalService(repo_root=Path.cwd()).reject(
            project=project,
            character=character,
            reference=reference,
            reason=reason,
        )
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    console.print(f"Rejected reference '{reference}' in: {path}")


@app.command("list-references")
def list_references(
    project: Annotated[
        str,
        typer.Option("--project", help="Project id under projects/."),
    ],
    character: Annotated[
        str,
        typer.Option("--character", help="Character asset id."),
    ],
) -> None:
    """List mapped character references and validation state."""
    try:
        validations = ReferenceInventoryService(repo_root=Path.cwd()).validate_character(
            project=project,
            character=character,
        )
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    _print_reference_validation_table(validations)


@app.command("validate-references")
def validate_references(
    project: Annotated[
        str,
        typer.Option("--project", help="Project id under projects/."),
    ],
    character: Annotated[
        str,
        typer.Option("--character", help="Character asset id."),
    ],
) -> None:
    """Validate mapped character reference images."""
    try:
        validations = ReferenceInventoryService(repo_root=Path.cwd()).validate_character(
            project=project,
            character=character,
        )
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    _print_reference_validation_table(validations)
    invalid = [validation for validation in validations if not validation.is_valid]
    if invalid:
        console.print(f"[red]{len(invalid)} invalid reference image(s).[/red]")
        raise typer.Exit(1)
    console.print("[green]Reference image validation passed.[/green]")


@app.command("register-production-reference")
def register_production_reference(
    project: Annotated[
        str,
        typer.Option("--project", help="Project id under projects/."),
    ],
    character: Annotated[
        str,
        typer.Option("--character", help="Character asset id."),
    ],
    reference_type: Annotated[
        str,
        typer.Option("--type", help="Production reference type, such as front."),
    ],
    path: Annotated[
        Path,
        typer.Option("--path", help="Path to the independently generated HD image."),
    ],
    source_type: Annotated[
        ReferenceSourceType,
        typer.Option("--source-type", help="Production reference source type."),
    ] = ReferenceSourceType.NATIVE_HIGH_RESOLUTION,
) -> None:
    """Register a separately generated HD production reference."""
    try:
        inventory = ReferenceInventoryService(repo_root=Path.cwd())
        character_yaml = inventory.register_production_reference(
            project=project,
            character=character,
            reference_type=reference_type,
            path=path,
            source_type=source_type,
        )
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    console.print(f"Registered production reference '{reference_type}' in: {character_yaml}")


@app.command("list-production-references")
def list_production_references(
    project: Annotated[
        str,
        typer.Option("--project", help="Project id under projects/."),
    ],
    character: Annotated[
        str,
        typer.Option("--character", help="Character asset id."),
    ],
) -> None:
    """List production references and readiness state."""
    try:
        inventory = ReferenceInventoryService(repo_root=Path.cwd())
        validations = inventory.validate_production_references(
            project=project,
            character=character,
        )
        readiness = inventory.production_readiness(project=project, character=character)
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    _print_reference_validation_table(validations)
    _print_readiness(readiness)


@app.command("validate-production-references")
def validate_production_references(
    project: Annotated[
        str,
        typer.Option("--project", help="Project id under projects/."),
    ],
    character: Annotated[
        str,
        typer.Option("--character", help="Character asset id."),
    ],
) -> None:
    """Validate HD production references and production readiness."""
    try:
        inventory = ReferenceInventoryService(repo_root=Path.cwd())
        validations = inventory.validate_production_references(
            project=project,
            character=character,
        )
        readiness = inventory.production_readiness(project=project, character=character)
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    _print_reference_validation_table(validations)
    _print_readiness(readiness)
    invalid = [validation for validation in validations if not validation.is_valid]
    if invalid or not readiness.production_ready:
        console.print("[red]Production reference validation failed.[/red]")
        raise typer.Exit(1)
    console.print("[green]Production reference validation passed.[/green]")


@app.command("migrate-cropped-references")
def migrate_cropped_references(
    project: Annotated[
        str,
        typer.Option("--project", help="Project id under projects/."),
    ],
    character: Annotated[
        str,
        typer.Option("--character", help="Character asset id."),
    ],
) -> None:
    """Move cropped reference metadata into legacy preview references."""
    try:
        inventory = ReferenceInventoryService(repo_root=Path.cwd())
        character_yaml = inventory.migrate_cropped_references(
            project=project,
            character=character,
        )
        readiness = inventory.production_readiness(project=project, character=character)
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    console.print(f"Migrated cropped references in: {character_yaml}")
    _print_readiness(readiness)


@app.command("select-references")
def select_references(
    scene_file: Annotated[
        Path,
        typer.Argument(help="Path to a reference-selection scene YAML file."),
    ],
    engine: Annotated[
        str,
        typer.Option("--engine", "-e", help="Target engine adapter id."),
    ],
    allow_weak_fallbacks: Annotated[
        bool,
        typer.Option(
            "--allow-weak-fallbacks",
            help="Allow weak selector fallbacks such as portrait refs for full-body shots.",
        ),
    ] = False,
    allow_preview_references: Annotated[
        bool,
        typer.Option(
            "--allow-preview-references",
            help="Allow cropped preview references for debugging only.",
        ),
    ] = False,
) -> None:
    """Debug reference selection for a scene and write a generation manifest."""
    try:
        runtime = create_default_builder().build()
        artifact = ReferenceSelectionService.from_runtime(
            runtime,
            repo_root=Path.cwd(),
            output_root=Path("output"),
        ).compile_scene(
            scene_file,
            engine=engine,
            allow_weak_fallbacks=allow_weak_fallbacks,
            allow_preview_references=allow_preview_references,
        )
    except AIFilmStudioError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    inputs = artifact.result.selector_inputs
    console.print(f"Character: {artifact.result.character_id}")
    console.print(f"Shot: {inputs.camera_shot_type}")
    console.print(f"Angle: {inputs.angle}")
    if inputs.framing:
        console.print(f"Framing: {inputs.framing}")
    if inputs.pose:
        console.print(f"Pose: {inputs.pose}")
    if inputs.action:
        console.print(f"Action: {inputs.action}")
    console.print(f"Allow preview references: {inputs.allow_preview_references}")
    console.print(f"Engine reference limit: {artifact.result.engine_reference_limit}")
    console.print(f"Manifest: {artifact.output_path}")

    console.print("\nSelected:")
    if artifact.result.selected:
        for index, reference in enumerate(artifact.result.selected, start=1):
            console.print(f"{index}. {reference.path}")
            console.print(f"   Score: {_format_score(reference.score)}")
            console.print(f"   Reason: {reference.reason}")
    else:
        console.print("- none")

    console.print("\nExcluded:")
    if artifact.result.excluded:
        for excluded_reference in artifact.result.excluded:
            path = excluded_reference.path or excluded_reference.name
            console.print(f"- {path}")
            console.print(f"  Reason: {excluded_reference.reason}")
    else:
        console.print("- none")


@adapters_app.command("list")
def list_adapters() -> None:
    """List registered engine adapter ids."""
    runtime = create_default_builder().build()
    adapter_ids = runtime.engine_adapters.list_adapter_ids()
    if not adapter_ids:
        console.print("No engine adapters registered.")
        return

    table = Table(title="Engine Adapters")
    table.add_column("Adapter ID")
    for adapter_id in adapter_ids:
        table.add_row(adapter_id)
    console.print(table)


@modules_app.command("load")
def load_module(
    import_path: Annotated[
        str,
        typer.Argument(help="Python import path using 'package.module:object' syntax."),
    ],
) -> None:
    """Validate that a module or object can be loaded."""
    runtime = create_default_builder().build()
    runtime.module_loader.load(import_path)
    console.print(f"[green]Loaded:[/green] {import_path}")


def _resolve_project_character(
    image_path: Path,
    project: str | None,
    character: str | None,
) -> tuple[str, str]:
    if project and character:
        return project, character
    if project or character:
        msg = "Both --project and --character are required when either is provided."
        raise AIFilmStudioError(msg)

    parts = image_path.parts
    try:
        projects_index = parts.index("projects")
        inferred_project = parts[projects_index + 1]
        characters_label = parts[projects_index + 2]
        inferred_character = parts[projects_index + 3]
    except (ValueError, IndexError) as exc:
        msg = "Could not infer project and character from image path. Provide both options."
        raise AIFilmStudioError(msg) from exc
    if characters_label != "characters":
        msg = "Could not infer character from image path. Provide --project and --character."
        raise AIFilmStudioError(msg)
    return inferred_project, inferred_character


def _print_reference_validation_table(validations: Iterable[ReferenceImageValidation]) -> None:
    table = Table(title="Character References")
    table.add_column("Reference")
    table.add_column("Path")
    table.add_column("Source")
    table.add_column("Selectable")
    table.add_column("Status")
    table.add_column("Approved")
    table.add_column("Valid")
    table.add_column("Size")
    table.add_column("Minimum")
    table.add_column("Reason")
    for validation in validations:
        size = (
            f"{validation.width}x{validation.height}"
            if validation.width and validation.height
            else "-"
        )
        minimum = (
            f"{validation.min_width}x{validation.min_height}"
            if validation.min_width and validation.min_height
            else "-"
        )
        table.add_row(
            validation.name,
            validation.path or "-",
            validation.source_type.value if validation.source_type else "-",
            "yes" if validation.production_selectable else "no",
            validation.status.value,
            "yes" if validation.approved else "no",
            "yes" if validation.is_valid else "no",
            size,
            minimum,
            validation.reason,
        )
    console.print(table)


def _print_project_validation_report(report: ProjectValidationReport) -> None:
    state = "passed" if report.is_valid else "failed"
    color = "green" if report.is_valid else "red"
    console.print(f"[{color}]Project validation {state}:[/{color}] {report.project_id}")
    if report.is_valid:
        return

    table = Table(title="Project Validation Issues")
    table.add_column("Code", no_wrap=True)
    table.add_column("Path")
    table.add_column("Message")
    for issue in report.issues:
        table.add_row(issue.code, issue.path, issue.message)
    console.print(table)


def _print_readiness(readiness: ProductionReadiness) -> None:
    state = "yes" if readiness.production_ready else "no"
    console.print(f"Production ready: {state}")
    if readiness.ready_references:
        console.print(f"Ready: {', '.join(readiness.ready_references)}")
    if readiness.missing_references:
        console.print(f"Missing: {', '.join(readiness.missing_references)}")
    if readiness.invalid_references:
        console.print(f"Invalid: {', '.join(readiness.invalid_references)}")


def _format_score(score: float) -> str:
    if score.is_integer():
        return str(int(score))
    return f"{score:.2f}"
