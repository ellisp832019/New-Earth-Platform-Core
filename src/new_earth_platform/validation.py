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


def _render_schema_errors(source: Any, errors: list[Any]) -> list[str]:
    rendered: list[str] = []
    for error in sorted(errors, key=lambda e: list(e.absolute_path)):
        location = ".".join(str(p) for p in error.absolute_path) or "<root>"
        rendered.append(f"{source}: {location}: {error.message}")
    return rendered


def validate_instance_against_schema(instance: Any, schema_path: Path, source: Any) -> list[str]:
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)
    return _render_schema_errors(source, list(validator.iter_errors(instance)))


def validate_yaml_against_schema(yaml_path: Path, schema_path: Path) -> list[str]:
    instance = load_yaml(yaml_path)
    return validate_instance_against_schema(instance, schema_path, yaml_path)


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
MCP_RESOURCE_URI_RE = re.compile(r"^mcp://[a-z][a-z0-9-]*(?:/[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?)+$")
MCP_RESOURCE_IDENTIFIER_RE = re.compile(
    r"^(?:[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*(?:_[a-z0-9]+)*)+|mcp://[a-z][a-z0-9-]*(?:/[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?)+)$"
)
MCP_SCHEMA_REF_RE = re.compile(r"^schemas/[a-z0-9][a-z0-9._/-]*\.schema\.json$")
MCP_STATUS_SET = {"planned", "declared", "active", "deprecated"}
MCP_MODE_SET = {"read_only"}
MCP_TIMEOUT_CLASS_SET = {"short", "medium", "long"}
MCP_OPERATION_CLASS_SET = {
    "health.read",
    "status.read",
    "registry.read",
    "project.read",
    "repository.read",
    "engineering.read",
    "dependency.read",
    "decision.read",
    "architecture.read",
    "evidence.read",
    "knowledge.read",
    "diagnostic.read",
    "report.read",
    "search.read",
}
MCP_RESOURCE_TYPE_SET = {
    "health",
    "status",
    "project",
    "repository",
    "engineering",
    "dependency",
    "decision",
    "architecture",
    "evidence",
    "knowledge",
    "diagnostic",
    "report",
    "registry",
}
MCP_QUERY_OPERATION_SET = {
    "get",
    "list",
    "search",
    "lookup",
    "summary",
    "status",
    "health",
    "dependencies",
    "decisions",
    "evidence",
    "diagnostics",
}
MCP_FILTER_OPERATOR_SET = {"eq", "neq", "contains", "prefix", "in"}
MCP_SORT_DIRECTION_SET = {"asc", "desc"}
MCP_MANIFEST_EXPOSURE_MODE_SET = {"declared", "disabled", "planned"}
MCP_DISCOVERY_MODE_SET = {"static", "local_registry", "stdio_command", "localhost_endpoint"}
MCP_LOCAL_ENDPOINT_RE = re.compile(r"^https?://(?:localhost|127\.0\.0\.1)(?::[0-9]{1,5})?(?:/.*)?$")
MCP_POLICY_EFFECT_SET = {"allow", "deny", "approval_required"}
MCP_APPROVAL_CLASS_SET = {"none", "single_approval", "elevated_approval", "explicit_founder_approval"}
MCP_EXPIRY_MODE_SET = {"single_use", "session", "duration"}


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


def validate_mcp_server_manifest_contract_file(contract_path: Path, schema_path: Path) -> list[str]:
    errors = validate_yaml_against_schema(contract_path, schema_path)
    if errors:
        return errors
    data = load_yaml(contract_path)
    return _validate_semver_fields(contract_path, data, ["version", "manifest_version"])


def validate_mcp_server_discovery_contract_file(contract_path: Path, schema_path: Path) -> list[str]:
    errors = validate_yaml_against_schema(contract_path, schema_path)
    if errors:
        return errors
    data = load_yaml(contract_path)
    return _validate_mcp_discovery_data(contract_path.parents[2], data, str(contract_path))


def validate_mcp_tool_identifier(value: str) -> bool:
    return bool(MCP_NAMESPACED_IDENTIFIER_RE.fullmatch(value))


def validate_mcp_permission_identifier(value: str) -> bool:
    return bool(MCP_NAMESPACED_IDENTIFIER_RE.fullmatch(value))


def validate_mcp_resource_identifier(value: str) -> bool:
    return bool(MCP_RESOURCE_IDENTIFIER_RE.fullmatch(value))


