from __future__ import annotations

from pathlib import Path

from .graph import load_dependencies, load_projects, mermaid
from .validation import (
    validate_project_ids,
    validate_unique_project_ids,
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
    errors += validate_unique_project_ids(root / "registry/projects.yaml")
    errors += validate_project_ids(
        root / "registry/projects.yaml",
        root / "registry/dependencies.yaml",
    )
    return errors


def graph_text(root: Path) -> str:
    projects = load_projects(root / "registry/projects.yaml")
    dependencies = load_dependencies(root / "registry/dependencies.yaml")
    return mermaid(projects, dependencies)
