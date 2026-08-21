from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

import yaml

from .validation import validate_semver

EXPECTED_BASELINE_ID = "NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21"
EXPECTED_FORMAT_VERSION = "1.0.0"
EXPECTED_CATEGORIES = {
    "registry",
    "schema",
    "identity",
    "capability",
    "tool",
    "resource",
    "query",
    "manifest",
    "consumption",
    "discovery",
    "policy",
}
EXPECTED_SCHEMA_PATHS = frozenset(
    {
        "schemas/mcp-approval-policy.schema.json",
        "schemas/mcp-authorization-decision-record.schema.json",
        "schemas/mcp-authorization-policy.schema.json",
        "schemas/mcp-capability.schema.json",
        "schemas/mcp-client-consumption.schema.json",
        "schemas/mcp-client-identity.schema.json",
        "schemas/mcp-invocation-record.schema.json",
        "schemas/mcp-query.schema.json",
        "schemas/mcp-resource.schema.json",
        "schemas/mcp-server-discovery.schema.json",
        "schemas/mcp-server-identity.schema.json",
        "schemas/mcp-server-manifest.schema.json",
        "schemas/mcp-tool.schema.json",
        "schemas/mcp/empty-input.schema.json",
        "schemas/mcp/neos-health-read.output.schema.json",
        "schemas/mcp/neos-health-resource.schema.json",
        "schemas/mcp/neos-project-summary-query-parameters.schema.json",
        "schemas/mcp/neos-project-summary-read.output.schema.json",
        "schemas/mcp/neos-project-summary-resource.schema.json",
    }
)
EXPECTED_EXCLUDED_PATHS = frozenset(
    {
        "examples/mcp/mcp-client-identity.yaml",
        "examples/mcp/mcp-invocation-record-gaia-neos-health-read.yaml",
        "examples/mcp/mcp-authorization-decision-record-gaia-neos-health-read.yaml",
    }
)
CATEGORY_ORDER = {
    "registry": 0,
    "schema": 1,
    "identity": 2,
    "capability": 3,
    "tool": 4,
    "resource": 5,
    "query": 6,
    "manifest": 7,
    "consumption": 8,
    "discovery": 9,
    "policy": 10,
}
MACHINE_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\)")
APPROVED_SOURCE_ROOTS = frozenset({"registry", "schemas", "examples"})


@dataclass(frozen=True)
class McpBundleExportEntry:
    source_path: str
    bundle_path: str
    category: str
    required: bool
    canonical_id: str | None = None