def _validate_mcp_schema_ref(root: Path, ref: Any, source: str, field: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(ref, str) or not ref.strip():
        errors.append(f"{source}: {field} must be a non-empty schema reference")
        return errors
    if not MCP_SCHEMA_REF_RE.fullmatch(ref):
        errors.append(f"{source}: {field} is not a supported MCP schema reference: {ref}")
        return errors
    schema_path = (root / ref).resolve()
    if root.resolve() not in schema_path.parents and schema_path != root.resolve():
        errors.append(f"{source}: {field} escapes repository root: {ref}")
        return errors
    if not schema_path.exists():
        errors.append(f"{source}: missing schema reference for {field}: {ref}")
        return errors
    try:
        _load_json(schema_path)
    except (json.JSONDecodeError, TypeError) as exc:
        errors.append(f"{source}: invalid JSON schema for {field}: {ref} ({exc})")
    return errors


def _validate_mcp_capability_data(root: Path, capability: dict[str, Any], source: str) -> list[str]:
    schema_path = root / "schemas/mcp-capability.schema.json"
    errors = validate_instance_against_schema(capability, schema_path, source)
    return errors


def _validate_mcp_tool_data(root: Path, tool: dict[str, Any], source: str) -> list[str]:
    schema_path = root / "schemas/mcp-tool.schema.json"
    errors = validate_instance_against_schema(tool, schema_path, source)
    if errors:
        return errors
    errors = []
    errors += _validate_mcp_schema_ref(root, tool.get("input_schema_ref"), source, "input_schema_ref")
    errors += _validate_mcp_schema_ref(root, tool.get("output_schema_ref"), source, "output_schema_ref")
    operation = str(tool["operation"])
    if operation not in MCP_OPERATION_CLASS_SET:
        errors.append(f"{source}: unsupported MCP operation class: {operation}")
    return errors


def _validate_mcp_resource_data(root: Path, resource: dict[str, Any], source: str) -> list[str]:
    schema_path = root / "schemas/mcp-resource.schema.json"
    errors = validate_instance_against_schema(resource, schema_path, source)
    if errors:
        return errors
    errors = []
    errors += _validate_mcp_schema_ref(root, resource.get("schema_ref"), source, "schema_ref")
    return errors


def _validate_mcp_query_data(root: Path, query: dict[str, Any], source: str) -> list[str]:
    schema_path = root / "schemas/mcp-query.schema.json"
    errors = validate_instance_against_schema(query, schema_path, source)
    if errors:
        return errors
    errors = []
    errors += _validate_mcp_schema_ref(root, query.get("parameter_schema_ref"), source, "parameter_schema_ref")
    errors += _validate_mcp_schema_ref(root, query.get("result_schema_ref"), source, "result_schema_ref")
    operation = str(query["operation"])
    if operation not in MCP_QUERY_OPERATION_SET:
        errors.append(f"{source}: unsupported MCP query operation: {operation}")

    pagination = query.get("pagination")
    if pagination is not None:
        if not isinstance(pagination, dict):
            errors.append(f"{source}: pagination must be an object")
        else:
            enabled = pagination.get("enabled")
            default_page_size = pagination.get("default_page_size")
            max_page_size = pagination.get("max_page_size")
            if not isinstance(enabled, bool):
                errors.append(f"{source}: pagination.enabled must be a boolean")
            if not isinstance(default_page_size, int) or default_page_size < 1:
                errors.append(f"{source}: pagination.default_page_size must be a positive integer")
            if not isinstance(max_page_size, int) or max_page_size < 1:
                errors.append(f"{source}: pagination.max_page_size must be a positive integer")
            if isinstance(default_page_size, int) and isinstance(max_page_size, int) and max_page_size < default_page_size:
                errors.append(f"{source}: pagination.max_page_size must be greater than or equal to default_page_size")

    filtering = query.get("filtering")
    if filtering is not None:
        if not isinstance(filtering, dict):
            errors.append(f"{source}: filtering must be an object")
        else:
            operators = filtering.get("operators")
            if not isinstance(operators, list) or not operators:
                errors.append(f"{source}: filtering.operators must be a non-empty list")
            else:
                for operator in operators:
                    if not isinstance(operator, str):
                        errors.append(f"{source}: filtering.operators must contain strings")
                    elif operator not in MCP_FILTER_OPERATOR_SET:
                        errors.append(f"{source}: unsupported MCP filter operator: {operator}")

    sorting = query.get("sorting")
    if sorting is not None:
        if not isinstance(sorting, dict):
            errors.append(f"{source}: sorting must be an object")
        else:
            directions = sorting.get("directions")
            if not isinstance(directions, list) or not directions:
                errors.append(f"{source}: sorting.directions must be a non-empty list")
            else:
                for direction in directions:
                    if not isinstance(direction, str):
                        errors.append(f"{source}: sorting.directions must contain strings")
                    elif direction not in MCP_SORT_DIRECTION_SET:
                        errors.append(f"{source}: unsupported MCP sort direction: {direction}")
    return errors


def _validate_mcp_manifest_data(root: Path, manifest: dict[str, Any], source: str) -> list[str]:
    schema_path = root / "schemas/mcp-server-manifest.schema.json"
    errors = validate_instance_against_schema(manifest, schema_path, source)
    if errors:
        return errors
    errors = _validate_semver_fields(Path(source), manifest, ["version", "manifest_version"])
    if str(manifest["exposure_mode"]) not in MCP_MANIFEST_EXPOSURE_MODE_SET:
        errors.append(f"{source}: unsupported MCP manifest exposure mode: {manifest['exposure_mode']}")
    return errors


def _validate_mcp_discovery_data(root: Path, discovery: dict[str, Any], source: str) -> list[str]:
    schema_path = root / "schemas/mcp-server-discovery.schema.json"
    errors = validate_instance_against_schema(discovery, schema_path, source)
    if errors:
        return errors
    errors = _validate_semver_fields(Path(source), discovery, ["version"])
    mode = str(discovery["discovery_mode"])
    if mode not in MCP_DISCOVERY_MODE_SET:
        errors.append(f"{source}: unsupported MCP discovery mode: {mode}")
    endpoint_hint = discovery.get("endpoint_hint")
    if mode == "localhost_endpoint":
        if not isinstance(endpoint_hint, str) or not MCP_LOCAL_ENDPOINT_RE.fullmatch(endpoint_hint):
            errors.append(f"{source}: endpoint_hint must use localhost or 127.0.0.1")
    elif endpoint_hint is not None:
        errors.append(f"{source}: endpoint_hint is only valid for localhost_endpoint discovery")
    if mode == "stdio_command" and not isinstance(discovery.get("command_id"), str):
        errors.append(f"{source}: stdio_command discovery requires a controlled command_id")
    return errors


def _validate_mcp_consumption_data(root: Path, consumption: dict[str, Any], source: str) -> list[str]:
    schema_path = root / "schemas/mcp-client-consumption.schema.json"
    errors = validate_instance_against_schema(consumption, schema_path, source)
    if errors:
        return errors
    errors = _validate_semver_fields(Path(source), consumption, ["version"])
    compatibility = consumption["compatibility"]
    errors += _validate_semver_fields(
        Path(source),
        compatibility,
        ["minimum_server_version", "manifest_version"],
    )
    for capability_id, version in compatibility["capability_versions"].items():
        if not validate_semver(str(version)):
            errors.append(f"{source}: capability_versions.{capability_id} is not valid SemVer: {version}")
    return errors


def _validate_mcp_authorization_policy_data(root: Path, policy: dict[str, Any], source: str) -> list[str]:
    schema_path = root / "schemas/mcp-authorization-policy.schema.json"
    errors = validate_instance_against_schema(policy, schema_path, source)
    if errors:
        return errors
    errors = _validate_semver_fields(Path(source), policy, ["version"])
    if str(policy["effect"]) not in MCP_POLICY_EFFECT_SET:
        errors.append(f"{source}: unsupported MCP policy effect: {policy['effect']}")
    target_count = sum(len(policy[field]) for field in ["server_ids", "capability_ids", "tool_ids", "resource_ids", "query_ids"])
    if target_count == 0:
        errors.append(f"{source}: authorization policy must declare at least one target")
    return errors


def _validate_mcp_approval_policy_data(root: Path, policy: dict[str, Any], source: str) -> list[str]:
    schema_path = root / "schemas/mcp-approval-policy.schema.json"
    errors = validate_instance_against_schema(policy, schema_path, source)
    if errors:
        return errors
    errors = _validate_semver_fields(Path(source), policy, ["version"])
    if str(policy["approval_class"]) not in MCP_APPROVAL_CLASS_SET:
        errors.append(f"{source}: unsupported MCP approval class: {policy['approval_class']}")
    expiry = policy["expiry"]
    if str(expiry["mode"]) not in MCP_EXPIRY_MODE_SET:
        errors.append(f"{source}: unsupported MCP expiry mode: {expiry['mode']}")
    if expiry["mode"] == "duration" and "duration_seconds" not in expiry:
        errors.append(f"{source}: duration expiry requires duration_seconds")
    return errors


def validate_mcp_capability_contract_file(contract_path: Path, schema_path: Path, _root: Path) -> list[str]:
    return validate_yaml_against_schema(contract_path, schema_path)


def validate_mcp_tool_contract_file(contract_path: Path, schema_path: Path, root: Path) -> list[str]:
    errors = validate_yaml_against_schema(contract_path, schema_path)
    if errors:
        return errors
    data = load_yaml(contract_path)
    errors += _validate_mcp_schema_ref(root, data.get("input_schema_ref"), str(contract_path), "input_schema_ref")
    errors += _validate_mcp_schema_ref(root, data.get("output_schema_ref"), str(contract_path), "output_schema_ref")
    operation = str(data["operation"])
    if operation not in MCP_OPERATION_CLASS_SET:
        errors.append(f"{contract_path}: unsupported MCP operation class: {operation}")
    return errors


def validate_mcp_resource_contract_file(contract_path: Path, schema_path: Path, root: Path) -> list[str]:
    errors = validate_yaml_against_schema(contract_path, schema_path)
    if errors:
        return errors
    data = load_yaml(contract_path)
    errors += _validate_mcp_schema_ref(root, data.get("schema_ref"), str(contract_path), "schema_ref")
    return errors


def validate_mcp_query_contract_file(contract_path: Path, schema_path: Path, root: Path) -> list[str]:
    errors = validate_yaml_against_schema(contract_path, schema_path)
    if errors:
        return errors
    data = load_yaml(contract_path)
    errors += _validate_mcp_schema_ref(root, data.get("parameter_schema_ref"), str(contract_path), "parameter_schema_ref")
    errors += _validate_mcp_schema_ref(root, data.get("result_schema_ref"), str(contract_path), "result_schema_ref")
    operation = str(data["operation"])
    if operation not in MCP_QUERY_OPERATION_SET:
        errors.append(f"{contract_path}: unsupported MCP query operation: {operation}")
    return errors


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


def validate_mcp_contracts(root: Path) -> list[str]:
    registry_path = root / "registry/mcp.yaml"
    if not registry_path.exists():
        return [f"Missing MCP registry: {registry_path}"]

    data = load_yaml(registry_path)
    client_identity_path = root / "examples/mcp/mcp-client-identity.yaml"
    servers = data.get("servers")
    manifests = data.get("manifests")
    consumptions = data.get("consumptions")
    discoveries = data.get("discoveries")
    authorization_policies = data.get("authorization_policies")
    approval_policies = data.get("approval_policies")
    capabilities = data.get("capabilities")
    resources = data.get("resources")
    queries = data.get("queries")
    tools = data.get("tools")
    errors: list[str] = []

    if not isinstance(servers, list):
        errors.append(f"{registry_path}: servers must be a list")
        servers = []
    if not isinstance(manifests, list):
        errors.append(f"{registry_path}: manifests must be a list")
        manifests = []
    if not isinstance(consumptions, list):
        errors.append(f"{registry_path}: consumptions must be a list")
        consumptions = []
    if not isinstance(discoveries, list):
        errors.append(f"{registry_path}: discoveries must be a list")
        discoveries = []
    if not isinstance(authorization_policies, list):
        errors.append(f"{registry_path}: authorization_policies must be a list")
        authorization_policies = []
    if not isinstance(approval_policies, list):
        errors.append(f"{registry_path}: approval_policies must be a list")
        approval_policies = []
    if not isinstance(capabilities, list):
        errors.append(f"{registry_path}: capabilities must be a list")
        capabilities = []
    if not isinstance(resources, list):
        errors.append(f"{registry_path}: resources must be a list")
        resources = []
    if not isinstance(queries, list):
        errors.append(f"{registry_path}: queries must be a list")
        queries = []
    if not isinstance(tools, list):
        errors.append(f"{registry_path}: tools must be a list")
        tools = []

    server_map: dict[str, dict[str, Any]] = {}
    manifest_map: dict[str, dict[str, Any]] = {}
    consumption_map: dict[str, dict[str, Any]] = {}
    discovery_map: dict[str, dict[str, Any]] = {}
    authorization_policy_map: dict[str, dict[str, Any]] = {}
    approval_policy_map: dict[str, dict[str, Any]] = {}
    capability_map: dict[str, dict[str, Any]] = {}
    resource_map: dict[str, dict[str, Any]] = {}
    query_map: dict[str, dict[str, Any]] = {}
    tool_map: dict[str, dict[str, Any]] = {}

    client_map: dict[str, dict[str, Any]] = {}
    if client_identity_path.exists():
        client_data = load_yaml(client_identity_path)
        if isinstance(client_data, dict) and isinstance(client_data.get("client_id"), str):
            client_map[str(client_data["client_id"])] = client_data
    system_ids = {str(item["id"]) for item in load_yaml(root / "registry/projects.yaml").get("projects", [])}

    for index, server in enumerate(servers):
        if not isinstance(server, dict):
            errors.append(f"{registry_path}: servers[{index}] must be an object")
            continue
        server_id = str(server.get("server_id", ""))
        if server_id in server_map:
            errors.append(f"Duplicate server id: {server_id}")
        else:
            server_map[server_id] = server
        errors += validate_instance_against_schema(server, root / "schemas/mcp-server-identity.schema.json", f"{registry_path}: servers[{index}]")

    for index, manifest in enumerate(manifests):
        if not isinstance(manifest, dict):
            errors.append(f"{registry_path}: manifests[{index}] must be an object")
            continue
        manifest_id = str(manifest.get("id", ""))
        if manifest_id in manifest_map:
            errors.append(f"Duplicate manifest id: {manifest_id}")
        else:
            manifest_map[manifest_id] = manifest
        errors += _validate_mcp_manifest_data(root, manifest, f"{registry_path}: manifests[{index}]")

    for index, discovery in enumerate(discoveries):
        if not isinstance(discovery, dict):
            errors.append(f"{registry_path}: discoveries[{index}] must be an object")
            continue
        discovery_id = str(discovery.get("id", ""))
        if discovery_id in discovery_map:
            errors.append(f"Duplicate discovery id: {discovery_id}")
        else:
            discovery_map[discovery_id] = discovery
        errors += _validate_mcp_discovery_data(root, discovery, f"{registry_path}: discoveries[{index}]")

    for index, consumption in enumerate(consumptions):
        if not isinstance(consumption, dict):
            errors.append(f"{registry_path}: consumptions[{index}] must be an object")
            continue
        consumption_id = str(consumption.get("id", ""))
        if consumption_id in consumption_map:
            errors.append(f"Duplicate consumption id: {consumption_id}")
        else:
            consumption_map[consumption_id] = consumption
        errors += _validate_mcp_consumption_data(
            root,
            consumption,
            f"{registry_path}: consumptions[{index}]",
        )

    for index, policy in enumerate(authorization_policies):
        if not isinstance(policy, dict):
            errors.append(f"{registry_path}: authorization_policies[{index}] must be an object")
            continue
        policy_id = str(policy.get("id", ""))
        if policy_id in authorization_policy_map:
            errors.append(f"Duplicate authorization policy id: {policy_id}")
        else:
            authorization_policy_map[policy_id] = policy
        errors += _validate_mcp_authorization_policy_data(root, policy, f"{registry_path}: authorization_policies[{index}]")

    for index, policy in enumerate(approval_policies):
        if not isinstance(policy, dict):
            errors.append(f"{registry_path}: approval_policies[{index}] must be an object")
            continue
        policy_id = str(policy.get("id", ""))
        if policy_id in approval_policy_map:
            errors.append(f"Duplicate approval policy id: {policy_id}")
        else:
            approval_policy_map[policy_id] = policy
        errors += _validate_mcp_approval_policy_data(root, policy, f"{registry_path}: approval_policies[{index}]")

    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            errors.append(f"{registry_path}: capabilities[{index}] must be an object")
            continue
        cap_id = str(capability.get("id", ""))
        if cap_id in capability_map:
            errors.append(f"Duplicate capability id: {cap_id}")
        else:
            capability_map[cap_id] = capability
        errors += _validate_mcp_capability_data(root, capability, f"{registry_path}: capabilities[{index}]")

    for index, resource in enumerate(resources):
        if not isinstance(resource, dict):
            errors.append(f"{registry_path}: resources[{index}] must be an object")
            continue
        resource_id = str(resource.get("id", ""))
        if resource_id in resource_map:
            errors.append(f"Duplicate resource id: {resource_id}")
        else:
            resource_map[resource_id] = resource
        errors += _validate_mcp_resource_data(root, resource, f"{registry_path}: resources[{index}]")

    for index, query in enumerate(queries):
        if not isinstance(query, dict):
            errors.append(f"{registry_path}: queries[{index}] must be an object")
            continue
        query_id = str(query.get("id", ""))
        if query_id in query_map:
            errors.append(f"Duplicate query id: {query_id}")
        else:
            query_map[query_id] = query
        errors += _validate_mcp_query_data(root, query, f"{registry_path}: queries[{index}]")

    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            errors.append(f"{registry_path}: tools[{index}] must be an object")
            continue
        tool_id = str(tool.get("id", ""))
        if tool_id in tool_map:
            errors.append(f"Duplicate tool id: {tool_id}")
        else:
            tool_map[tool_id] = tool
        errors += _validate_mcp_tool_data(root, tool, f"{registry_path}: tools[{index}]")

    for server_id, server in server_map.items():
        declared_tool_ids = [str(tool_id) for tool_id in server.get("declared_tools", [])]
        declared_resource_ids = [str(resource_id) for resource_id in server.get("declared_resources", [])]
        for tool_id in declared_tool_ids:
            if tool_id not in tool_map:
                errors.append(f"Orphan server tool reference: {server_id} -> {tool_id}")
                continue
            tool = tool_map[tool_id]
            if str(tool.get("server_id", "")) != server_id:
                errors.append(f"Server mismatch for tool {tool_id}: {tool.get('server_id')} != {server_id}")
            if str(tool.get("owner_system_id", "")) != str(server.get("owner_system_id", "")):
                errors.append(
                    f"Owner mismatch for tool {tool_id}: {tool.get('owner_system_id')} != {server.get('owner_system_id')}"
                )
        for resource_id in declared_resource_ids:
            if resource_id not in resource_map:
                errors.append(f"Orphan server resource reference: {server_id} -> {resource_id}")
                continue
            resource = resource_map[resource_id]
            if str(resource.get("server_id", "")) != server_id:
                errors.append(f"Server mismatch for resource {resource_id}: {resource.get('server_id')} != {server_id}")
            if str(resource.get("owner_system_id", "")) != str(server.get("owner_system_id", "")):
                errors.append(
                    f"Owner mismatch for resource {resource_id}: {resource.get('owner_system_id')} != {server.get('owner_system_id')}"
                )

    declared_tool_references: Counter[str] = Counter()
    for capability in capability_map.values():
        cap_id = str(capability["id"])
        tool_id_values = [str(tool_id) for tool_id in capability.get("tool_ids", [])]
        for tool_id in tool_id_values:
            declared_tool_references[tool_id] += 1
            if tool_id not in tool_map:
                errors.append(f"Orphan capability reference: {cap_id} -> {tool_id}")
                continue
            tool = tool_map[tool_id]
            tool_capability_id = str(tool.get("capability_id", ""))
            if tool_capability_id != cap_id:
                errors.append(f"Tool capability mismatch: {tool_id} -> {tool_capability_id} (expected {cap_id})")
            if str(tool.get("server_id", "")) != str(capability.get("server_id", "")):
                errors.append(f"Server mismatch for tool {tool_id}: {tool.get('server_id')} != {capability.get('server_id')}")
            if str(tool.get("owner_system_id", "")) != str(capability.get("owner_system_id", "")):
                errors.append(
                    f"Owner mismatch for tool {tool_id}: {tool.get('owner_system_id')} != {capability.get('owner_system_id')}"
                )

    for tool_id, count in declared_tool_references.items():
        if count > 1:
            errors.append(f"Tool referenced by multiple capabilities: {tool_id}")

    for resource_id, resource in resource_map.items():
        capability_id = str(resource.get("capability_id", ""))
        server_id = str(resource.get("server_id", ""))
        if capability_id not in capability_map:
            errors.append(f"Orphan resource reference: {resource_id} -> {capability_id}")
            continue
        capability = capability_map[capability_id]
        if server_id not in server_map:
            errors.append(f"Orphan resource server reference: {resource_id} -> {server_id}")
            continue
        server = server_map[server_id]
        if str(resource.get("owner_system_id", "")) != str(capability.get("owner_system_id", "")):
            errors.append(
                f"Owner mismatch for resource {resource_id}: {resource.get('owner_system_id')} != {capability.get('owner_system_id')}"
            )
        if str(resource.get("owner_system_id", "")) != str(server.get("owner_system_id", "")):
            errors.append(
                f"Owner mismatch for resource {resource_id}: {resource.get('owner_system_id')} != {server.get('owner_system_id')}"
            )
        if str(resource.get("server_id", "")) != str(capability.get("server_id", "")):
            errors.append(
                f"Server mismatch for resource {resource_id}: {resource.get('server_id')} != {capability.get('server_id')}"
            )
        for query_id in [str(query_id) for query_id in resource.get("query_ids", [])]:
            if query_id not in query_map:
                errors.append(f"Orphan resource query reference: {resource_id} -> {query_id}")

    for query_id, query in query_map.items():
        resource_id = str(query.get("resource_id", ""))
        capability_id = str(query.get("capability_id", ""))
        server_id = str(query.get("server_id", ""))
        if resource_id not in resource_map:
            errors.append(f"Orphan query resource reference: {query_id} -> {resource_id}")
            continue
        resource = resource_map[resource_id]
        if capability_id not in capability_map:
            errors.append(f"Orphan query capability reference: {query_id} -> {capability_id}")
            continue
        capability = capability_map[capability_id]
        if server_id not in server_map:
            errors.append(f"Orphan query server reference: {query_id} -> {server_id}")
            continue
        server = server_map[server_id]
        if str(query.get("owner_system_id", "")) != str(resource.get("owner_system_id", "")):
            errors.append(
                f"Owner mismatch for query {query_id}: {query.get('owner_system_id')} != {resource.get('owner_system_id')}"
            )
        if str(query.get("owner_system_id", "")) != str(capability.get("owner_system_id", "")):
            errors.append(
                f"Owner mismatch for query {query_id}: {query.get('owner_system_id')} != {capability.get('owner_system_id')}"
            )
        if str(query.get("owner_system_id", "")) != str(server.get("owner_system_id", "")):
            errors.append(
                f"Owner mismatch for query {query_id}: {query.get('owner_system_id')} != {server.get('owner_system_id')}"
            )
        if str(query.get("server_id", "")) != str(resource.get("server_id", "")):
            errors.append(
                f"Server mismatch for query {query_id}: {query.get('server_id')} != {resource.get('server_id')}"
            )
        if str(query.get("capability_id", "")) != str(resource.get("capability_id", "")):
            errors.append(
                f"Capability mismatch for query {query_id}: {query.get('capability_id')} != {resource.get('capability_id')}"
            )
        if query_id not in resource.get("query_ids", []):
            errors.append(f"Resource query_ids missing reverse reference: {resource_id} -> {query_id}")

    for tool_id, tool in tool_map.items():
        capability_id = str(tool.get("capability_id", ""))
        if capability_id not in capability_map:
            errors.append(f"Orphan tool reference: {tool_id} -> {capability_id}")
            continue
        capability = capability_map[capability_id]
        if str(tool.get("server_id", "")) != str(capability.get("server_id", "")):
            errors.append(f"Server mismatch for tool {tool_id}: {tool.get('server_id')} != {capability.get('server_id')}")
        if str(tool.get("owner_system_id", "")) != str(capability.get("owner_system_id", "")):
            errors.append(
                f"Owner mismatch for tool {tool_id}: {tool.get('owner_system_id')} != {capability.get('owner_system_id')}"
            )
        if tool_id not in capability.get("tool_ids", []):
            errors.append(f"Capability tool_ids missing reverse reference: {capability_id} -> {tool_id}")
        for query_id in [str(query_id) for query_id in tool.get("query_ids", [])]:
            if query_id not in query_map:
                errors.append(f"Orphan tool query reference: {tool_id} -> {query_id}")
                continue
            query = query_map[query_id]
            if str(query.get("server_id", "")) != str(tool.get("server_id", "")):
                errors.append(f"Server mismatch for query {query_id}: {query.get('server_id')} != {tool.get('server_id')}")
            if str(query.get("owner_system_id", "")) != str(tool.get("owner_system_id", "")):
                errors.append(
                    f"Owner mismatch for query {query_id}: {query.get('owner_system_id')} != {tool.get('owner_system_id')}"
                )
            if str(query.get("capability_id", "")) != capability_id:
                errors.append(
                    f"Capability mismatch for query {query_id}: {query.get('capability_id')} != {capability_id}"
                )

    for manifest_id, manifest in manifest_map.items():
        server_id = str(manifest.get("server_id", ""))
        owner_system_id = str(manifest.get("owner_system_id", ""))
        if server_id not in server_map:
            errors.append(f"Orphan manifest server reference: {manifest_id} -> {server_id}")
            continue
        server = server_map[server_id]
        if owner_system_id != str(server.get("owner_system_id", "")):
            errors.append(f"Owner mismatch for manifest {manifest_id}: {owner_system_id} != {server.get('owner_system_id')}")
        if str(manifest.get("transport", "")) != str(server.get("transport", "")):
            errors.append(f"Transport mismatch for manifest {manifest_id}: {manifest.get('transport')} != {server.get('transport')}")
        if str(manifest.get("bind_scope", "")) != str(server.get("bind_scope", "")):
            errors.append(f"Bind scope mismatch for manifest {manifest_id}: {manifest.get('bind_scope')} != {server.get('bind_scope')}")

        exposed_capability_ids = {str(value) for value in manifest.get("capability_ids", [])}
        exposed_tool_ids = {str(value) for value in manifest.get("tool_ids", [])}
        exposed_resource_ids = {str(value) for value in manifest.get("resource_ids", [])}
        exposed_query_ids = {str(value) for value in manifest.get("query_ids", [])}

        for capability_id in exposed_capability_ids:
            if capability_id not in capability_map:
                errors.append(f"Orphan manifest capability reference: {manifest_id} -> {capability_id}")
                continue
            capability = capability_map[capability_id]
            if str(capability.get("server_id", "")) != server_id:
                errors.append(f"Server mismatch for manifest capability {capability_id}: {capability.get('server_id')} != {server_id}")
            if str(capability.get("owner_system_id", "")) != owner_system_id:
                errors.append(f"Owner mismatch for manifest capability {capability_id}: {capability.get('owner_system_id')} != {owner_system_id}")
            if capability.get("read_only") is not True or capability.get("mode") != "read_only":
                errors.append(f"Unsafe capability exposure: {manifest_id} -> {capability_id}")

        for tool_id in exposed_tool_ids:
            if tool_id not in tool_map:
                errors.append(f"Orphan manifest tool reference: {manifest_id} -> {tool_id}")
                continue
            tool = tool_map[tool_id]
            if str(tool.get("server_id", "")) != server_id:
                errors.append(f"Server mismatch for manifest tool {tool_id}: {tool.get('server_id')} != {server_id}")
            if str(tool.get("owner_system_id", "")) != owner_system_id:
                errors.append(f"Owner mismatch for manifest tool {tool_id}: {tool.get('owner_system_id')} != {owner_system_id}")
            if str(tool.get("capability_id", "")) not in exposed_capability_ids:
                errors.append(f"Tool exposed without capability: {manifest_id} -> {tool_id}")
            if tool.get("read_only") is not True or tool.get("side_effects") is not False:
                errors.append(f"Unsafe tool exposure: {manifest_id} -> {tool_id}")

        for resource_id in exposed_resource_ids:
            if resource_id not in resource_map:
                errors.append(f"Orphan manifest resource reference: {manifest_id} -> {resource_id}")
                continue
            resource = resource_map[resource_id]
            if str(resource.get("server_id", "")) != server_id:
                errors.append(f"Server mismatch for manifest resource {resource_id}: {resource.get('server_id')} != {server_id}")
            if str(resource.get("owner_system_id", "")) != owner_system_id:
                errors.append(f"Owner mismatch for manifest resource {resource_id}: {resource.get('owner_system_id')} != {owner_system_id}")
            if str(resource.get("capability_id", "")) not in exposed_capability_ids:
                errors.append(f"Resource exposed without capability: {manifest_id} -> {resource_id}")
            if resource.get("read_only") is not True:
                errors.append(f"Unsafe resource exposure: {manifest_id} -> {resource_id}")

        for query_id in exposed_query_ids:
            if query_id not in query_map:
                errors.append(f"Orphan manifest query reference: {manifest_id} -> {query_id}")
                continue
            query = query_map[query_id]
            if str(query.get("server_id", "")) != server_id:
                errors.append(f"Server mismatch for manifest query {query_id}: {query.get('server_id')} != {server_id}")
            if str(query.get("owner_system_id", "")) != owner_system_id:
                errors.append(f"Owner mismatch for manifest query {query_id}: {query.get('owner_system_id')} != {owner_system_id}")
            if str(query.get("resource_id", "")) not in exposed_resource_ids:
                errors.append(f"Query exposed without resource: {manifest_id} -> {query_id}")
            if str(query.get("capability_id", "")) not in exposed_capability_ids:
                errors.append(f"Query exposed without capability: {manifest_id} -> {query_id}")
            if query.get("read_only") is not True or query.get("side_effects") is not False:
                errors.append(f"Unsafe query exposure: {manifest_id} -> {query_id}")

    discovery_priorities: dict[tuple[str, int], str] = {}
    for discovery_id, discovery in discovery_map.items():
        server_id = str(discovery.get("server_id", ""))
        priority = discovery.get("priority")
        if server_id not in server_map:
            errors.append(f"Orphan discovery server reference: {discovery_id} -> {server_id}")
            continue
        server = server_map[server_id]
        if str(discovery.get("owner_system_id", "")) != str(server.get("owner_system_id", "")):
            errors.append(f"Owner mismatch for discovery {discovery_id}: {discovery.get('owner_system_id')} != {server.get('owner_system_id')}")
        if str(discovery.get("transport", "")) != str(server.get("transport", "")):
            errors.append(f"Transport mismatch for discovery {discovery_id}: {discovery.get('transport')} != {server.get('transport')}")
        if str(discovery.get("bind_scope", "")) != str(server.get("bind_scope", "")):
            errors.append(f"Bind scope mismatch for discovery {discovery_id}: {discovery.get('bind_scope')} != {server.get('bind_scope')}")
        if isinstance(priority, int):
            priority_key = (server_id, priority)
            if priority_key in discovery_priorities:
                errors.append(
                    f"Ambiguous discovery priority for {server_id}: {discovery_priorities[priority_key]} and {discovery_id}"
                )
            else:
                discovery_priorities[priority_key] = discovery_id

    def _reference_set(value: Any) -> set[str]:
        return {str(item) for item in value} if isinstance(value, list) else set()

    for consumption_id, consumption in consumption_map.items():
        client_id = str(consumption.get("client_id", ""))
        server_id = str(consumption.get("server_id", ""))
        owner_system_id = str(consumption.get("owner_system_id", ""))
        if client_id not in client_map:
            errors.append(f"Orphan consumption client reference: {consumption_id} -> {client_id}")
            continue
        client = client_map[client_id]
        if owner_system_id != str(client.get("owner_system_id", "")):
            errors.append(f"Owner mismatch for consumption {consumption_id}: {owner_system_id} != {client.get('owner_system_id')}")
        if server_id not in server_map:
            errors.append(f"Orphan consumption server reference: {consumption_id} -> {server_id}")
            continue
        server = server_map[server_id]
        manifest_id = str(consumption.get("expected_manifest_id", ""))
        if manifest_id not in manifest_map:
            errors.append(f"Orphan consumption manifest reference: {consumption_id} -> {manifest_id}")
            continue
        manifest = manifest_map[manifest_id]
        if str(manifest.get("server_id", "")) != server_id:
            errors.append(f"Server mismatch for consumption manifest {manifest_id}: {manifest.get('server_id')} != {server_id}")
        if str(manifest.get("owner_system_id", "")) != str(server.get("owner_system_id", "")):
            errors.append(f"Owner mismatch for expected manifest {manifest_id}: {manifest.get('owner_system_id')} != {server.get('owner_system_id')}")

        discovery_id = str(consumption.get("discovery_id", ""))
        if discovery_id not in discovery_map:
            errors.append(f"Orphan consumption discovery reference: {consumption_id} -> {discovery_id}")
        elif str(discovery_map[discovery_id].get("server_id", "")) != server_id:
            errors.append(f"Server mismatch for discovery {discovery_id}: {discovery_map[discovery_id].get('server_id')} != {server_id}")

        expected_capability_ids = _reference_set(consumption.get("expected_capability_ids"))
        expected_tool_ids = _reference_set(consumption.get("expected_tool_ids"))
        expected_resource_ids = _reference_set(consumption.get("expected_resource_ids"))
        expected_query_ids = _reference_set(consumption.get("expected_query_ids"))
        exposed_capability_ids = _reference_set(manifest.get("capability_ids"))
        exposed_tool_ids = _reference_set(manifest.get("tool_ids"))
        exposed_resource_ids = _reference_set(manifest.get("resource_ids"))
        exposed_query_ids = _reference_set(manifest.get("query_ids"))

        for capability_id in expected_capability_ids:
            if capability_id not in capability_map:
                errors.append(f"Orphan expected capability reference: {consumption_id} -> {capability_id}")
                continue
            capability = capability_map[capability_id]
            if str(capability.get("server_id", "")) != server_id:
                errors.append(f"Server mismatch for expected capability {capability_id}: {capability.get('server_id')} != {server_id}")
            if capability_id not in exposed_capability_ids:
                errors.append(f"Unexposed expected capability: {consumption_id} -> {capability_id}")

        for tool_id in expected_tool_ids:
            if tool_id not in tool_map:
                errors.append(f"Orphan expected tool reference: {consumption_id} -> {tool_id}")
                continue
            tool = tool_map[tool_id]
            if str(tool.get("server_id", "")) != server_id:
                errors.append(f"Server mismatch for expected tool {tool_id}: {tool.get('server_id')} != {server_id}")
            if tool_id not in exposed_tool_ids:
                errors.append(f"Unexposed expected tool: {consumption_id} -> {tool_id}")
            if str(tool.get("capability_id", "")) not in expected_capability_ids:
                errors.append(f"Expected tool capability missing: {consumption_id} -> {tool_id}")
            if tool.get("read_only") is not True or tool.get("side_effects") is not False:
                errors.append(f"Unsafe expected tool: {consumption_id} -> {tool_id}")

        for resource_id in expected_resource_ids:
            if resource_id not in resource_map:
                errors.append(f"Orphan expected resource reference: {consumption_id} -> {resource_id}")
                continue
            resource = resource_map[resource_id]
            if str(resource.get("server_id", "")) != server_id:
                errors.append(f"Server mismatch for expected resource {resource_id}: {resource.get('server_id')} != {server_id}")
            if resource_id not in exposed_resource_ids:
                errors.append(f"Unexposed expected resource: {consumption_id} -> {resource_id}")
            if resource.get("read_only") is not True:
                errors.append(f"Unsafe expected resource: {consumption_id} -> {resource_id}")

        for query_id in expected_query_ids:
            if query_id not in query_map:
                errors.append(f"Orphan expected query reference: {consumption_id} -> {query_id}")
                continue
            query = query_map[query_id]
            if str(query.get("server_id", "")) != server_id:
                errors.append(f"Server mismatch for expected query {query_id}: {query.get('server_id')} != {server_id}")
            if query_id not in exposed_query_ids:
                errors.append(f"Unexposed expected query: {consumption_id} -> {query_id}")
            if str(query.get("resource_id", "")) not in expected_resource_ids:
                errors.append(f"Expected query resource missing: {consumption_id} -> {query_id}")
            if str(query.get("capability_id", "")) not in expected_capability_ids:
                errors.append(f"Expected query capability missing: {consumption_id} -> {query_id}")
            if query.get("read_only") is not True or query.get("side_effects") is not False:
                errors.append(f"Unsafe expected query: {consumption_id} -> {query_id}")

        compatibility = consumption.get("compatibility")
        if isinstance(compatibility, dict):
            minimum_server_version = compatibility.get("minimum_server_version")
            if (
                isinstance(minimum_server_version, str)
                and validate_semver(minimum_server_version)
                and validate_semver(str(server.get("server_version", "")))
                and Version(str(server["server_version"])) < Version(minimum_server_version)
            ):
                errors.append(f"Incompatible server version for consumption {consumption_id}: {server.get('server_version')} < {minimum_server_version}")
            required_manifest_version = compatibility.get("manifest_version")
            if isinstance(required_manifest_version, str) and str(manifest.get("manifest_version", "")) != required_manifest_version:
                errors.append(f"Incompatible manifest version for consumption {consumption_id}: {manifest.get('manifest_version')} != {required_manifest_version}")
            capability_versions = compatibility.get("capability_versions")
            if isinstance(capability_versions, dict):
                for capability_id, required_version in capability_versions.items():
                    if capability_id not in expected_capability_ids:
                        errors.append(f"Compatibility capability is not expected: {consumption_id} -> {capability_id}")
                        continue
                    capability = capability_map.get(str(capability_id))
                    actual_version = capability.get("version") if capability else None
                    if (
                        isinstance(actual_version, str)
                        and validate_semver(str(required_version))
                        and validate_semver(actual_version)
                        and Version(actual_version) < Version(str(required_version))
                    ):
                        errors.append(f"Incompatible capability version for consumption {consumption_id}: {capability_id}")

    def _policy_targets(scope: dict[str, Any]) -> set[tuple[str, str]]:
        return {
            (kind, value)
            for kind, field in [
                ("server", "server_ids"),
                ("capability", "capability_ids"),
                ("tool", "tool_ids"),
                ("resource", "resource_ids"),
                ("query", "query_ids"),
            ]
            for value in _reference_set(scope.get(field))
        }

    def _validate_policy_targets(policy: dict[str, Any], source: str, scope: dict[str, Any]) -> set[tuple[str, str]]:
        target_keys = _policy_targets(scope)
        server_ids = _reference_set(scope.get("server_ids"))
        for server_id in server_ids:
            if server_id not in server_map:
                errors.append(f"Unknown policy server target: {server_id}")
        for capability_id in _reference_set(scope.get("capability_ids")):
            capability = capability_map.get(capability_id)
            if capability is None:
                errors.append(f"Unknown policy capability target: {capability_id}")
                continue
            if server_ids and str(capability.get("server_id", "")) not in server_ids:
                errors.append(f"Policy capability crosses server scope: {capability_id}")
            if capability.get("read_only") is not True or capability.get("mode") != "read_only":
                errors.append(f"Unsafe policy capability target: {capability_id}")
        for tool_id in _reference_set(scope.get("tool_ids")):
            tool = tool_map.get(tool_id)
            if tool is None:
                errors.append(f"Unknown policy tool target: {tool_id}")
                continue
            if server_ids and str(tool.get("server_id", "")) not in server_ids:
                errors.append(f"Policy tool crosses server scope: {tool_id}")
            if tool.get("read_only") is not True or tool.get("side_effects") is not False:
                errors.append(f"Unsafe policy tool target: {tool_id}")
        for resource_id in _reference_set(scope.get("resource_ids")):
            resource = resource_map.get(resource_id)
            if resource is None:
                errors.append(f"Unknown policy resource target: {resource_id}")
                continue
            if server_ids and str(resource.get("server_id", "")) not in server_ids:
                errors.append(f"Policy resource crosses server scope: {resource_id}")
            if resource.get("read_only") is not True:
                errors.append(f"Unsafe policy resource target: {resource_id}")
        for query_id in _reference_set(scope.get("query_ids")):
            query = query_map.get(query_id)
            if query is None:
                errors.append(f"Unknown policy query target: {query_id}")
                continue
            if server_ids and str(query.get("server_id", "")) not in server_ids:
                errors.append(f"Policy query crosses server scope: {query_id}")
            if query.get("read_only") is not True or query.get("side_effects") is not False:
                errors.append(f"Unsafe policy query target: {query_id}")
        return target_keys

    policy_conflicts: dict[tuple[str, tuple[str, str], int], tuple[str, str]] = {}
    for policy_id, policy in authorization_policy_map.items():
        source = f"{registry_path}: authorization_policies.{policy_id}"
        if str(policy.get("owner_system_id", "")) not in system_ids:
            errors.append(f"Unknown authorization policy owner: {policy.get('owner_system_id')}")
        subject = policy.get("subject")
        subject_id = str(subject.get("id", "")) if isinstance(subject, dict) else ""
        if subject_id not in client_map:
            errors.append(f"Unknown policy subject client: {subject_id}")
        targets = _validate_policy_targets(policy, source, policy)
        approval_policy_id = policy.get("approval_policy_id")
        if policy.get("effect") == "approval_required":
            if not isinstance(approval_policy_id, str):
                errors.append(f"Approval-required policy missing approval policy: {policy_id}")
            elif approval_policy_id not in approval_policy_map:
                errors.append(f"Unknown approval policy: {approval_policy_id}")
        elif approval_policy_id is not None:
            errors.append(f"Only approval-required policies may reference approval policy: {policy_id}")
        for target in targets:
            conflict_key = (subject_id, target, int(policy.get("priority", 0)))
            effect = str(policy.get("effect", ""))
            previous = policy_conflicts.get(conflict_key)
            if previous is not None and previous[1] != effect:
                errors.append(f"Conflicting same-priority policies: {previous[0]} and {policy_id}")
            else:
                policy_conflicts[conflict_key] = (policy_id, effect)

    for policy_id, policy in approval_policy_map.items():
        if str(policy.get("owner_system_id", "")) not in system_ids:
            errors.append(f"Unknown approval policy owner: {policy.get('owner_system_id')}")
        approver_system_id = str(policy.get("approver_system_id", ""))
        if approver_system_id not in system_ids:
            errors.append(f"Unknown approver authority: {approver_system_id}")
        _validate_policy_targets(policy, f"{registry_path}: approval_policies.{policy_id}", policy.get("scope", {}))

    for policy_id, policy in authorization_policy_map.items():
        approval_policy_id = policy.get("approval_policy_id")
        if policy.get("effect") != "approval_required" or not isinstance(approval_policy_id, str):
            continue
        approval_policy = approval_policy_map.get(approval_policy_id)
        if approval_policy is None:
            continue
        policy_targets = _policy_targets(policy)
        approval_targets = _policy_targets(approval_policy.get("scope", {}))
        if not policy_targets.issubset(approval_targets):
            errors.append(f"Approval scope does not cover authorization policy: {policy_id}")
        subject = policy.get("subject")
        subject_id = str(subject.get("id", "")) if isinstance(subject, dict) else ""
        subject_client = client_map.get(subject_id)
        approver = str(approval_policy.get("approver_system_id", ""))
        if subject_id == approver or (subject_client and str(subject_client.get("owner_system_id", "")) == approver):
            errors.append(f"Self-approval is not allowed: {policy_id}")

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
