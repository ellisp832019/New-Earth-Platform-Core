from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from .governance import GovernanceRecord, governance_records, load_governance
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

GOV_ROLE_SET = {
    "PLATFORM",
    "ENGINEERING_INTELLIGENCE",
    "AI_SYSTEM",
    "SHELL",
    "OPERATIONS_UI",
    "PRODUCT",
    "LAB",
    "PROGRAMME",
    "ENGINE",
    "SERVICE",
    "TOOLING",
    "PROTOTYPE",
    "LEGACY",
    "REFERENCE",
}
GOV_CANONICAL_STATUS_SET = {
    "canonical",
    "canonical_specialist",
    "canonical_programme",
    "planned_extraction",
    "probable_extraction",
    "placeholder",
    "prototype",
    "legacy",
    "reference",
    "vendor_reference",
    "learning_reference",
}
GOV_LIFECYCLE_SET = {
    "active",
    "developing",
    "embedded",
    "planned",
    "probable",
    "placeholder",
    "prototype",
    "legacy",
    "reference",
    "vendor_reference",
    "learning_reference",
    "superseded",
}
GOV_INTERNAL_OWNER = "New Earth Advanced Technologies Ltd"
GOV_CANONICAL_STATUSES = {"canonical", "canonical_specialist", "canonical_programme"}
GOV_EXTRACTED_STATUSES = {"planned_extraction", "probable_extraction"}
GOV_REFERENCE_STATUSES = {"reference", "vendor_reference", "learning_reference"}
GOV_PLANNED_LIFECYCLE = {"planned", "probable", "placeholder"}
GOV_DEPENDENCY_CLASS_SET = {
    "platform_spine",
    "platform_service",
    "specialist_system",
    "product",
    "programme",
    "lab",
    "planned_extraction",
    "legacy",
    "prototype",
    "reference",
}
GOV_DEPENDENCY_STATUS_SET = {"active", "planned", "optional", "future", "not_required", "deferred"}
GOV_STATUS_LIFECYCLE: dict[str, set[str]] = {
    "canonical": {"active", "developing"},
    "canonical_specialist": {"active", "developing", "embedded"},
    "canonical_programme": {"active", "planned", "developing"},
    "planned_extraction": {"planned"},
    "probable_extraction": {"probable"},
    "placeholder": {"placeholder", "planned"},
    "prototype": {"prototype"},
    "legacy": {"legacy", "superseded"},
    "reference": {"reference"},
    "vendor_reference": {"reference", "vendor_reference"},
    "learning_reference": {"reference", "learning_reference"},
}
GOV_RELATIONSHIP_KINDS = {
    "authoritative",
    "registered_in",
    "consumes_declarations",
    "consumes_evidence",
    "observed_by",
    "explained_by",
    "operated_by",
    "bridge_target",
    "extracted_from",
    "superseded_by",
    "overlaps",
    "not_applicable",
}


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


def validate_governance_schema(governance_path: Path, schema_path: Path) -> list[str]:
    return validate_yaml_against_schema(governance_path, schema_path)


