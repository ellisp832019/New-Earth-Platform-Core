from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

import yaml

from .mcp_export_graph import (
    EXPECTED_BASELINE_ID,
    EXPECTED_FORMAT_VERSION,
    McpBundleExportEntry,
    load_mcp_export_graph,
    validate_bundle_path,
    validate_mcp_export_graph,
    validate_source_path,
)
from .service import validate_repository
from .validation import (
    _validate_mcp_approval_policy_data,
    _validate_mcp_authorization_policy_data,
    _validate_mcp_consumption_data,
    _validate_mcp_discovery_data,
    _validate_mcp_manifest_data,
    validate_instance_against_schema,
    validate_mcp_client_identity_contract_file,
    validate_mcp_query_contract_file,
    validate_mcp_resource_contract_file,
    validate_mcp_server_identity_contract_file,
    validate_mcp_server_manifest_contract_file,
    validate_mcp_tool_contract_file,
)

BUNDLE_ID = "new-earth-mcp-contract-bundle-v1"
HASH_ALGORITHM = "SHA-256"
SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
MANIFEST_NAME = "bundle-manifest.json"
HASHES_NAME = "hashes/SHA256SUMS.txt"
CONTROL_FILES = frozenset({MANIFEST_NAME, HASHES_NAME})


class BundleError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _root_hash(hashes: dict[str, str]) -> str:
    payload = "".join(f"{path}  {hashes[path]}\n" for path in sorted(hashes)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git_output(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BundleError("SOURCE_SHA_UNAVAILABLE", "Unable to determine Platform Core commit") from exc
    return result.stdout.strip()


def _source_commit(root: Path) -> str:
    commit = _git_output(root, "rev-parse", "HEAD")
    if not COMMIT_PATTERN.fullmatch(commit):
        raise BundleError("SOURCE_SHA_INVALID", "Platform Core HEAD is not a full commit SHA")
    status = _git_output(root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise BundleError("DIRTY_SOURCE_TREE", "Export requires a clean Platform Core source tree")
    return commit


def _manifest_payload(entries: tuple[McpBundleExportEntry, ...], commit: str, hashes: dict[str, str]) -> dict[str, Any]:
    schema_paths = sorted(entry.bundle_path for entry in entries if entry.category == "schema")
    contract_paths = sorted(entry.bundle_path for entry in entries if entry.category not in {"registry", "schema"})
    return {
        "bundle_id": BUNDLE_ID,
        "bundle_format_version": EXPECTED_FORMAT_VERSION,
        "contract_baseline_id": EXPECTED_BASELINE_ID,
        "platform_core_commit": commit,
        "registry_path": "registry/mcp.yaml",
        "schema_paths": schema_paths,
        "contract_paths": contract_paths,
        "hash_algorithm": HASH_ALGORITHM,
        "content_root_hash": _root_hash(hashes),
        "read_only": True,
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _payload_hashes(bundle: Path, payload_paths: list[str]) -> dict[str, str]:
    return {path: _sha256(bundle / path) for path in sorted(payload_paths)}


def _write_hashes(path: Path, hashes: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{digest}  {name}\n" for name, digest in sorted(hashes.items())), encoding="utf-8", newline="\n")


def _parse_hashes(bundle: Path) -> dict[str, str]:
    path = bundle / HASHES_NAME
    if not path.is_file():
        raise BundleError("MISSING_BUNDLE_FILE", f"Missing hash listing: {HASHES_NAME}")
    result: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("  ", 1)
        if len(parts) != 2 or not SHA_PATTERN.fullmatch(parts[0]):
            raise BundleError("MANIFEST_INVALID", f"Invalid hash listing line {line_number}")
        relative = parts[1]
        if validate_bundle_path(relative):
            raise BundleError("UNSAFE_DESTINATION_PATH", f"Unsafe hash path: {relative}")
        if relative in result:
            raise BundleError("MANIFEST_INVALID", f"Duplicate hash path: {relative}")
        result[relative] = parts[0]
    return result


def _manifest(bundle: Path) -> dict[str, Any]:
    path = bundle / MANIFEST_NAME
    if not path.is_file():
        raise BundleError("MISSING_BUNDLE_FILE", f"Missing manifest: {MANIFEST_NAME}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleError("MANIFEST_INVALID", "Bundle manifest is not valid JSON") from exc
    if not isinstance(data, dict):
        raise BundleError("MANIFEST_INVALID", "Bundle manifest must be an object")
    required = {
        "bundle_id",
        "bundle_format_version",
        "contract_baseline_id",
        "platform_core_commit",
        "registry_path",
        "schema_paths",
        "contract_paths",
        "hash_algorithm",
        "content_root_hash",
        "read_only",
    }
    if not required.issubset(data):
        raise BundleError("MANIFEST_INVALID", "Bundle manifest is missing required fields")
    if data["bundle_id"] != BUNDLE_ID or data["bundle_format_version"] != EXPECTED_FORMAT_VERSION:
        raise BundleError("MANIFEST_INVALID", "Unsupported bundle identity or format")
    if data["contract_baseline_id"] != EXPECTED_BASELINE_ID:
        raise BundleError("BASELINE_MISMATCH", "Bundle baseline does not match the frozen baseline")
    if not isinstance(data["platform_core_commit"], str) or not COMMIT_PATTERN.fullmatch(data["platform_core_commit"]):
        raise BundleError("MANIFEST_INVALID", "Manifest source SHA is invalid")
    if data["registry_path"] != "registry/mcp.yaml" or data["hash_algorithm"] != HASH_ALGORITHM or data["read_only"] is not True:
        raise BundleError("MANIFEST_INVALID", "Manifest contains unsupported values")
    if not isinstance(data["schema_paths"], list) or not isinstance(data["contract_paths"], list):
        raise BundleError("MANIFEST_INVALID", "Manifest path lists must be arrays")
    for relative in [*data["schema_paths"], *data["contract_paths"], data["registry_path"]]:
        if validate_bundle_path(relative):
            raise BundleError("UNSAFE_DESTINATION_PATH", f"Unsafe manifest path: {relative}")
    if not isinstance(data["content_root_hash"], str) or not SHA_PATTERN.fullmatch(data["content_root_hash"]):
        raise BundleError("MANIFEST_INVALID", "Manifest content root hash is invalid")
    return data


def _expected_payload_paths(manifest: dict[str, Any]) -> list[str]:
    paths = [manifest["registry_path"], *manifest["schema_paths"], *manifest["contract_paths"]]
    if len(paths) != len(set(paths)):
        raise BundleError("MANIFEST_INVALID", "Manifest contains duplicate payload paths")
    return paths


def _actual_payload_paths(bundle: Path) -> set[str]:
    actual: set[str] = set()
    for path in bundle.rglob("*"):
        if path.is_file():
            relative = path.relative_to(bundle).as_posix()
            if relative not in CONTROL_FILES:
                actual.add(relative)
    return actual


def _bundle_contract_validation(bundle: Path, manifest: dict[str, Any]) -> None:
    errors: list[str] = []
    registry_path = bundle / manifest["registry_path"]
    try:
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise BundleError("CONTRACT_VALIDATION_FAILED", "Bundled registry is invalid") from exc
    if not isinstance(registry, dict) or not isinstance(registry.get("export_graph"), dict):
        errors.append("Bundled registry is missing export_graph")

    for schema_path in manifest["schema_paths"]:
        path = bundle / schema_path
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid bundled schema: {schema_path}: {exc}")

    for contract_path in manifest["contract_paths"]:
        path = bundle / contract_path
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"Invalid bundled contract: {contract_path}: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"Bundled contract must be an object: {contract_path}")
            continue
        category = Path(contract_path).parts[1]
        if category == "identities":
            if "client_id" in data:
                errors += validate_mcp_client_identity_contract_file(path, bundle / "schemas/mcp-client-identity.schema.json")
            else:
                errors += validate_mcp_server_identity_contract_file(path, bundle / "schemas/mcp-server-identity.schema.json")
        elif category == "capabilities":
            errors += validate_instance_against_schema(data, bundle / "schemas/mcp-capability.schema.json", contract_path)
        elif category == "tools":
            errors += validate_mcp_tool_contract_file(path, bundle / "schemas/mcp-tool.schema.json", bundle)
        elif category == "resources":
            errors += validate_mcp_resource_contract_file(path, bundle / "schemas/mcp-resource.schema.json", bundle)
        elif category == "queries":
            errors += validate_mcp_query_contract_file(path, bundle / "schemas/mcp-query.schema.json", bundle)
        elif category == "manifests":
            errors += validate_mcp_server_manifest_contract_file(path, bundle / "schemas/mcp-server-manifest.schema.json")
            errors += _validate_mcp_manifest_data(bundle, data, contract_path)
        elif category == "consumptions":
            errors += _validate_mcp_consumption_data(bundle, data, contract_path)
        elif category == "discoveries":
            errors += _validate_mcp_discovery_data(bundle, data, contract_path)
        elif category == "policies":
            if "approval_class" in data:
                errors += _validate_mcp_approval_policy_data(bundle, data, contract_path)
            else:
                errors += _validate_mcp_authorization_policy_data(bundle, data, contract_path)
        else:
            errors.append(f"Unsupported bundled contract category: {category}")
    if errors:
        raise BundleError("CONTRACT_VALIDATION_FAILED", "\n".join(errors))


def verify_bundle(bundle: Path) -> dict[str, Any]:
    bundle = bundle.resolve()
    if not bundle.is_dir():
        raise BundleError("MISSING_BUNDLE_FILE", f"Bundle directory does not exist: {bundle}")
    manifest = _manifest(bundle)
    expected = set(_expected_payload_paths(manifest))
    actual = _actual_payload_paths(bundle)
    if expected != actual:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing:
            raise BundleError("MISSING_BUNDLE_FILE", ", ".join(missing))
        raise BundleError("UNEXPECTED_BUNDLE_FILE", ", ".join(unexpected))
    hashes = _parse_hashes(bundle)
    if set(hashes) != expected:
        raise BundleError("MANIFEST_INVALID", "Hash listing does not match payload set")
    for relative, expected_hash in hashes.items():
        actual_hash = _sha256(bundle / relative)
        if actual_hash != expected_hash:
            raise BundleError("HASH_MISMATCH", relative)
    if _root_hash(hashes) != manifest["content_root_hash"]:
        raise BundleError("ROOT_HASH_MISMATCH", "Bundle content root hash does not match")
    _bundle_contract_validation(bundle, manifest)
    return manifest


def _final_bundle_path(root: Path, output: Path | None) -> Path:
    parent = (output or (root / "dist/mcp-contract-bundle")).resolve()
    return parent / BUNDLE_ID / EXPECTED_BASELINE_ID


def export_bundle(root: Path, output: Path | None = None) -> Path:
    root = root.resolve()
    commit = _source_commit(root)
    errors = validate_repository(root)
    if errors:
        raise BundleError("CONTRACT_VALIDATION_FAILED", "\n".join(errors))
    graph_errors = validate_mcp_export_graph(root)
    if graph_errors:
        raise BundleError("INVALID_EXPORT_GRAPH", "\n".join(graph_errors))
    entries = load_mcp_export_graph(root)
    final = _final_bundle_path(root, output)
    if final.exists():
        raise BundleError("BUNDLE_ALREADY_EXISTS", str(final))
    final.parent.mkdir(parents=True, exist_ok=True)
    temporary = final.parent / f".{final.name}.tmp-{uuid.uuid4().hex}"
    try:
        temporary.mkdir()
        for entry in entries:
            errors = validate_source_path(root, entry.source_path) + validate_bundle_path(entry.bundle_path)
            if errors:
                raise BundleError("UNSAFE_SOURCE_PATH", "\n".join(errors))
            destination = temporary / entry.bundle_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / entry.source_path, destination)
        payload_paths = [entry.bundle_path for entry in entries]
        hashes = _payload_hashes(temporary, payload_paths)
        _write_json(temporary / MANIFEST_NAME, _manifest_payload(entries, commit, hashes))
        _write_hashes(temporary / HASHES_NAME, hashes)
        verify_bundle(temporary)
        os.replace(temporary, final)
    except BundleError:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    except (OSError, shutil.Error) as exc:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise BundleError("EXPORT_FAILED", str(exc)) from exc
    return final
