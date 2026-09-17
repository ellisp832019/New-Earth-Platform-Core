from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from new_earth_platform.programme_compiler import compile_data, compile_file
from new_earth_platform.programme_compiler.resolver import Resolution


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "programme-definition.schema.json"
EXAMPLE_PATH = ROOT / "examples" / "programmes" / "PROGRAMME_DEFINITION_CONTRACT_V1.example.yaml"


def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def example():
    return yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))


def clean_definition():
    data = copy.deepcopy(example())
    data["repository_bindings"] = []
    data["platform_contract_refs"] = []
    for wp in data["work_packages"]:
        wp["dependencies"] = []
        wp["blockers"] = []
        for task in wp["tasks"]:
            task["blockers"] = []
    return data


def clone_wp(source, suffix):
    wp = copy.deepcopy(source)
    wp["work_package_id"] = f'{source["work_package_id"]}-{suffix}'
    wp["title"] = f'{source["title"]} {suffix}'
    wp["dependencies"] = []
    wp["blockers"] = []
    for index, task in enumerate(wp["tasks"], start=1):
        task["task_id"] = f'{task["task_id"]}-{suffix}-{index}'
        task["blockers"] = []
    return wp


class Resolved:
    def resolve_repository_binding(self, binding):
        return Resolution("RESOLVED", evidence="adversarial-test")

    def resolve_platform_contract_ref(self, contract_ref):
        return Resolution("RESOLVED", evidence="adversarial-test")


class Contradicted:
    def resolve_repository_binding(self, binding):
        return Resolution("CONTRADICTED", evidence="test", message="binding contradicted")

    def resolve_platform_contract_ref(self, contract_ref):
        return Resolution("CONTRADICTED", evidence="test", message="contract contradicted")


class ExplodingResolver:
    def resolve_repository_binding(self, binding):
        raise RuntimeError("simulated authoritative adapter outage")

    def resolve_platform_contract_ref(self, contract_ref):
        raise RuntimeError("simulated authoritative adapter outage")