def _validate_governance_record(
    record: GovernanceRecord,
    registered_project_ids: set[str],
    all_record_ids: set[str],
    duplicate_canonical_names: set[str],
    canonical_repo_owners: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    if record.architecture_role not in GOV_ROLE_SET:
        errors.append(f"Invalid architecture role for {record.id}: {record.architecture_role}")
    if record.canonical_status not in GOV_CANONICAL_STATUS_SET:
        errors.append(f"Invalid canonical status for {record.id}: {record.canonical_status}")
    if record.lifecycle not in GOV_LIFECYCLE_SET:
        errors.append(f"Invalid lifecycle for {record.id}: {record.lifecycle}")
    if record.canonical_status in GOV_STATUS_LIFECYCLE and record.lifecycle not in GOV_STATUS_LIFECYCLE[record.canonical_status]:
        errors.append(
            f"Contradictory lifecycle for {record.id}: {record.canonical_status} cannot be {record.lifecycle}"
        )
    if record.dependency_class not in GOV_DEPENDENCY_CLASS_SET:
        errors.append(f"Invalid dependency class for {record.id}: {record.dependency_class}")
    if not record.ownership.system_owner.strip():
        errors.append(f"Missing owner for {record.id}")
    if record.record_type == "planned_extraction":
        if record.canonical_status not in GOV_EXTRACTED_STATUSES:
            errors.append(f"Planned extraction has invalid status for {record.id}: {record.canonical_status}")
        if record.repository.canonical_repo is not None:
            errors.append(f"Planned extraction must not declare canonical_repo for {record.id}")
        if record.lifecycle not in GOV_PLANNED_LIFECYCLE:
            errors.append(f"Planned extraction has invalid lifecycle for {record.id}: {record.lifecycle}")
    if record.lifecycle == "embedded":
        if record.repository.canonical_repo is not None:
            errors.append(f"Embedded system must not declare canonical_repo for {record.id}")
        if record.release_independence:
            errors.append(f"Embedded system should not be release independent: {record.id}")
    if record.canonical_status in GOV_REFERENCE_STATUSES and record.ownership.system_owner == GOV_INTERNAL_OWNER:
        errors.append(f"Reference or vendor record cannot use the internal owner for {record.id}")
    if record.id == "new-earth-local-ai-runtime":
        if record.architecture_role != "SERVICE":
            errors.append(f"Local AI Runtime must use SERVICE role: {record.id}")
        if record.canonical_status != "canonical":
            errors.append(f"Local AI Runtime must be canonical: {record.id}")
        if record.lifecycle != "active":
            errors.append(f"Local AI Runtime must be active: {record.id}")
        if record.dependency_class != "platform_service":
            errors.append(f"Local AI Runtime must be a platform service: {record.id}")
        if record.repository.canonical_repo != "New-Earth-Local-AI-Runtime":
            errors.append(f"Local AI Runtime must declare its canonical repository: {record.id}")
        if record.relationships.get("neos", None) and record.relationships["neos"].kind == "authoritative":
            errors.append("Local AI Runtime must not claim NEOS engineering authority")
        if record.relationships.get("gaia", None) and record.relationships["gaia"].kind == "authoritative":
            errors.append("Local AI Runtime must not claim GAIA employee authority")
    if record.canonical_status in GOV_CANONICAL_STATUSES and record.id not in registered_project_ids:
        errors.append(f"Canonical system must be registered in Platform Core: {record.id}")
    if (
        record.canonical_status in GOV_CANONICAL_STATUSES
        and record.lifecycle != "embedded"
        and not record.release_independence
    ):
        errors.append(f"Canonical system should be release independent: {record.id}")
    if (
        (record.canonical_status in GOV_EXTRACTED_STATUSES or record.canonical_status in GOV_REFERENCE_STATUSES)
        and record.release_independence
    ):
        errors.append(f"Non-canonical record should not be release independent: {record.id}")
    if record.canonical_status in {"placeholder", "prototype", "legacy"} and record.release_independence:
        errors.append(f"Placeholder, prototype, or legacy records should not be release independent: {record.id}")
    if (
        record.record_type == "system"
        and record.canonical_status in {"canonical", "canonical_programme"}
        and record.repository.canonical_repo is None
    ):
        errors.append(f"Canonical system must declare a canonical repository: {record.id}")
    if record.record_type == "system" and record.repository.canonical_repo is not None and record.canonical_status not in GOV_REFERENCE_STATUSES:
        repo = record.repository.canonical_repo
        owner = canonical_repo_owners.get(repo)
        if owner is None:
            canonical_repo_owners[repo] = record.id
        elif owner != record.id:
            errors.append(f"Canonical repository ownership is ambiguous for {repo}: {owner} and {record.id}")
    if record.canonical_name in duplicate_canonical_names:
        errors.append(f"Duplicate canonical name: {record.canonical_name}")
    if (
        record.repository.canonical_repo is not None
        and record.record_type == "system"
        and record.canonical_status not in GOV_REFERENCE_STATUSES
        and record.repository.canonical_repo in canonical_repo_owners
        and canonical_repo_owners[record.repository.canonical_repo] != record.id
    ):
        errors.append(
            f"Canonical repository ownership is ambiguous for {record.repository.canonical_repo}: "
            f"{canonical_repo_owners[record.repository.canonical_repo]} and {record.id}"
        )
    for key, relationship in record.relationships.items():
        if relationship.kind not in GOV_RELATIONSHIP_KINDS:
            errors.append(f"Invalid relationship kind for {record.id}.{key}: {relationship.kind}")
        if relationship.target is not None and relationship.target not in all_record_ids:
            errors.append(f"Unresolved relationship target for {record.id}.{key}: {relationship.target}")
    if record.record_type == "system" and record.canonical_status == "legacy" and not record.superseded_by:
        errors.append(f"Superseded system should declare a successor when known: {record.id}")
    return errors


def validate_governance(root: Path) -> list[str]:
    governance_path = root / "registry/governance.yaml"
    schema_path = root / "schemas/governance.schema.json"
    errors = validate_governance_schema(governance_path, schema_path)
    catalog = load_governance(governance_path)
    if not catalog.ownership_model:
        errors.append("Governance ownership model is required")

    registered_project_ids = {str(item["id"]) for item in load_yaml(root / "registry/projects.yaml").get("projects", [])}
    records = governance_records(governance_path)
    record_ids = [record.id for record in records]
    canonical_names = [record.canonical_name for record in records]
    if len(set(record_ids)) != len(record_ids):
        errors.append("Duplicate governance record IDs detected")
    duplicate_canonical_names = {name for name, count in Counter(canonical_names).items() if count > 1}
    if duplicate_canonical_names:
        errors.append("Duplicate governance canonical names detected")

    all_record_ids = set(record_ids)
    canonical_repo_owners: dict[str, str] = {}
    for record in records:
        errors += _validate_governance_record(
            record,
            registered_project_ids,
            all_record_ids,
            duplicate_canonical_names,
            canonical_repo_owners,
        )

    for record in records:
        if record.source_system is not None and record.source_system not in all_record_ids:
            errors.append(f"Unresolved source system for planned extraction {record.id}: {record.source_system}")
        if record.source_system is not None and record.record_type != "planned_extraction":
            errors.append(f"Only planned extractions may declare a source system: {record.id}")
    return errors


def validate_project_contract_file(contract_path: Path, schema_path: Path) -> list[str]:
    errors = validate_yaml_against_schema(contract_path, schema_path)
    if errors:
        return errors
    data = load_yaml(contract_path)
    version = str(data["repository"]["version"])
    if not validate_semver(version):
        errors.append(f"{contract_path}: repository.version is not valid SemVer: {version}")
    return errors


MCP_NAMESPACED_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*(?:_[a-z0-9]+)*)+$")
MCP_RESOURCE_IDENTIFIER_RE = re.compile(r"^mcp://[a-z][a-z0-9-]*(?:/[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?)+$")


