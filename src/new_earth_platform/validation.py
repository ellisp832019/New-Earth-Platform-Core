from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .models import load_yaml


class ValidationFailure(Exception):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_yaml_against_schema(yaml_path: Path, schema_path: Path) -> list[str]:
    instance = load_yaml(yaml_path)
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    rendered: list[str] = []
    for error in errors:
        location = ".".join(str(p) for p in error.absolute_path) or "<root>"
        rendered.append(f"{yaml_path}: {location}: {error.message}")
    return rendered


def validate_project_ids(projects_path: Path, dependencies_path: Path) -> list[str]:
    projects = load_yaml(projects_path).get("projects", [])
    dependencies = load_yaml(dependencies_path).get("dependencies", [])
    ids = {str(p["id"]) for p in projects}
    errors: list[str] = []
    for edge in dependencies:
        source = str(edge["source"])
        target = str(edge["target"])
        if source not in ids:
            errors.append(f"Unknown dependency source: {source}")
        if target not in ids:
            errors.append(f"Unknown dependency target: {target}")
        if source == target:
            errors.append(f"Self dependency is not allowed: {source}")
    return errors


def validate_unique_project_ids(projects_path: Path) -> list[str]:
    projects = load_yaml(projects_path).get("projects", [])
    seen: set[str] = set()
    errors: list[str] = []
    for project in projects:
        pid = str(project["id"])
        if pid in seen:
            errors.append(f"Duplicate project id: {pid}")
        seen.add(pid)
    return errors
