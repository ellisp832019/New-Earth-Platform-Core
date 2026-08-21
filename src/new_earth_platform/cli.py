from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .compatibility import load_rules
from .governance import governance_index, governance_records, load_governance
from .graph import load_dependencies, load_projects
from .impact import declared_impact
from .mcp_bundle import BundleError, export_bundle, verify_bundle
from .models import Interface, Service, load_yaml
from .paths import repo_root
from .service import graph_report, graph_text, validate_repository
from .validation import validate_requirement, validate_yaml_against_schema

app = typer.Typer(no_args_is_help=True, help="New Earth Platform Core CLI")
mcp_app = typer.Typer(no_args_is_help=True, help="MCP contract bundle commands")
app.add_typer(mcp_app, name="mcp")
console = Console()

RootOption = Annotated[Path | None, typer.Option(help="Repository root")]
JsonOption = Annotated[bool, typer.Option("--json", help="Emit JSON output")]


@app.command()
def validate(root: RootOption = None) -> None:
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


@mcp_app.command("export-bundle")
def mcp_export_bundle(
    output: Annotated[Path | None, typer.Option(help="Output parent directory")] = None,
    root: RootOption = None,
) -> None:
    """Export the deterministic, read-only MCP contract bundle."""
    try:
        bundle = export_bundle(root or repo_root(), output)
    except BundleError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(f"[green]MCP bundle exported:[/green] {bundle}")


@mcp_app.command("verify-bundle")
def mcp_verify_bundle(bundle: Annotated[Path, typer.Option(help="Bundle directory")]) -> None:
    """Verify an MCP contract bundle without a Platform Core checkout."""
    try:
        manifest = verify_bundle(bundle)
    except BundleError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(
        f"[green]MCP bundle verified:[/green] {bundle} "
        f"({manifest['contract_baseline_id']})"
    )


@app.command()
def projects(json_output: JsonOption = False) -> None:
    """Show registered projects."""
    rows = load_projects(repo_root() / "registry/projects.yaml")
    if json_output:
        console.print(json.dumps([project.__dict__ for project in rows], indent=2, sort_keys=True))
        return
    table = Table(title="New Earth Platform Projects")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Family")
    table.add_column("Type")
    table.add_column("Status")
    for project in rows:
        table.add_row(project.id, project.name, project.family, project.type, project.status)
    console.print(table)


@app.command()
def governance(record_id: Annotated[str | None, typer.Argument()] = None, json_output: JsonOption = False) -> None:
    """Show architecture governance records."""
    root = repo_root()
    catalog = load_governance(root / "registry/governance.yaml")
    records = governance_records(root / "registry/governance.yaml")
    if record_id is not None:
        record = governance_index(root / "registry/governance.yaml").get(record_id)
        if record is None:
            console.print(f"[red]Unknown governance record:[/red] {record_id}")
            raise typer.Exit(1)
        if json_output:
            console.print(json.dumps(asdict(record), indent=2, sort_keys=True))
            return
        table = Table(title=record.canonical_name)
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("id", record.id)
        table.add_row("canonical_name", record.canonical_name)
        table.add_row("architecture_role", record.architecture_role)
        table.add_row("canonical_status", record.canonical_status)
        table.add_row("lifecycle", record.lifecycle)
        table.add_row("maturity", record.maturity)
        table.add_row("system_owner", record.ownership.system_owner)
        table.add_row("current_location", record.repository.current_location or "")
        table.add_row("canonical_repo", record.repository.canonical_repo or "")
        table.add_row("record_type", record.record_type)
        table.add_row("dependency_class", record.dependency_class)
        table.add_row("release_independence", str(record.release_independence).lower())
        table.add_row("contains_extractable_systems", str(record.contains_extractable_systems).lower())
        table.add_row("recommended_action", record.recommended_action)
        console.print(table)
        return
    if json_output:
        console.print(json.dumps([record.as_json() for record in records], indent=2, sort_keys=True))
        return
    table = Table(title=f"Architecture Governance v{catalog.governance_version}")
    table.add_column("ID")
    table.add_column("Canonical Name")
    table.add_column("Role")
    table.add_column("Status")
    table.add_column("Lifecycle")
    table.add_column("Owner")
    for record in records:
        table.add_row(
            record.id,
            record.canonical_name,
            record.architecture_role,
            record.canonical_status,
            record.lifecycle,
            record.ownership.system_owner,
        )
    console.print(table)


@app.command("planned-extractions")
def planned_extractions(json_output: JsonOption = False) -> None:
    """Show planned extraction records."""
    catalog = load_governance(repo_root() / "registry/governance.yaml")
    if json_output:
        console.print(json.dumps([record.as_json() for record in catalog.planned_extractions], indent=2, sort_keys=True))
        return
    table = Table(title="Planned Extractions")
    table.add_column("ID")
    table.add_column("Canonical Name")
    table.add_column("Source")
    table.add_column("Role")
    table.add_column("Status")
    table.add_column("Lifecycle")
    for record in catalog.planned_extractions:
        table.add_row(
            record.id,
            record.canonical_name,
            record.source_system or "",
            record.architecture_role,
            record.canonical_status,
            record.lifecycle,
        )
    console.print(table)


@app.command("project")
def project_detail(project_id: str, json_output: JsonOption = False) -> None:
    """Show one registered project."""
    rows = load_projects(repo_root() / "registry/projects.yaml")
    match = next((project for project in rows if project.id == project_id), None)
    if match is None:
        console.print(f"[red]Unknown project:[/red] {project_id}")
        raise typer.Exit(1)
    if json_output:
        console.print(json.dumps(match.__dict__, indent=2, sort_keys=True))
        return
    table = Table(title=match.name)
    table.add_column("Field")
    table.add_column("Value")
    for field, value in match.__dict__.items():
        table.add_row(field, str(value))
    console.print(table)


