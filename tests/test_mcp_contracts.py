from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, cast

import yaml

from new_earth_platform.validation import (
    validate_mcp_capability_contract_file,
    validate_mcp_client_identity_contract_file,
    validate_mcp_contracts,
    validate_mcp_server_identity_contract_file,
    validate_mcp_tool_contract_file,
)


def _copy_repo_data(root: Path, target: Path) -> None:
    for name in ["registry", "schemas", "compatibility", "examples", "NEW_EARTH_PROJECT.yaml"]:
        source = root / name
        destination = target / name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def test_mcp_identity_examples_validate() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_mcp_client_identity_contract_file(
        root / "examples/mcp/mcp-client-identity.yaml",
        root / "schemas/mcp-client-identity.schema.json",
    ) == []
    assert validate_mcp_server_identity_contract_file(
        root / "examples/mcp/mcp-server-identity.yaml",
        root / "schemas/mcp-server-identity.schema.json",
    ) == []


def test_mcp_capability_and_tool_examples_validate() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_mcp_capability_contract_file(
        root / "examples/mcp/mcp-capability-neos-engineering-read.yaml",
        root / "schemas/mcp-capability.schema.json",
        root,
    ) == []
    assert validate_mcp_tool_contract_file(
        root / "examples/mcp/mcp-tool-neos-health-read.yaml",
        root / "schemas/mcp-tool.schema.json",
        root,
    ) == []
    assert validate_mcp_tool_contract_file(
        root / "examples/mcp/mcp-tool-neos-project-summary-read.yaml",
        root / "schemas/mcp-tool.schema.json",
        root,
    ) == []


def test_existing_platform_core_owner_conventions_are_accepted(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    cap_path = tmp_path / "examples/mcp/mcp-capability-neos-engineering-read.yaml"
    tool_path = tmp_path / "examples/mcp/mcp-tool-neos-health-read.yaml"
    cap_schema = tmp_path / "schemas/mcp-capability.schema.json"
    tool_schema = tmp_path / "schemas/mcp-tool.schema.json"
    capability = _load_yaml(cap_path)
    tool = _load_yaml(tool_path)

    for owner_system_id in [
        "new-earth-platform-core",
        "new-earth-local-ai-runtime",
        "neos",
        "gaia",
        "command-centre",
    ]:
        capability["owner_system_id"] = owner_system_id
        tool["owner_system_id"] = owner_system_id
        cap_path.write_text(yaml.safe_dump(capability, sort_keys=False), encoding="utf-8")
        tool_path.write_text(yaml.safe_dump(tool, sort_keys=False), encoding="utf-8")
        assert validate_mcp_capability_contract_file(cap_path, cap_schema, tmp_path) == []
        assert validate_mcp_tool_contract_file(tool_path, tool_schema, tmp_path) == []


def test_mcp_registry_validates() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_mcp_contracts(root) == []


def test_missing_required_identity_fields_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)

    client_path = tmp_path / "examples/mcp/mcp-client-identity.yaml"
    client = _load_yaml(client_path)
    del client["client_id"]
    client_path.write_text(yaml.safe_dump(client, sort_keys=False), encoding="utf-8")
    client_errors = validate_mcp_client_identity_contract_file(
        client_path,
        tmp_path / "schemas/mcp-client-identity.schema.json",
    )
    assert any("client_id" in error and "required" in error for error in client_errors)

    server_path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    server = _load_yaml(server_path)
    del server["server_id"]
    server_path.write_text(yaml.safe_dump(server, sort_keys=False), encoding="utf-8")
    server_errors = validate_mcp_server_identity_contract_file(
        server_path,
        tmp_path / "schemas/mcp-server-identity.schema.json",
    )
    assert any("server_id" in error and "required" in error for error in server_errors)


