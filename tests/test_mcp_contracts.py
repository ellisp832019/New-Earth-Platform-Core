from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, cast

import yaml

from new_earth_platform.validation import (
    validate_mcp_capability_contract_file,
    validate_mcp_client_identity_contract_file,
    validate_mcp_contracts,
    validate_mcp_query_contract_file,
    validate_mcp_resource_contract_file,
    validate_mcp_server_discovery_contract_file,
    validate_mcp_server_identity_contract_file,
    validate_mcp_server_manifest_contract_file,
    validate_mcp_tool_contract_file,
    validate_yaml_against_schema,
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


def test_mcp_resource_and_query_examples_validate() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_mcp_resource_contract_file(
        root / "examples/mcp/mcp-resource-neos-health.yaml",
        root / "schemas/mcp-resource.schema.json",
        root,
    ) == []
    assert validate_mcp_resource_contract_file(
        root / "examples/mcp/mcp-resource-neos-project-summary.yaml",
        root / "schemas/mcp-resource.schema.json",
        root,
    ) == []
    assert validate_mcp_query_contract_file(
        root / "examples/mcp/mcp-query-neos-health.yaml",
        root / "schemas/mcp-query.schema.json",
        root,
    ) == []
    assert validate_mcp_query_contract_file(
        root / "examples/mcp/mcp-query-neos-project-summary.yaml",
        root / "schemas/mcp-query.schema.json",
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


def test_mcp_server_manifest_example_validates() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_mcp_server_manifest_contract_file(
        root / "examples/mcp/mcp-server-manifest-neos-read.yaml",
        root / "schemas/mcp-server-manifest.schema.json",
    ) == []


def test_manifest_required_fields_and_version_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    manifest_path = tmp_path / "examples/mcp/mcp-server-manifest-neos-read.yaml"
    manifest = _load_yaml(manifest_path)
    del manifest["server_id"]
    manifest["version"] = "not-semver"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_server_manifest_contract_file(manifest_path, tmp_path / "schemas/mcp-server-manifest.schema.json")
    assert any("server_id" in error and "required" in error for error in errors)


def test_manifest_server_and_owner_mismatch_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["manifests"][0]["server_id"] = "missing-server"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("manifest server reference" in error for error in errors)

    registry["manifests"][0]["server_id"] = "neos-engineering-read-server"
    registry["manifests"][0]["owner_system_id"] = "gaia"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Owner mismatch for manifest" in error for error in errors)


def test_manifest_duplicate_id_and_references_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    manifest = registry["manifests"][0]
    duplicate = dict(manifest)
    registry["manifests"].append(duplicate)
    manifest["capability_ids"].append(manifest["capability_ids"][0])
    manifest["tool_ids"].append(manifest["tool_ids"][0])
    manifest["resource_ids"].append(manifest["resource_ids"][0])
    manifest["query_ids"].append(manifest["query_ids"][0])
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Duplicate manifest id" in error for error in errors)
    assert any("capability_ids" in error for error in errors)
    assert any("tool_ids" in error for error in errors)
    assert any("resource_ids" in error for error in errors)
    assert any("query_ids" in error for error in errors)


def test_manifest_cross_server_objects_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["manifests"][0]["capability_ids"] = ["neos.engineering.read"]
    registry["manifests"][0]["tool_ids"] = ["neos.health.read"]
    registry["manifests"][0]["resource_ids"] = ["neos.health"]
    registry["manifests"][0]["query_ids"] = ["neos.health.query"]
    registry["capabilities"][0]["server_id"] = "other-server"
    registry["tools"][0]["server_id"] = "other-server"
    registry["resources"][0]["server_id"] = "other-server"
    registry["queries"][0]["server_id"] = "other-server"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("manifest capability" in error and "Server mismatch" in error for error in errors)
    assert any("manifest tool" in error and "Server mismatch" in error for error in errors)
    assert any("manifest resource" in error and "Server mismatch" in error for error in errors)
    assert any("manifest query" in error and "Server mismatch" in error for error in errors)


def test_manifest_exposure_completeness_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    manifest = registry["manifests"][0]
    manifest["capability_ids"] = []
    manifest["resource_ids"] = []
    manifest["query_ids"] = ["neos.health.query"]
    manifest["tool_ids"] = ["neos.health.read"]
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Tool exposed without capability" in error for error in errors)
    assert any("Query exposed without resource" in error for error in errors)
    assert any("Query exposed without capability" in error for error in errors)


def test_manifest_unsafe_objects_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["tools"][0]["read_only"] = False
    registry["resources"][0]["read_only"] = False
    registry["queries"][0]["side_effects"] = True
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Unsafe tool exposure" in error for error in errors)
    assert any("Unsafe resource exposure" in error for error in errors)
    assert any("Unsafe query exposure" in error for error in errors)


def test_manifest_transport_bind_scope_and_subset_rules(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    manifest = registry["manifests"][0]
    manifest["tool_ids"] = ["neos.health.read"]
    manifest["resource_ids"] = []
    manifest["query_ids"] = []
    consumption = registry["consumptions"][0]
    consumption["expected_tool_ids"] = ["neos.health.read"]
    consumption["expected_resource_ids"] = []
    consumption["expected_query_ids"] = []
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    assert validate_mcp_contracts(tmp_path) == []

    manifest["transport"] = "grpc"
    manifest["bind_scope"] = "global"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("transport" in error for error in errors)
    assert any("bind_scope" in error for error in errors)


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


def test_missing_required_resource_and_query_fields_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)

    resource_path = tmp_path / "examples/mcp/mcp-resource-neos-health.yaml"
    resource = _load_yaml(resource_path)
    del resource["id"]
    resource_path.write_text(yaml.safe_dump(resource, sort_keys=False), encoding="utf-8")
    resource_errors = validate_mcp_resource_contract_file(
        resource_path,
        tmp_path / "schemas/mcp-resource.schema.json",
        tmp_path,
    )
    assert any("id" in error and "required" in error for error in resource_errors)

    query_path = tmp_path / "examples/mcp/mcp-query-neos-health.yaml"
    query = _load_yaml(query_path)
    del query["resource_id"]
    query_path.write_text(yaml.safe_dump(query, sort_keys=False), encoding="utf-8")
    query_errors = validate_mcp_query_contract_file(
        query_path,
        tmp_path / "schemas/mcp-query.schema.json",
        tmp_path,
    )
    assert any("resource_id" in error and "required" in error for error in query_errors)


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


def test_invalid_resource_and_query_shapes_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)

    resource_path = tmp_path / "examples/mcp/mcp-resource-neos-project-summary.yaml"
    resource = _load_yaml(resource_path)
    resource["read_only"] = False
    resource_path.write_text(yaml.safe_dump(resource, sort_keys=False), encoding="utf-8")
    resource_errors = validate_mcp_resource_contract_file(
        resource_path,
        tmp_path / "schemas/mcp-resource.schema.json",
        tmp_path,
    )
    assert any("read_only" in error for error in resource_errors)

    query_path = tmp_path / "examples/mcp/mcp-query-neos-project-summary.yaml"
    query = _load_yaml(query_path)
    query["side_effects"] = True
    query["pagination"] = "invalid"
    query["filtering"] = {"operators": ["eq", "unsupported"]}
    query["sorting"] = {"directions": ["asc", "sideways"]}
    query_path.write_text(yaml.safe_dump(query, sort_keys=False), encoding="utf-8")
    query_errors = validate_mcp_query_contract_file(
        query_path,
        tmp_path / "schemas/mcp-query.schema.json",
        tmp_path,
    )
    assert any("side_effects" in error for error in query_errors)
    assert any("pagination" in error for error in query_errors)
    assert any("filter" in error.lower() for error in query_errors)
    assert any("sorting" in error.lower() for error in query_errors)


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


def test_duplicate_resource_and_query_relationships_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)

    duplicate_resource = dict(registry["resources"][0])
    duplicate_resource["description"] = "Duplicate resource"
    registry["resources"].append(duplicate_resource)
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    duplicate_resource_errors = validate_mcp_contracts(tmp_path)
    assert any("Duplicate resource id" in error for error in duplicate_resource_errors)

    registry = _load_yaml(registry_path)
    registry["resources"] = registry["resources"][:2]
    duplicate_query = dict(registry["queries"][0])
    duplicate_query["description"] = "Duplicate query"
    registry["queries"].append(duplicate_query)
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    duplicate_query_errors = validate_mcp_contracts(tmp_path)
    assert any("Duplicate query id" in error for error in duplicate_query_errors)