def _load_registry(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    path = root / "registry/mcp.yaml"
    if not path.is_file():
        return None, [f"Missing MCP registry: {path}"]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, [f"Unable to load MCP registry: {exc}"]
    if not isinstance(data, dict):
        return None, ["MCP registry must be an object"]
    return data, []


def _path_parts(value: Any, field: str) -> tuple[tuple[str, ...] | None, list[str]]:
    if not isinstance(value, str) or not value.strip():
        return None, [f"{field} must be a non-empty relative path"]
    normalized = value.replace("\\", "/")
    windows = PureWindowsPath(value)
    if windows.drive or windows.root or normalized.startswith("/"):
        return None, [f"{field} must not be absolute: {value}"]
    parts = tuple(part for part in normalized.split("/") if part)
    if not parts or any(part in {".", ".."} for part in parts):
        return None, [f"{field} contains unsafe traversal: {value}"]
    return parts, []


def validate_bundle_path(value: Any) -> list[str]:
    _, errors = _path_parts(value, "bundle_path")
    return errors


def _has_reparse_point(path: Path, root: Path) -> bool:
    current = root
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    for part in relative.parts:
        current /= part
        try:
            info = current.lstat()
        except OSError:
            return False
        if stat.S_ISLNK(info.st_mode):
            return True
        if getattr(info, "st_file_attributes", 0) & 0x400:
            return True
    return False


def validate_source_path(root: Path, value: Any) -> list[str]:
    parts, errors = _path_parts(value, "source_path")
    if errors or parts is None:
        return errors
    if parts[0] not in APPROVED_SOURCE_ROOTS or (parts[0] == "examples" and parts[1:2] != ("mcp",)):
        return [f"source_path is outside approved roots: {value}"]
    repository_root = root.resolve()
    candidate = (repository_root.joinpath(*parts)).resolve(strict=False)
    try:
        candidate.relative_to(repository_root)
    except ValueError:
        return [f"source_path escapes repository root: {value}"]
    if _has_reparse_point(repository_root.joinpath(*parts), repository_root):
        return [f"source_path contains a symlink or reparse point: {value}"]
    if not candidate.is_file():
        return [f"source_path does not exist as a file: {value}"]
    return []


def _entries_from_registry(data: dict[str, Any]) -> tuple[list[McpBundleExportEntry], list[str]]:
    graph = data.get("export_graph")
    if not isinstance(graph, dict):
        return [], ["MCP export_graph is missing or malformed"]
    raw_entries = graph.get("entries")
    if not isinstance(raw_entries, list):
        return [], ["MCP export_graph.entries must be an array"]
    entries: list[McpBundleExportEntry] = []
    errors: list[str] = []
    for index, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            errors.append(f"export_graph.entries[{index}] must be an object")
            continue
        category = raw.get("category")
        if category not in EXPECTED_CATEGORIES:
            errors.append(f"Unsupported export category at index {index}: {category}")
        required = raw.get("required")
        if not isinstance(required, bool):
            errors.append(f"Export entry {index} required must be boolean")
        canonical_id = raw.get("canonical_id")
        if canonical_id is not None and not isinstance(canonical_id, str):
            errors.append(f"Export entry {index} canonical_id must be a string")
        entries.append(
            McpBundleExportEntry(
                source_path=str(raw.get("source_path", "")),
                bundle_path=str(raw.get("bundle_path", "")),
                category=str(category),
                required=required is True,
                canonical_id=canonical_id,
            )
        )
    return entries, errors


def load_mcp_export_graph(root: Path) -> tuple[McpBundleExportEntry, ...]:
    data, errors = _load_registry(root)
    if errors or data is None:
        raise ValueError("; ".join(errors))
    entries, errors = _entries_from_registry(data)
    if errors:
        raise ValueError("; ".join(errors))
    return tuple(entries)


def _registry_ids(data: dict[str, Any]) -> dict[str, set[str]]:
    mapping = {
        "identity": ("clients", "client_id"),
        "manifest": ("manifests", "id"),
        "capability": ("capabilities", "id"),
        "tool": ("tools", "id"),
        "resource": ("resources", "id"),
        "query": ("queries", "id"),
        "consumption": ("consumptions", "id"),
        "discovery": ("discoveries", "id"),
    }
    result: dict[str, set[str]] = {}
    for category, (section, key) in mapping.items():
        result[category] = {
            str(item[key])
            for item in data.get(section, [])
            if isinstance(item, dict) and key in item
        }
    result["identity"].update(
        str(item["server_id"])
        for item in data.get("servers", [])
        if isinstance(item, dict) and "server_id" in item
    )
    result["policy"] = {
        str(item["id"])
        for section in ("authorization_policies", "approval_policies")
        for item in data.get(section, [])
        if isinstance(item, dict) and "id" in item
    }
    return result


def validate_mcp_export_graph(root: Path) -> list[str]:
    data, errors = _load_registry(root)
    if errors or data is None:
        return errors
    graph = data.get("export_graph")
    if not isinstance(graph, dict):
        return ["MCP export_graph is missing or malformed"]
    if graph.get("format_version") != EXPECTED_FORMAT_VERSION:
        errors.append("MCP export_graph format_version must be 1.0.0")
    if graph.get("contract_baseline_id") != EXPECTED_BASELINE_ID:
        errors.append("MCP export_graph baseline ID does not match the frozen baseline")

    entries, entry_errors = _entries_from_registry(data)
    errors.extend(entry_errors)
    if not entries:
        return errors
    source_keys: list[str] = []
    destination_keys: list[str] = []
    for entry in entries:
        errors.extend(validate_source_path(root, entry.source_path))
        errors.extend(validate_bundle_path(entry.bundle_path))
        source_keys.append(entry.source_path.replace("\\", "/").casefold())
        destination_keys.append(entry.bundle_path.replace("\\", "/").casefold())
        if entry.category == "registry" and entry.source_path != "registry/mcp.yaml":
            errors.append("The registry export entry must use registry/mcp.yaml")
        if entry.category != "schema" and entry.canonical_id is None and entry.category != "registry":
            errors.append(f"Missing canonical_id for {entry.category}: {entry.source_path}")
        if entry.category == "schema" and entry.canonical_id is not None:
            errors.append(f"Schema export must not declare canonical_id: {entry.source_path}")
        source_path = root / entry.source_path.replace("/", os.sep)
        if source_path.is_file() and entry.category not in {"registry", "schema"}:
            try:
                if MACHINE_PATH_PATTERN.search(source_path.read_text(encoding="utf-8")):
                    errors.append(f"Machine-specific path in contract: {entry.source_path}")
            except UnicodeDecodeError:
                errors.append(f"Contract is not UTF-8 text: {entry.source_path}")

    if len(source_keys) != len(set(source_keys)):
        errors.append("Duplicate export source paths are not allowed")
    if len(destination_keys) != len(set(destination_keys)):
        errors.append("Duplicate export bundle paths or Windows case collisions are not allowed")
    registry_entries = [entry for entry in entries if entry.category == "registry"]
    if len(registry_entries) != 1:
        errors.append("MCP export graph must contain exactly one registry entry")

    schema_entries = {entry.source_path.replace("\\", "/") for entry in entries if entry.category == "schema"}
    if schema_entries != EXPECTED_SCHEMA_PATHS:
        errors.append("MCP export graph must include exactly the 19 required MCP schemas")
    if any(not entry.required for entry in entries):
        errors.append("All current MCP export graph entries must be required")

    excluded = graph.get("excluded_source_paths")
    if not isinstance(excluded, list) or {str(value).replace("\\", "/") for value in excluded} != EXPECTED_EXCLUDED_PATHS:
        errors.append("MCP export graph exclusions do not match the development-only MCP files")
    if source_keys and any(path.casefold() in source_keys for path in EXPECTED_EXCLUDED_PATHS):
        errors.append("Development-only MCP files must not be exported")

    registered_ids = _registry_ids(data)
    for entry in entries:
        if entry.canonical_id is not None and entry.canonical_id not in registered_ids.get(entry.category, set()):
            errors.append(f"Export declaration is not registered in the MCP graph: {entry.canonical_id}")
    if any(entry.category == "registry" for entry in entries) and not validate_semver(str(graph.get("format_version"))):
        errors.append("MCP export_graph format_version must be semantic version")
    return errors


def export_graph_summary(root: Path) -> dict[str, int]:
    entries = load_mcp_export_graph(root)
    return {
        "total": len(entries),
        "registry": sum(entry.category == "registry" for entry in entries),
        "schemas": sum(entry.category == "schema" for entry in entries),
        "contracts": sum(entry.category not in {"registry", "schema"} for entry in entries),
    }


def schema_layout_is_portable(root: Path) -> bool:
    for path in EXPECTED_SCHEMA_PATHS:
        try:
            data = json.loads((root / path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if isinstance(data, dict) and "$ref" in data and not str(data["$ref"]).startswith("#"):
            return False
    return True