def _validate_semver_fields(contract_path: Path, data: dict[str, Any], fields: list[str]) -> list[str]:
    errors: list[str] = []
    for field in fields:
        value = str(data[field])
        if not validate_semver(value):
            errors.append(f"{contract_path}: {field} is not valid SemVer: {value}")
    return errors


def validate_mcp_client_identity_contract_file(contract_path: Path, schema_path: Path) -> list[str]:
    errors = validate_yaml_against_schema(contract_path, schema_path)
    if errors:
        return errors
    data = load_yaml(contract_path)
    return errors + _validate_semver_fields(contract_path, data, ["client_version"])


def validate_mcp_server_identity_contract_file(contract_path: Path, schema_path: Path) -> list[str]:
    errors = validate_yaml_against_schema(contract_path, schema_path)
    if errors:
        return errors
    data = load_yaml(contract_path)
    return errors + _validate_semver_fields(
        contract_path,
        data,
        ["server_version", "capability_version", "schema_version"],
    )


def validate_mcp_tool_identifier(value: str) -> bool:
    return bool(MCP_NAMESPACED_IDENTIFIER_RE.fullmatch(value))


def validate_mcp_permission_identifier(value: str) -> bool:
    return bool(MCP_NAMESPACED_IDENTIFIER_RE.fullmatch(value))


def validate_mcp_resource_identifier(value: str) -> bool:
    return bool(MCP_RESOURCE_IDENTIFIER_RE.fullmatch(value))


def validate_mcp_identity_contracts(root: Path) -> list[str]:
    errors: list[str] = []
    client_contract = root / "examples/mcp/mcp-client-identity.yaml"
    server_contract = root / "examples/mcp/mcp-server-identity.yaml"
    client_schema = root / "schemas/mcp-client-identity.schema.json"
    server_schema = root / "schemas/mcp-server-identity.schema.json"
    if client_contract.exists():
        errors += validate_mcp_client_identity_contract_file(client_contract, client_schema)
    else:
        errors.append(f"Missing MCP client identity contract: {client_contract}")
    if server_contract.exists():
        errors += validate_mcp_server_identity_contract_file(server_contract, server_schema)
    else:
        errors.append(f"Missing MCP server identity contract: {server_contract}")
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
        status = edge.get("status")
        if status is not None and str(status) not in GOV_DEPENDENCY_STATUS_SET:
            errors.append(f"Invalid dependency status for {source}->{target}: {status}")
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
        version = interface.get("version")
        if version is not None and not validate_semver(str(version)):
            errors.append(f"Malformed interface version for {iid}: {version}")
        consumers = interface.get("consumers", [])
        if consumers is not None:
            for consumer in consumers:
                consumer_id = str(consumer)
                if consumer_id not in project_ids:
                    errors.append(f"Unknown interface consumer for {iid}: {consumer_id}")

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