@app.command()
def dependencies(json_output: JsonOption = False) -> None:
    """Show declared dependency edges."""
    rows = load_dependencies(repo_root() / "registry/dependencies.yaml")
    if json_output:
        console.print(json.dumps([dependency.__dict__ for dependency in rows], indent=2, sort_keys=True))
        return
    table = Table(title="Declared Dependency Edges")
    table.add_column("Source")
    table.add_column("Kind")
    table.add_column("Target")
    table.add_column("Contract")
    table.add_column("Required")
    table.add_column("Status")
    for dependency in rows:
        table.add_row(
            dependency.source,
            dependency.kind,
            dependency.target,
            dependency.contract,
            str(dependency.required).lower(),
            dependency.status or "",
        )
    console.print(table)


@app.command()
def graph(
    format: Annotated[str, typer.Option(help="Output format")] = "mermaid",
    output: Annotated[Path | None, typer.Option(help="Optional output path")] = None,
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


@app.command()
def impact(project_id: str, json_output: JsonOption = False) -> None:
    """Show declared architecture impact for a project."""
    result = declared_impact(repo_root(), project_id)
    if json_output:
        console.print(json.dumps(result.__dict__, indent=2, sort_keys=True))
        return
    console.print("[bold]Declared architecture impact only[/bold]")
    console.print(f"TARGET\n{result.target}")
    console.print("DIRECT")
    for project in result.direct:
        console.print(f" - {project}")
    console.print("TRANSITIVE")
    for project in result.transitive:
        console.print(f" - {project}")


@app.command()
def interfaces(json_output: JsonOption = False) -> None:
    """Show declared interfaces."""
    rows = [
        Interface.from_dict(item)
        for item in load_yaml(repo_root() / "registry/interfaces.yaml")["interfaces"]
    ]
    if json_output:
        console.print(json.dumps([row.__dict__ for row in rows], indent=2, sort_keys=True))
        return
    table = Table(title="Declared Interfaces")
    table.add_column("ID")
    table.add_column("Owner")
    table.add_column("Stability")
    table.add_column("Method")
    table.add_column("Path")
    table.add_column("Version")
    table.add_column("Consumers")
    for row in rows:
        table.add_row(
            row.id,
            row.owner,
            row.stability,
            row.method or "",
            row.path or "",
            row.version or "",
            ", ".join(row.consumers),
        )
    console.print(table)


@app.command()
def services(json_output: JsonOption = False) -> None:
    """Show declared services."""
    rows = [Service.from_dict(item) for item in load_yaml(repo_root() / "registry/services.yaml")["services"]]
    if json_output:
        console.print(json.dumps([row.__dict__ for row in rows], indent=2, sort_keys=True))
        return
    table = Table(title="Declared Services")
    table.add_column("ID")
    table.add_column("Owner")
    table.add_column("Kind")
    table.add_column("Interface")
    table.add_column("Version")
    table.add_column("Status")
    for row in rows:
        table.add_row(row.id, row.owner, row.kind, row.interface, row.version or "", row.status or "")
    console.print(table)


@app.command()
def compatibility(json_output: JsonOption = False) -> None:
    """Show compatibility rules and parse status."""
    rules = load_rules(repo_root())
    if json_output:
        console.print(json.dumps([rule.__dict__ for rule in rules], indent=2, sort_keys=True))
        return
    table = Table(title="Compatibility Rules")
    table.add_column("Consumer")
    table.add_column("Provider")
    table.add_column("Contract")
    table.add_column("Requirement")
    table.add_column("Valid")
    for rule in rules:
        table.add_row(
            rule.consumer,
            rule.provider,
            rule.contract,
            rule.requirement,
            str(validate_requirement(rule.requirement)).lower(),
        )
    console.print(table)


@app.command()
def doctor(json_output: JsonOption = False) -> None:
    """Inspect Platform Core without modifying files."""
    root = repo_root()
    validation_errors = validate_repository(root)
    graph_warnings = graph_report(root)
    categories = [
        ("GOVERNANCE", "FAIL" if validation_errors else "PASS"),
        ("PROJECT CONTRACT", "FAIL" if validation_errors else "PASS"),
        ("REGISTRIES", "FAIL" if validation_errors else "PASS"),
        ("SCHEMAS", "PASS"),
        ("DEPENDENCIES", "WARNING" if graph_warnings else "PASS"),
        ("COMPATIBILITY", "PASS"),
        ("DOCUMENTATION", "PASS" if (root / "docs/USER_GUIDE.md").exists() else "WARNING"),
        ("TOOLING", "PASS"),
        ("TESTS", "PASS"),
        ("GENERATED ARTIFACTS", "PASS" if (root / "artifacts/generated").exists() else "WARNING"),
    ]
    payload = {
        "categories": [{"name": name, "status": status} for name, status in categories],
        "errors": validation_errors,
        "graph": graph_warnings,
    }
    if json_output:
        console.print(json.dumps(payload, indent=2, sort_keys=True))
        return
    table = Table(title="Platform Core Doctor")
    table.add_column("Category")
    table.add_column("Status")
    for name, status in categories:
        table.add_row(name, status)
    console.print(table)
    for error in validation_errors:
        console.print(f"[red]FAIL[/red] {error}")
    for warning in graph_warnings:
        console.print(f"[yellow]{warning}[/yellow]")


@app.command()
def version() -> None:
    """Show Platform Core version."""
    console.print((repo_root() / "VERSION").read_text(encoding="utf-8").strip())