def test_malformed_yaml_is_invalid(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("programme: [\n", encoding="utf-8")
    result = compile_file(path, schema_path=SCHEMA_PATH)
    assert result.outcome == "INVALID"
    assert result.diagnostics[0].code == "PCV001"


def test_malformed_json_is_invalid(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"programme":', encoding="utf-8")
    result = compile_file(path, schema_path=SCHEMA_PATH)
    assert result.outcome == "INVALID"
    assert result.diagnostics[0].code == "PCV001"


def test_unknown_top_level_field_is_invalid():
    data = clean_definition()
    data["unexpected"] = "malicious"
    assert compile_data(data, schema=schema(), resolver=Resolved()).outcome == "INVALID"


def test_unknown_nested_field_is_invalid():
    data = clean_definition()
    data["programme"]["unexpected"] = "malicious"
    assert compile_data(data, schema=schema(), resolver=Resolved()).outcome == "INVALID"


def test_invalid_authority_is_invalid():
    data = clean_definition()
    data["work_packages"][0]["authority_required"] = "SUPERUSER"
    assert compile_data(data, schema=schema(), resolver=Resolved()).outcome == "INVALID"


def test_nested_operational_state_is_invalid():
    data = clean_definition()
    data["work_packages"][0]["tasks"][0]["execution_state"] = "RUNNING"
    result = compile_data(data, schema=schema(), resolver=Resolved())
    assert result.outcome == "INVALID"
    assert any(d.code in {"PCV010", "PCV025"} for d in result.diagnostics)


def test_three_node_cycle_is_invalid():
    data = clean_definition()
    first = data["work_packages"][0]
    second = clone_wp(first, "B")
    third = clone_wp(first, "C")
    data["work_packages"] = [first, second, third]
    first["dependencies"] = [second["work_package_id"]]
    second["dependencies"] = [third["work_package_id"]]
    third["dependencies"] = [first["work_package_id"]]
    result = compile_data(data, schema=schema(), resolver=Resolved())
    assert result.outcome == "INVALID"
    assert any(d.code == "PCV024" for d in result.diagnostics)


def test_unknown_precedes_blocked():
    data = clean_definition()
    data["repository_bindings"] = [{"repository_id": "REPO-UNKNOWN", "required": True}]
    data["work_packages"][0]["blockers"] = ["BLOCKER"]
    result = compile_data(data, schema=schema())
    assert result.outcome == "UNKNOWN"
    assert any(d.classification == "UNKNOWN" for d in result.diagnostics)
    assert any(d.classification == "BLOCKED" for d in result.diagnostics)


def test_contradiction_precedes_blocked():
    data = clean_definition()
    data["repository_bindings"] = [{"repository_id": "REPO-X", "required": True}]
    data["work_packages"][0]["blockers"] = ["BLOCKER"]
    result = compile_data(data, schema=schema(), resolver=Contradicted())
    assert result.outcome == "INVALID"


def test_diagnostics_are_deterministic():
    data = clean_definition()
    first = data["work_packages"][0]
    second = clone_wp(first, "B")
    second["work_package_id"] = first["work_package_id"]
    second["tasks"][0]["task_id"] = first["tasks"][0]["task_id"]
    data["work_packages"].append(second)

    one = compile_data(data, schema=schema(), resolver=Resolved())
    two = compile_data(copy.deepcopy(data), schema=schema(), resolver=Resolved())
    assert [d.to_dict() for d in one.diagnostics] == [d.to_dict() for d in two.diagnostics]


def test_unicode_valid_and_deterministic():
    data = clean_definition()
    data["programme"]["name"] = "New Earth â€“ ðŸŒ"
    data["programme"]["objective"] = "cafÃ© naÃ¯ve æ—¥æœ¬èªž ðŸš€"
    one = compile_data(data, schema=schema(), resolver=Resolved())
    two = compile_data(copy.deepcopy(data), schema=schema(), resolver=Resolved())
    assert one.outcome == "VALID"
    assert one.normalized_content_sha256 == two.normalized_content_sha256
    assert one.registration_plan["plan_sha256"] == two.registration_plan["plan_sha256"]


def test_large_valid_programme():
    data = clean_definition()
    template = data["work_packages"][0]
    packages = []
    for index in range(1, 101):
        wp = clone_wp(template, f"{index:03d}")
        if packages:
            wp["dependencies"] = [packages[-1]["work_package_id"]]
        packages.append(wp)
    data["work_packages"] = packages
    result = compile_data(data, schema=schema(), resolver=Resolved())
    assert result.outcome == "VALID"
    assert result.registration_plan["proposed_work"]["task_count"] == 100


def test_plan_never_claims_operational_authority():
    result = compile_data(clean_definition(), schema=schema(), resolver=Resolved())
    authority = result.registration_plan["authority_statement"]
    assert authority["creates_operational_state"] is False
    assert authority["admits_repositories"] is False
    assert authority["activates_work"] is False
    assert authority["dispatches_tasks"] is False


def test_yaml_json_semantics_share_normalized_hash(tmp_path):
    data = clean_definition()
    yp = tmp_path / "p.yaml"
    jp = tmp_path / "p.json"
    yp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    jp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    yr = compile_file(yp, schema_path=SCHEMA_PATH, resolver=Resolved())
    jr = compile_file(jp, schema_path=SCHEMA_PATH, resolver=Resolved())

    assert yr.outcome == "VALID"
    assert jr.outcome == "VALID"
    assert yr.normalized_content_sha256 == jr.normalized_content_sha256


def test_yaml_json_semantics_share_plan_hash(tmp_path):
    data = clean_definition()
    yp = tmp_path / "p.yaml"
    jp = tmp_path / "p.json"
    yp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    jp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    yr = compile_file(yp, schema_path=SCHEMA_PATH, resolver=Resolved())
    jr = compile_file(jp, schema_path=SCHEMA_PATH, resolver=Resolved())

    assert yr.registration_plan["plan_sha256"] == jr.registration_plan["plan_sha256"]


def test_source_hash_distinguishes_serializations(tmp_path):
    data = clean_definition()
    yp = tmp_path / "p.yaml"
    jp = tmp_path / "p.json"
    yp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    jp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    yr = compile_file(yp, schema_path=SCHEMA_PATH, resolver=Resolved())
    jr = compile_file(jp, schema_path=SCHEMA_PATH, resolver=Resolved())

    assert yr.source_sha256 != jr.source_sha256


def test_authoritative_adapter_outage_becomes_unknown():
    data = clean_definition()
    data["repository_bindings"] = [{"repository_id": "REPO-OUTAGE", "required": True}]
    result = compile_data(data, schema=schema(), resolver=ExplodingResolver())
    assert result.outcome == "UNKNOWN"
    assert any(d.classification == "UNKNOWN" for d in result.diagnostics)


@pytest.mark.parametrize("required", [True, False])
def test_binding_required_flag_never_activates_work(required):
    data = clean_definition()
    data["repository_bindings"] = [{"repository_id": "REPO-X", "required": required}]
    result = compile_data(data, schema=schema(), resolver=Resolved())
    assert result.outcome == "VALID"
    assert result.registration_plan["authority_statement"]["activates_work"] is False


def test_schema_failure_prevents_semantic_guessing():
    data = clean_definition()
    data["work_packages"][0]["dependencies"] = [123]
    result = compile_data(data, schema=schema(), resolver=Resolved())
    assert result.outcome == "INVALID"
    assert any(d.code == "PCV010" for d in result.diagnostics)
    assert not any(d.code == "PCV023" for d in result.diagnostics)