def test_query_resource_and_tool_relationships_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["resources"][0]["query_ids"] = ["missing.query"]
    registry["queries"][0]["resource_id"] = "missing.resource"
    registry["tools"][0]["query_ids"] = ["missing.query"]
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Orphan resource query reference" in error for error in errors)
    assert any("Orphan query resource reference" in error for error in errors)
    assert any("Orphan tool query reference" in error for error in errors)


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


def test_query_operation_and_pagination_rules_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["queries"][1]["operation"] = "write.execute"
    registry["queries"][1]["filtering"]["operators"] = ["eq", "unsupported"]
    registry["queries"][1]["sorting"]["directions"] = ["asc", "invalid"]
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("unsupported MCP query operation" in error or "operation" in error for error in errors)
    assert any("filter" in error.lower() for error in errors)
    assert any("sorting" in error.lower() for error in errors)


def test_query_pagination_bounds_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["queries"][1]["operation"] = "summary"
    registry["queries"][1]["pagination"]["max_page_size"] = 5
    registry["queries"][1]["pagination"]["default_page_size"] = 10
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("max_page_size" in error for error in errors)


def test_missing_registry_entry_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["tools"].pop()
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Orphan capability reference" in error for error in errors)


def test_mcp_consumption_and_discovery_examples_validate() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_mcp_server_discovery_contract_file(
        root / "examples/mcp/mcp-server-discovery-neos-local.yaml",
        root / "schemas/mcp-server-discovery.schema.json",
    ) == []
    assert validate_yaml_against_schema(
        root / "examples/mcp/mcp-client-consumption-gaia-neos-read.yaml",
        root / "schemas/mcp-client-consumption.schema.json",
    ) == []
    assert validate_mcp_contracts(root) == []