def test_invalid_transport_and_bind_scope_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    server_path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    server = _load_yaml(server_path)
    server["transport"] = "grpc"
    server["bind_scope"] = "global"
    server_path.write_text(yaml.safe_dump(server, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_server_identity_contract_file(
        server_path,
        tmp_path / "schemas/mcp-server-identity.schema.json",
    )
    assert any("transport" in error for error in errors)
    assert any("bind_scope" in error for error in errors)


def test_invalid_lifecycle_status_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    cap_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(cap_path)
    registry["capabilities"][0]["status"] = "runtime"
    cap_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("status" in error for error in errors)


def test_read_only_and_side_effects_invariants_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["tools"][0]["read_only"] = False
    registry["tools"][1]["side_effects"] = True
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("read_only" in error for error in errors)
    assert any("side_effects" in error for error in errors)


def test_unsupported_operation_classification_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["tools"][0]["operation"] = "write.execute"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("operation" in error for error in errors)


def test_missing_input_and_output_schema_references_are_deterministic(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    tool_path = tmp_path / "examples/mcp/mcp-tool-neos-health-read.yaml"
    tool = _load_yaml(tool_path)
    del tool["input_schema_ref"]
    tool_path.write_text(yaml.safe_dump(tool, sort_keys=False), encoding="utf-8")
    input_errors = validate_mcp_tool_contract_file(
        tool_path,
        tmp_path / "schemas/mcp-tool.schema.json",
        tmp_path,
    )
    assert any("input_schema_ref" in error for error in input_errors)

    tool = _load_yaml(tool_path)
    tool["input_schema_ref"] = "schemas/mcp/empty-input.schema.json"
    del tool["output_schema_ref"]
    tool_path.write_text(yaml.safe_dump(tool, sort_keys=False), encoding="utf-8")
    output_errors = validate_mcp_tool_contract_file(
        tool_path,
        tmp_path / "schemas/mcp-tool.schema.json",
        tmp_path,
    )
    assert any("output_schema_ref" in error for error in output_errors)


def test_missing_input_and_output_schema_references_fail_deterministically(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    tool_path = tmp_path / "examples/mcp/mcp-tool-neos-health-read.yaml"
    tool = _load_yaml(tool_path)
    del tool["output_schema_ref"]
    tool_path.write_text(yaml.safe_dump(tool, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_tool_contract_file(tool_path, tmp_path / "schemas/mcp-tool.schema.json", tmp_path)
    assert any("output_schema_ref" in error for error in errors)


def test_duplicate_and_orphan_relationships_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)

    duplicate_capability = dict(registry["capabilities"][0])
    duplicate_capability["description"] = "Duplicate capability"
    registry["capabilities"].append(duplicate_capability)
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    duplicate_errors = validate_mcp_contracts(tmp_path)
    assert any("Duplicate capability id" in error for error in duplicate_errors)

    registry = _load_yaml(registry_path)
    registry["capabilities"] = registry["capabilities"][:1]
    duplicate_tool = dict(registry["tools"][0])
    duplicate_tool["description"] = "Duplicate tool"
    registry["tools"].append(duplicate_tool)
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    duplicate_tool_errors = validate_mcp_contracts(tmp_path)
    assert any("Duplicate tool id" in error for error in duplicate_tool_errors)

    registry = _load_yaml(registry_path)
    registry["tools"] = registry["tools"][:1]
    registry["capabilities"][0]["tool_ids"] = ["neos.health.read", "missing.tool"]
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    orphan_capability_errors = validate_mcp_contracts(tmp_path)
    assert any("Orphan capability reference" in error for error in orphan_capability_errors)

    registry = _load_yaml(registry_path)
    registry["capabilities"][0]["tool_ids"] = ["neos.health.read"]
    registry["tools"][0]["capability_id"] = "missing.capability"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    orphan_tool_errors = validate_mcp_contracts(tmp_path)
    assert any("Orphan tool reference" in error for error in orphan_tool_errors)


def test_server_and_owner_mismatch_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["tools"][0]["server_id"] = "other-server"
    registry["tools"][0]["owner_system_id"] = "gaia"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Server mismatch" in error for error in errors)
    assert any("Owner mismatch" in error for error in errors)


def test_missing_registry_entry_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["tools"].pop()
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Orphan capability reference" in error for error in errors)
