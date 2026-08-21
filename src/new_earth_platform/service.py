from __future__ import annotations

from pathlib import Path

from .graph import graph_diagnostics, load_dependencies, load_projects, mermaid
from .mcp_export_graph import validate_mcp_export_graph
from .validation import (
    validate_contracts,
    validate_governance,
    validate_mcp_contracts,
    validate_mcp_identity_contracts,
    validate_registry,
    validate_yaml_against_schema,
)


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    errors += validate_yaml_against_schema(
        root / "registry/projects.yaml",
        root / "schemas/registry.schema.json",
    )
    errors += validate_yaml_against_schema(
        root / "registry/dependencies.yaml",
        root / "schemas/dependencies.schema.json",
    )
    errors += validate_yaml_against_schema(
        root / "NEW_EARTH_PROJECT.yaml",
        root / "schemas/project-contract.schema.json",
    )
    errors += validate_governance(root)
    errors += validate_registry(root)
    errors += validate_mcp_identity_contracts(root)
    errors += validate_mcp_contracts(root)
    errors += validate_mcp_export_graph(root)
    errors += validate_contracts(root)
    return errors


def graph_text(root: Path) -> str:
    projects = load_projects(root / "registry/projects.yaml")
    dependencies = load_dependencies(root / "registry/dependencies.yaml")
    return mermaid(projects, dependencies)


def graph_report(root: Path) -> list[str]:
    projects = load_projects(root / "registry/projects.yaml")
    dependencies = load_dependencies(root / "registry/dependencies.yaml")
    return graph_diagnostics(projects, dependencies)
