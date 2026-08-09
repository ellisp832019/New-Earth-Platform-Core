from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .graph import load_projects
from .paths import repo_root
from .service import graph_text, validate_repository
from .validation import validate_yaml_against_schema

app = typer.Typer(no_args_is_help=True, help="New Earth Platform Core CLI")
console = Console()


@app.command()
def validate(root: Optional[Path] = typer.Option(None, help="Repository root")) -> None:
    """Validate Platform Core registries and contracts."""
    target = root or repo_root()
    errors = validate_repository(target)
    if errors:
        console.print("[bold red]Validation failed[/bold red]")
        for error in errors:
            console.print(f" - {error}")
        raise typer.Exit(1)
    console.print("[bold green]Platform validation passed[/bold green]")


@app.command("validate-contract")
def validate_contract(path: Path) -> None:
    """Validate a NEW_EARTH_PROJECT.yaml file."""
    schema = repo_root() / "schemas/project-contract.schema.json"
    errors = validate_yaml_against_schema(path, schema)
    if errors:
        for error in errors:
            console.print(f"[red]{error}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Contract valid:[/green] {path}")


@app.command()
def projects() -> None:
    """Show registered projects."""
    rows = load_projects(repo_root() / "registry/projects.yaml")
    table = Table(title="New Earth Platform Projects")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Family")
    table.add_column("Type")
    table.add_column("Status")
    for p in rows:
        table.add_row(p.id, p.name, p.family, p.type, p.status)
    console.print(table)


@app.command()
def graph(
    format: str = typer.Option("mermaid", help="Output format"),
    output: Optional[Path] = typer.Option(None, help="Optional output path"),
) -> None:
    """Generate the platform dependency graph."""
    if format.lower() != "mermaid":
        console.print("[red]Only mermaid output is supported in v0.1[/red]")
        raise typer.Exit(2)
    text = graph_text(repo_root())
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]Wrote graph:[/green] {output}")
    else:
        console.print(text)
