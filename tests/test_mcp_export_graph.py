from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from new_earth_platform.mcp_export_graph import (
    EXPECTED_EXCLUDED_PATHS,
    EXPECTED_SCHEMA_PATHS,
    export_graph_summary,
    load_mcp_export_graph,
    schema_layout_is_portable,
    validate_bundle_path,
    validate_mcp_export_graph,
    validate_source_path,
)


@pytest.fixture
def graph_root(tmp_path: Path) -> Path:
    source_root = Path(__file__).parents[1]
    target = tmp_path / "platform-core"
    (target / "registry").mkdir(parents=True)
    shutil.copy2(source_root / "registry/mcp.yaml", target / "registry/mcp.yaml")
    shutil.copytree(source_root / "schemas", target / "schemas")
    shutil.copytree(source_root / "examples/mcp", target / "examples/mcp")
    return target


def _registry(root: Path) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load((root / "registry/mcp.yaml").read_text(encoding="utf-8")))


def _write_registry(root: Path, data: dict[str, Any]) -> None:
    (root / "registry/mcp.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_canonical_export_graph_validates(graph_root: Path) -> None:
    assert validate_mcp_export_graph(graph_root) == []
    assert export_graph_summary(graph_root) == {
        "total": 36,
        "registry": 1,
        "schemas": 19,
        "contracts": 16,
    }


def test_graph_includes_registry_schemas_and_canonical_declarations(graph_root: Path) -> None:
    entries = load_mcp_export_graph(graph_root)
    assert entries[0].source_path == "registry/mcp.yaml"
    assert sum(entry.category == "schema" for entry in entries) == 19
    assert sum(entry.category not in {"registry", "schema"} for entry in entries) == 16
    assert all(entry.bundle_path.startswith("contracts/") for entry in entries if entry.category not in {"registry", "schema"})


def test_development_only_files_are_excluded(graph_root: Path) -> None:
    entries = load_mcp_export_graph(graph_root)
    exported = {entry.source_path for entry in entries}
    assert EXPECTED_EXCLUDED_PATHS.isdisjoint(exported)
    assert "examples/mcp/mcp-client-identity.yaml" not in exported
    assert "examples/mcp/mcp-invocation-record-gaia-neos-health-read.yaml" not in exported
    assert "examples/mcp/mcp-authorization-decision-record-gaia-neos-health-read.yaml" not in exported


def test_source_path_safety_rejects_traversal_absolute_drive_and_unc(graph_root: Path) -> None:
    assert validate_source_path(graph_root, "examples/mcp/../secret.yaml")
    assert validate_source_path(graph_root, "/etc/passwd")
    assert validate_source_path(graph_root, "C:/outside.yaml")
    assert validate_source_path(graph_root, "\\\\server\\share\\outside.yaml")


@pytest.mark.parametrize("value", ["../outside.yaml", "/outside.yaml", "C:/outside.yaml", "\\\\server\\share\\outside.yaml"])
def test_bundle_path_safety_rejects_unsafe_paths(value: str) -> None:
    assert validate_bundle_path(value)


def test_missing_source_is_rejected(graph_root: Path) -> None:
    data = _registry(graph_root)
    entry = data["export_graph"]["entries"][0]
    entry["source_path"] = "registry/missing.yaml"
    _write_registry(graph_root, data)
    assert any("does not exist" in error for error in validate_mcp_export_graph(graph_root))


def test_duplicate_source_and_destination_are_rejected(graph_root: Path) -> None:
    data = _registry(graph_root)
    entries = data["export_graph"]["entries"]
    duplicate = dict(entries[-1])
    entries.append(duplicate)
    _write_registry(graph_root, data)
    errors = validate_mcp_export_graph(graph_root)
    assert any("Duplicate export source" in error for error in errors)
    assert any("Duplicate export bundle" in error for error in errors)


def test_windows_case_collision_is_rejected(graph_root: Path) -> None:
    data = _registry(graph_root)
    entries = data["export_graph"]["entries"]
    entries[-1]["bundle_path"] = entries[-2]["bundle_path"].upper()
    _write_registry(graph_root, data)
    errors = validate_mcp_export_graph(graph_root)
    assert any("Windows case collisions" in error for error in errors)


def test_unapproved_category_is_rejected(graph_root: Path) -> None:
    data = _registry(graph_root)
    data["export_graph"]["entries"][-1]["category"] = "runtime"
    _write_registry(graph_root, data)
    assert any("Unsupported export category" in error for error in validate_mcp_export_graph(graph_root))


def test_schema_layout_is_portable_and_has_no_machine_paths(graph_root: Path) -> None:
    assert set(EXPECTED_SCHEMA_PATHS) == {
        entry.source_path
        for entry in load_mcp_export_graph(graph_root)
        if entry.category == "schema"
    }
    assert schema_layout_is_portable(graph_root)
    assert not any(
        "C:/" in (graph_root / entry.source_path).read_text(encoding="utf-8")
        for entry in load_mcp_export_graph(graph_root)
        if entry.category not in {"registry", "schema"}
    )


def test_graph_traversal_is_deterministic(graph_root: Path) -> None:
    assert load_mcp_export_graph(graph_root) == load_mcp_export_graph(graph_root)
