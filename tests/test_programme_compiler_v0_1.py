from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from new_earth_platform.programme_compiler import compile_data, compile_file
from new_earth_platform.programme_compiler.resolver import Resolution


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "programme-definition.schema.json"
EXAMPLE_PATH = (
    ROOT
    / "examples"
    / "programmes"
    / "PROGRAMME_DEFINITION_CONTRACT_V1.example.yaml"
)


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _example():
    return yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))


def _clean_definition():
    data = copy.deepcopy(_example())

    # Contract V1 defines these at the DOCUMENT ROOT.
    data["repository_bindings"] = []
    data["platform_contract_refs"] = []

    for wp in data["work_packages"]:
        wp["dependencies"] = []
        wp["blockers"] = []
        for task in wp["tasks"]:
            task["blockers"] = []

    return data


class ResolvedReferenceResolver:
    def resolve_repository_binding(self, binding):
        return Resolution("RESOLVED", evidence="test")

    def resolve_platform_contract_ref(self, contract_ref):
        return Resolution("RESOLVED", evidence="test")


class ContradictedReferenceResolver:
    def resolve_repository_binding(self, binding):
        return Resolution(
            "CONTRADICTED",
            evidence="test",
            message="repository binding contradicted",
        )

    def resolve_platform_contract_ref(self, contract_ref):
        return Resolution(
            "CONTRADICTED",
            evidence="test",
            message="contract reference contradicted",
        )


def test_canonical_example_is_schema_valid():
    data = _example()
    errors = list(
        __import__("jsonschema")
        .Draft202012Validator(_schema())
        .iter_errors(data)
    )
    assert errors == []


def test_clean_definition_is_schema_valid():
    data = _clean_definition()
    errors = list(
        __import__("jsonschema")
        .Draft202012Validator(_schema())
        .iter_errors(data)
    )
    assert errors == []


def test_clean_local_definition_is_valid_and_non_operational():
    result = compile_data(
        _clean_definition(),
        schema=_schema(),
        resolver=ResolvedReferenceResolver(),
    )

    assert result.outcome == "VALID"
    authority = result.registration_plan["authority_statement"]
    assert authority == {
        "creates_operational_state": False,
        "admits_repositories": False,
        "activates_work": False,
        "dispatches_tasks": False,
    }


def test_compilation_is_deterministic_for_identical_input_and_snapshot():
    data = _clean_definition()
    schema = _schema()

    first = compile_data(
        data,
        schema=schema,
        resolver=ResolvedReferenceResolver(),
    )
    second = compile_data(
        copy.deepcopy(data),
        schema=schema,
        resolver=ResolvedReferenceResolver(),
    )

    assert first.outcome == second.outcome
    assert first.normalized_content_sha256 == second.normalized_content_sha256
    assert first.registration_plan["plan_sha256"] == second.registration_plan["plan_sha256"]
    assert [d.to_dict() for d in first.diagnostics] == [
        d.to_dict() for d in second.diagnostics
    ]


def test_duplicate_work_package_id_is_invalid():
    data = _clean_definition()
    duplicate = copy.deepcopy(data["work_packages"][0])
    duplicate["title"] = f'{duplicate["title"]} duplicate'
    for index, task in enumerate(duplicate["tasks"], start=1):
        task["task_id"] = f'{task["task_id"]}-DUP-{index}'
    data["work_packages"].append(duplicate)

    result = compile_data(
        data,
        schema=_schema(),
        resolver=ResolvedReferenceResolver(),
    )

    assert result.outcome == "INVALID"
    assert any(d.code == "PCV020" for d in result.diagnostics)


def test_duplicate_task_id_across_programme_is_invalid():
    data = _clean_definition()
    first = data["work_packages"][0]

    second = copy.deepcopy(first)
    second["work_package_id"] = f'{first["work_package_id"]}-SECOND'
    second["title"] = f'{first["title"]} second'
    second["dependencies"] = []

    first_task_id = first["tasks"][0]["task_id"]
    second["tasks"][0]["task_id"] = first_task_id
    data["work_packages"].append(second)

    result = compile_data(
        data,
        schema=_schema(),
        resolver=ResolvedReferenceResolver(),
    )

    assert result.outcome == "INVALID"
    assert any(d.code == "PCV021" for d in result.diagnostics)


def test_self_dependency_is_invalid():
    data = _clean_definition()
    wp = data["work_packages"][0]
    wp["dependencies"] = [wp["work_package_id"]]

    result = compile_data(
        data,
        schema=_schema(),
        resolver=ResolvedReferenceResolver(),
    )

    assert result.outcome == "INVALID"
    assert any(d.code == "PCV022" for d in result.diagnostics)


def test_missing_local_dependency_is_invalid():
    data = _clean_definition()
    data["work_packages"][0]["dependencies"] = ["WP-DOES-NOT-EXIST"]

    result = compile_data(
        data,
        schema=_schema(),
        resolver=ResolvedReferenceResolver(),
    )

    assert result.outcome == "INVALID"
    assert any(d.code == "PCV023" for d in result.diagnostics)


