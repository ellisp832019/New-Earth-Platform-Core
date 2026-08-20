from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from new_earth_platform.validation import (
    validate_mcp_client_identity_contract_file,
    validate_mcp_server_identity_contract_file,
)


def _copy_repo_data(root: Path, target: Path) -> None:
    for name in ["registry", "schemas", "compatibility", "examples", "NEW_EARTH_PROJECT.yaml"]:
        source = root / name
        destination = target / name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def test_mcp_client_identity_example_validates() -> None:
    root = Path(__file__).resolve().parents[1]
    contract = root / "examples/mcp/mcp-client-identity.yaml"
    schema = root / "schemas/mcp-client-identity.schema.json"
    assert validate_mcp_client_identity_contract_file(contract, schema) == []


def test_mcp_server_identity_example_validates() -> None:
    root = Path(__file__).resolve().parents[1]
    contract = root / "examples/mcp/mcp-server-identity.yaml"
    schema = root / "schemas/mcp-server-identity.schema.json"
    assert validate_mcp_server_identity_contract_file(contract, schema) == []


def test_owner_system_id_tracks_existing_platform_core_identity_conventions(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    client_path = tmp_path / "examples/mcp/mcp-client-identity.yaml"
    server_path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    client_schema = tmp_path / "schemas/mcp-client-identity.schema.json"
    server_schema = tmp_path / "schemas/mcp-server-identity.schema.json"
    client = yaml.safe_load(client_path.read_text(encoding="utf-8"))
    server = yaml.safe_load(server_path.read_text(encoding="utf-8"))

    for owner_system_id in [
        "new-earth-platform-core",
        "new-earth-local-ai-runtime",
        "neos",
        "gaia",
        "command-centre",
    ]:
        client["owner_system_id"] = owner_system_id
        server["owner_system_id"] = owner_system_id
        client_path.write_text(yaml.safe_dump(client, sort_keys=False), encoding="utf-8")
        server_path.write_text(yaml.safe_dump(server, sort_keys=False), encoding="utf-8")
        assert validate_mcp_client_identity_contract_file(client_path, client_schema) == []
        assert validate_mcp_server_identity_contract_file(server_path, server_schema) == []


def test_missing_required_client_fields_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "examples/mcp/mcp-client-identity.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    del data["client_id"]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_client_identity_contract_file(path, tmp_path / "schemas/mcp-client-identity.schema.json")
    assert any("client_id" in error and "required" in error for error in errors)


def test_missing_required_server_fields_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    del data["server_id"]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_server_identity_contract_file(path, tmp_path / "schemas/mcp-server-identity.schema.json")
    assert any("server_id" in error and "required" in error for error in errors)


def test_invalid_transport_fails(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["transport"] = "grpc"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_server_identity_contract_file(path, tmp_path / "schemas/mcp-server-identity.schema.json")
    assert any("transport" in error for error in errors)


def test_invalid_bind_scope_fails(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["bind_scope"] = "global"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_server_identity_contract_file(path, tmp_path / "schemas/mcp-server-identity.schema.json")
    assert any("bind_scope" in error for error in errors)


def test_namespaced_tool_identifiers_are_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "examples/mcp/mcp-server-identity.yaml"
    schema = root / "schemas/mcp-server-identity.schema.json"
    assert validate_mcp_server_identity_contract_file(path, schema) == []


def test_empty_identifier_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["declared_tools"][0] = ""
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_server_identity_contract_file(path, tmp_path / "schemas/mcp-server-identity.schema.json")
    assert any("declared_tools" in error for error in errors)


def test_raw_windows_path_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["declared_resources"][0] = r"C:\Users\ellis\secrets"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_server_identity_contract_file(path, tmp_path / "schemas/mcp-server-identity.schema.json")
    assert any("declared_resources" in error for error in errors)


def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["declared_resources"][0] = "../secrets"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_server_identity_contract_file(path, tmp_path / "schemas/mcp-server-identity.schema.json")
    assert any("declared_resources" in error for error in errors)


def test_whitespace_containing_identifier_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["declared_tools"][0] = "neos.get system_health"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_server_identity_contract_file(path, tmp_path / "schemas/mcp-server-identity.schema.json")
    assert any("declared_tools" in error for error in errors)


def test_malformed_namespaced_tool_identifier_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["declared_tools"][0] = "neos.get__system_health"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    errors = validate_mcp_server_identity_contract_file(path, tmp_path / "schemas/mcp-server-identity.schema.json")
    assert any("declared_tools" in error for error in errors)


def test_malformed_capability_tool_resource_structures_fail(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    client_path = tmp_path / "examples/mcp/mcp-client-identity.yaml"
    client_data = yaml.safe_load(client_path.read_text(encoding="utf-8"))
    client_data["declared_capabilities"] = ["platform.read_registry", {"bad": "shape"}]
    client_path.write_text(yaml.safe_dump(client_data, sort_keys=False), encoding="utf-8")

    server_path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    server_data = yaml.safe_load(server_path.read_text(encoding="utf-8"))
    server_data["declared_tools"] = {"bad": "shape"}
    server_data["declared_resources"] = ["mcp://new-earth/schema-catalog", {"bad": "shape"}]
    server_path.write_text(yaml.safe_dump(server_data, sort_keys=False), encoding="utf-8")

    client_errors = validate_mcp_client_identity_contract_file(
        client_path, tmp_path / "schemas/mcp-client-identity.schema.json"
    )
    server_errors = validate_mcp_server_identity_contract_file(
        server_path, tmp_path / "schemas/mcp-server-identity.schema.json"
    )
    assert any("declared_capabilities" in error for error in client_errors)
    assert any("declared_tools" in error or "declared_resources" in error for error in server_errors)


def test_duplicate_values_fail_where_uniqueness_is_required(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    client_path = tmp_path / "examples/mcp/mcp-client-identity.yaml"
    client_data = yaml.safe_load(client_path.read_text(encoding="utf-8"))
    client_data["declared_capabilities"].append(client_data["declared_capabilities"][0])
    client_path.write_text(yaml.safe_dump(client_data, sort_keys=False), encoding="utf-8")

    server_path = tmp_path / "examples/mcp/mcp-server-identity.yaml"
    server_data = yaml.safe_load(server_path.read_text(encoding="utf-8"))
    server_data["declared_tools"].append(server_data["declared_tools"][0])
    server_data["declared_resources"].append(server_data["declared_resources"][0])
    server_path.write_text(yaml.safe_dump(server_data, sort_keys=False), encoding="utf-8")

    client_errors = validate_mcp_client_identity_contract_file(
        client_path, tmp_path / "schemas/mcp-client-identity.schema.json"
    )
    server_errors = validate_mcp_server_identity_contract_file(
        server_path, tmp_path / "schemas/mcp-server-identity.schema.json"
    )
    assert any("unique" in error.lower() for error in client_errors)
    assert any("unique" in error.lower() for error in server_errors)
