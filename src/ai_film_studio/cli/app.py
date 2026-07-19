"""Typer command-line interface for AI Film Studio."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ai_film_studio import __version__
from ai_film_studio.asset_bible import AssetBibleService
from ai_film_studio.builder import create_default_builder
from ai_film_studio.core.exceptions import AIFilmStudioError
from ai_film_studio.core.logging import configure_logging
from ai_film_studio.prompt_compiler import PromptCompilationService
from ai_film_studio.reference_sheets import (
    ReferenceApprovalService,
    ReferenceOutputFormat,
    ReferenceSheetSplitter,
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