def test_consumption_missing_client_server_and_manifest_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    consumption = registry["consumptions"][0]

    consumption["client_id"] = "missing-client"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("consumption client reference" in error for error in errors)

    consumption["client_id"] = "new-earth-platform-core-mcp-client"
    consumption["server_id"] = "missing-server"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("consumption server reference" in error for error in errors)

    consumption["server_id"] = "neos-engineering-read-server"
    consumption["expected_manifest_id"] = "missing.manifest"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("consumption manifest reference" in error for error in errors)


def test_consumption_manifest_server_and_owner_mismatch_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["consumptions"][0]["server_id"] = "other-server"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("consumption server reference" in error for error in errors)

    registry["consumptions"][0]["server_id"] = "neos-engineering-read-server"
    registry["consumptions"][0]["owner_system_id"] = "gaia"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Owner mismatch for consumption" in error for error in errors)


def test_duplicate_consumption_and_expected_references_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    consumption = registry["consumptions"][0]
    registry["consumptions"].append(dict(consumption))
    consumption["expected_capability_ids"].append(consumption["expected_capability_ids"][0])
    consumption["expected_tool_ids"].append(consumption["expected_tool_ids"][0])
    consumption["expected_resource_ids"].append(consumption["expected_resource_ids"][0])
    consumption["expected_query_ids"].append(consumption["expected_query_ids"][0])
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Duplicate consumption id" in error for error in errors)
    assert any("expected_capability_ids" in error for error in errors)
    assert any("expected_tool_ids" in error for error in errors)
    assert any("expected_resource_ids" in error for error in errors)
    assert any("expected_query_ids" in error for error in errors)


def test_unexposed_consumption_objects_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    consumption = registry["consumptions"][0]
    consumption["expected_capability_ids"] = []
    consumption["expected_tool_ids"] = ["neos.health.read"]
    consumption["expected_resource_ids"] = []
    consumption["expected_query_ids"] = ["neos.health.query"]
    registry["manifests"][0]["tool_ids"] = []
    registry["manifests"][0]["query_ids"] = []
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Unexposed expected tool" in error for error in errors)
    assert any("Unexposed expected query" in error for error in errors)
    assert any("Expected query resource missing" in error for error in errors)


def test_unsafe_consumption_objects_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["tools"][0]["read_only"] = False
    registry["resources"][0]["read_only"] = False
    registry["queries"][0]["side_effects"] = True
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Unsafe expected tool" in error for error in errors)
    assert any("Unsafe expected resource" in error for error in errors)
    assert any("Unsafe expected query" in error for error in errors)


