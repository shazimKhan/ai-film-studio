"""Typer command-line interface for AI Film Studio."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ai_film_studio import __version__
from ai_film_studio.builder import create_default_builder
from ai_film_studio.core.logging import configure_logging

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

