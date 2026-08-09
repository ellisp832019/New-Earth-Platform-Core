from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from .models import load_yaml


class ValidationFailure(Exception):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object at its root")
    return data


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


ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _duplicates(values: list[str], label: str) -> list[str]:
    seen: set[str] = set()
    errors: list[str] = []
    for value in values:
        if value in seen:
            errors.append(f"Duplicate {label}: {value}")
        seen.add(value)
    return errors


def validate_semver(value: str) -> bool:
    try:
        Version(value)
    except InvalidVersion:
        return False
    return True


def validate_requirement(value: str) -> bool:
    try:
        SpecifierSet(value)
    except InvalidSpecifier:
        return False
    return bool(value.strip())


def validate_project_contract_file(contract_path: Path, schema_path: Path) -> list[str]:
    errors = validate_yaml_against_schema(contract_path, schema_path)
    if errors:
        return errors
    data = load_yaml(contract_path)
    version = str(data["repository"]["version"])
    if not validate_semver(version):
        errors.append(f"{contract_path}: repository.version is not valid SemVer: {version}")
    return errors


def validate_contracts(root: Path) -> list[str]:
    projects = load_yaml(root / "registry/projects.yaml").get("projects", [])
    errors: list[str] = []
    schema = root / "schemas/project-contract.schema.json"
    for project in projects:
        contract = (root / str(project["contract"])).resolve()
        if root.resolve() not in contract.parents and contract != root.resolve():
            errors.append(f"Project contract path escapes repository for {project['id']}: {project['contract']}")
            continue
        if not contract.exists():
            errors.append(f"Missing project contract for {project['id']}: {project['contract']}")
            continue
        errors += validate_project_contract_file(contract, schema)
    return errors


def validate_registry(root: Path) -> list[str]:
    projects_data = load_yaml(root / "registry/projects.yaml").get("projects", [])
    dependencies = load_yaml(root / "registry/dependencies.yaml").get("dependencies", [])
    services = load_yaml(root / "registry/services.yaml").get("services", [])
    interfaces = load_yaml(root / "registry/interfaces.yaml").get("interfaces", [])
    releases = load_yaml(root / "registry/releases.yaml")
    compatibility = load_yaml(root / "compatibility/matrix.yaml").get("rules", [])

    projects = {str(project["id"]): project for project in projects_data}
    project_ids = list(projects)
    interface_ids = [str(interface["id"]) for interface in interfaces]
    service_ids = [str(service["id"]) for service in services]

    errors: list[str] = []
    errors += _duplicates([str(project["id"]) for project in projects_data], "project id")
    errors += _duplicates(service_ids, "service id")
    errors += _duplicates(interface_ids, "interface id")

    for project in projects_data:
        pid = str(project["id"])
        if not ID_RE.match(pid):
            errors.append(f"Invalid project id: {pid}")
        contract_path = (root / str(project["contract"])).resolve()
        if root.resolve() not in contract_path.parents and contract_path != root.resolve():
            errors.append(f"Project contract path escapes repository for {pid}: {project['contract']}")
        if not contract_path.exists():
            errors.append(f"Missing project contract for {pid}: {project['contract']}")

    edge_keys: set[tuple[str, str, str, str]] = set()
    allowed_kinds = {
        "compatible_with",
        "consumes",
        "controls",
        "depends_on",
        "observes",
        "provides",
        "publishes",
        "subscribes",
    }
    for edge in dependencies:
        source = str(edge["source"])
        target = str(edge["target"])
        kind = str(edge["kind"])
        contract = str(edge["contract"])
        key = (source, target, kind, contract)
        if source not in project_ids:
            errors.append(f"Unknown dependency source: {source}")
        if target not in project_ids:
            errors.append(f"Unknown dependency target: {target}")
        if source == target:
            errors.append(f"Self dependency is not allowed: {source}")
        if kind not in allowed_kinds:
            errors.append(f"Invalid dependency kind for {source}->{target}: {kind}")
        if not isinstance(edge.get("required"), bool):
            errors.append(f"Invalid required flag for dependency {source}->{target}: {edge.get('required')}")
        if key in edge_keys:
            errors.append(f"Duplicate dependency edge: {source}->{target} {kind} {contract}")
        edge_keys.add(key)
        if contract not in interface_ids and contract not in service_ids:
            errors.append(f"Dependency references missing contract/interface: {contract}")

    for service in services:
        owner = str(service["owner"])
        sid = str(service["id"])
        if owner not in project_ids:
            errors.append(f"Unknown service owner for {sid}: {owner}")
        version = service.get("version")
        if version is not None and not validate_semver(str(version)):
            errors.append(f"Malformed service version for {sid}: {version}")

    for interface in interfaces:
        owner = str(interface["owner"])
        iid = str(interface["id"])
        if owner not in project_ids:
            errors.append(f"Unknown interface owner for {iid}: {owner}")
        schema = interface.get("schema")
        if schema is not None and not (root / str(schema)).exists():
            errors.append(f"Missing interface schema for {iid}: {schema}")

    platform = releases.get("platform", {})
    current = str(platform.get("current", ""))
    if not validate_semver(current):
        errors.append(f"Malformed platform release version: {current}")

    for rule in compatibility:
        consumer = str(rule["consumer"])
        provider = str(rule["provider"])
        requirement = str(rule["requirement"])
        if consumer not in project_ids:
            errors.append(f"Unknown compatibility consumer: {consumer}")
        if provider not in project_ids:
            errors.append(f"Unknown compatibility provider: {provider}")
        if not validate_requirement(requirement):
            errors.append(f"Malformed compatibility requirement for {consumer}->{provider}: {requirement}")

    return errors
