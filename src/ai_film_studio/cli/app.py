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