def test_required_optional_and_subset_consumption_are_valid(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    consumption = registry["consumptions"][0]
    consumption["required"] = True
    consumption["expected_tool_ids"] = ["neos.health.read"]
    consumption["expected_resource_ids"] = ["neos.health"]
    consumption["expected_query_ids"] = ["neos.health.query"]
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    assert validate_mcp_contracts(tmp_path) == []


def test_discovery_server_transport_bind_endpoint_and_priority_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    discovery = registry["discoveries"][0]
    discovery["server_id"] = "missing-server"
    discovery["transport"] = "grpc"
    discovery["bind_scope"] = "global"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("discovery server reference" in error for error in errors)

    discovery["server_id"] = "neos-engineering-read-server"
    discovery["transport"] = "stdio"
    discovery["bind_scope"] = "local-only"
    discovery["discovery_mode"] = "localhost_endpoint"
    discovery["endpoint_hint"] = "http://remote.example:8080"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("localhost" in error for error in errors)

    discovery["discovery_mode"] = "local_registry"
    discovery.pop("endpoint_hint")
    duplicate = dict(discovery)
    duplicate["id"] = "neos.engineering.read.other"
    registry["discoveries"].append(duplicate)
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Ambiguous discovery priority" in error for error in errors)


def test_discovery_duplicate_id_and_consumption_compatibility_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["discoveries"].append(dict(registry["discoveries"][0]))
    registry["consumptions"][0]["compatibility"]["minimum_server_version"] = "2.0.0"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Duplicate discovery id" in error for error in errors)
    assert any("Incompatible server version" in error for error in errors)


def test_authorization_and_approval_examples_validate() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_yaml_against_schema(
        root / "examples/mcp/mcp-authorization-policy-gaia-neos-read.yaml",
        root / "schemas/mcp-authorization-policy.schema.json",
    ) == []
    assert validate_yaml_against_schema(
        root / "examples/mcp/mcp-authorization-policy-neos-project-deny.yaml",
        root / "schemas/mcp-authorization-policy.schema.json",
    ) == []
    assert validate_yaml_against_schema(
        root / "examples/mcp/mcp-approval-policy-command-centre-elevated-read.yaml",
        root / "schemas/mcp-approval-policy.schema.json",
    ) == []
    assert validate_mcp_contracts(root) == []


def test_policy_required_subject_and_targets_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    policy = registry["authorization_policies"][0]
    del policy["subject"]
    policy["server_ids"] = ["missing-server"]
    policy["capability_ids"] = ["missing.capability"]
    policy["tool_ids"] = ["missing.tool"]
    policy["resource_ids"] = ["missing.resource"]
    policy["query_ids"] = ["missing.query"]
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("subject" in error for error in errors)
    assert any("Unknown policy server target" in error for error in errors)
    assert any("Unknown policy capability target" in error for error in errors)
    assert any("Unknown policy tool target" in error for error in errors)
    assert any("Unknown policy resource target" in error for error in errors)
    assert any("Unknown policy query target" in error for error in errors)


def test_duplicate_policy_and_approval_ids_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["authorization_policies"].append(dict(registry["authorization_policies"][0]))
    registry["approval_policies"].append(dict(registry["approval_policies"][0]))
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Duplicate authorization policy id" in error for error in errors)
    assert any("Duplicate approval policy id" in error for error in errors)


def test_invalid_policy_effect_and_priority_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["authorization_policies"][0]["effect"] = "grant"
    registry["authorization_policies"][0]["priority"] = -1
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("effect" in error for error in errors)
    assert any("priority" in error for error in errors)


def test_approval_required_linkage_and_approval_class_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    policy = registry["authorization_policies"][2]
    del policy["approval_policy_id"]
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("missing approval policy" in error for error in errors)

    policy["approval_policy_id"] = "missing.approval"
    registry["approval_policies"][0]["approval_class"] = "runtime_approval"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Unknown approval policy" in error for error in errors)
    assert any("approval_class" in error for error in errors)


def test_approver_authority_and_self_approval_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["approval_policies"][0]["approver_system_id"] = "missing-system"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Unknown approver authority" in error for error in errors)

    registry["approval_policies"][0]["approver_system_id"] = "new-earth-platform-core"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Self-approval is not allowed" in error for error in errors)


def test_unsafe_policy_targets_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    policy = registry["authorization_policies"][0]
    registry["tools"][0]["side_effects"] = True
    registry["resources"][0]["read_only"] = False
    registry["queries"][0]["read_only"] = False
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Unsafe policy tool target" in error for error in errors)
    assert any("Unsafe policy resource target" in error for error in errors)
    assert any("Unsafe policy query target" in error for error in errors)
    assert policy["effect"] == "allow"


def test_same_priority_policy_conflict_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    conflict = dict(registry["authorization_policies"][0])
    conflict["id"] = "gaia.neos.engineering.read.deny.same-priority"
    conflict["effect"] = "deny"
    registry["authorization_policies"].append(conflict)
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_contracts(tmp_path)
    assert any("Conflicting same-priority policies" in error for error in errors)


def test_audit_and_expiry_declarations_validate(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    registry_path = tmp_path / "registry/mcp.yaml"
    registry = _load_yaml(registry_path)
    registry["authorization_policies"][0]["audit_required"] = True
    registry["approval_policies"][0]["expiry"] = {"mode": "single_use"}
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    assert validate_mcp_contracts(tmp_path) == []