def test_dependency_cycle_is_invalid():
    data = _clean_definition()
    first = data["work_packages"][0]

    second = copy.deepcopy(first)
    second["work_package_id"] = f'{first["work_package_id"]}-SECOND'
    second["title"] = f'{first["title"]} second'
    for index, task in enumerate(second["tasks"], start=1):
        task["task_id"] = f'{task["task_id"]}-SECOND-{index}'
    second["dependencies"] = []

    data["work_packages"].append(second)
    first["dependencies"] = [second["work_package_id"]]
    second["dependencies"] = [first["work_package_id"]]

    result = compile_data(
        data,
        schema=_schema(),
        resolver=ResolvedReferenceResolver(),
    )

    assert result.outcome == "INVALID"
    assert any(d.code == "PCV024" for d in result.diagnostics)


def test_unknown_root_level_repository_binding_fails_closed():
    data = _clean_definition()
    data["repository_bindings"] = [
        {
            "repository_id": "REPO-TEST-UNKNOWN",
            "required": True,
        }
    ]

    result = compile_data(data, schema=_schema())

    assert result.outcome == "UNKNOWN"
    assert any(d.code == "PCV070" for d in result.diagnostics)
    assert result.registration_plan["references"]["repository_bindings"] == (
        data["repository_bindings"]
    )


def test_unknown_root_level_platform_contract_ref_fails_closed():
    data = _clean_definition()
    data["platform_contract_refs"] = ["new-earth.test.contract.v1"]

    result = compile_data(data, schema=_schema())

    assert result.outcome == "UNKNOWN"
    assert any(d.code == "PCV030" for d in result.diagnostics)
    assert result.registration_plan["references"]["platform_contract_refs"] == (
        data["platform_contract_refs"]
    )


def test_contradicted_external_reference_is_invalid():
    data = _clean_definition()
    data["repository_bindings"] = [
        {
            "repository_id": "REPO-TEST-CONTRADICTED",
            "required": True,
        }
    ]

    result = compile_data(
        data,
        schema=_schema(),
        resolver=ContradictedReferenceResolver(),
    )

    assert result.outcome == "INVALID"
    assert any(d.code == "PCV031" for d in result.diagnostics)


def test_explicit_work_package_blocker_is_blocked():
    data = _clean_definition()
    data["work_packages"][0]["blockers"] = ["TEST-BLOCKER"]

    result = compile_data(
        data,
        schema=_schema(),
        resolver=ResolvedReferenceResolver(),
    )

    assert result.outcome == "BLOCKED"
    assert any(d.code == "PCV040" for d in result.diagnostics)


def test_explicit_task_blocker_is_blocked():
    data = _clean_definition()
    data["work_packages"][0]["tasks"][0]["blockers"] = ["TASK-BLOCKER"]

    result = compile_data(
        data,
        schema=_schema(),
        resolver=ResolvedReferenceResolver(),
    )

    assert result.outcome == "BLOCKED"
    assert any(d.code == "PCV040" for d in result.diagnostics)


def test_approval_required_is_info_not_compile_blocker():
    data = _clean_definition()
    data["work_packages"][0]["approval_required"] = True

    result = compile_data(
        data,
        schema=_schema(),
        resolver=ResolvedReferenceResolver(),
    )

    assert result.outcome == "VALID"
    assert any(d.code == "PCV060" for d in result.diagnostics)


def test_prohibited_operational_field_is_invalid():
    data = _clean_definition()
    data["programme"]["execution_eligible"] = True

    result = compile_data(
        data,
        schema=_schema(),
        resolver=ResolvedReferenceResolver(),
    )

    assert result.outcome == "INVALID"
    assert any(d.code in {"PCV010", "PCV025"} for d in result.diagnostics)


def test_invalid_precedes_unknown_and_blocked():
    data = _clean_definition()
    data["programme"]["execution_eligible"] = True
    data["repository_bindings"] = [
        {
            "repository_id": "REPO-TEST-UNKNOWN",
            "required": True,
        }
    ]
    data["work_packages"][0]["blockers"] = ["BLOCKER"]

    result = compile_data(data, schema=_schema())

    # Schema-invalid structure suppresses semantic/reference stages, so INVALID wins.
    assert result.outcome == "INVALID"


def test_unknown_precedes_blocked():
    data = _clean_definition()
    data["repository_bindings"] = [
        {
            "repository_id": "REPO-TEST-UNKNOWN",
            "required": True,
        }
    ]
    data["work_packages"][0]["blockers"] = ["BLOCKER"]

    result = compile_data(data, schema=_schema())

    assert result.outcome == "UNKNOWN"
    assert any(d.classification == "UNKNOWN" for d in result.diagnostics)
    assert any(d.classification == "BLOCKED" for d in result.diagnostics)


def test_parse_failure_is_invalid(tmp_path):
    broken = tmp_path / "broken.yaml"
    broken.write_text("programme: [\n", encoding="utf-8")

    result = compile_file(broken, schema_path=SCHEMA_PATH)

    assert result.outcome == "INVALID"
    assert result.diagnostics[0].code == "PCV001"
