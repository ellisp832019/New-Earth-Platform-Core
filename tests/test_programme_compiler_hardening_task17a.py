from __future__ import annotations

import json
from pathlib import Path

import yaml

from new_earth_platform.programme_compiler import compile_data, compile_file


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "programme-definition.schema.json"
EXAMPLE_PATH = ROOT / "examples" / "programmes" / "PROGRAMME_DEFINITION_CONTRACT_V1.example.yaml"


def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def clean_definition():
    data = yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))
    data["repository_bindings"] = []
    data["platform_contract_refs"] = []
    for wp in data["work_packages"]:
        wp["dependencies"] = []
        wp["blockers"] = []
        for task in wp["tasks"]:
            task["blockers"] = []
    return data


class Resolved:
    def resolve_repository_binding(self, binding):
        from new_earth_platform.programme_compiler.resolver import Resolution
        return Resolution("RESOLVED", evidence="task17a")

    def resolve_platform_contract_ref(self, contract_ref):
        from new_earth_platform.programme_compiler.resolver import Resolution
        return Resolution("RESOLVED", evidence="task17a")


class Exploding:
    def resolve_repository_binding(self, binding):
        raise RuntimeError("volatile repository outage detail")

    def resolve_platform_contract_ref(self, contract_ref):
        raise ValueError("volatile contract outage detail")


def test_plan_hash_ignores_source_serialization_but_keeps_source_hash(tmp_path):
    data = clean_definition()
    yp = tmp_path / "programme.yaml"
    jp = tmp_path / "programme.json"

    yp.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    jp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    yr = compile_file(yp, schema_path=SCHEMA_PATH, resolver=Resolved())
    jr = compile_file(jp, schema_path=SCHEMA_PATH, resolver=Resolved())

    assert yr.outcome == "VALID"
    assert jr.outcome == "VALID"
    assert yr.normalized_content_sha256 == jr.normalized_content_sha256
    assert yr.source_sha256 != jr.source_sha256
    assert yr.registration_plan["source"]["source_sha256"] == yr.source_sha256
    assert jr.registration_plan["source"]["source_sha256"] == jr.source_sha256
    assert yr.registration_plan["plan_sha256"] == jr.registration_plan["plan_sha256"]


def test_repository_resolver_exception_is_unknown_not_crash():
    data = clean_definition()
    data["repository_bindings"] = [
        {"repository_id": "REPO-OUTAGE", "required": True}
    ]

    result = compile_data(data, schema=schema(), resolver=Exploding())

    assert result.outcome == "UNKNOWN"
    matches = [d for d in result.diagnostics if d.code == "PCV070"]
    assert len(matches) == 1
    assert matches[0].classification == "UNKNOWN"
    assert matches[0].evidence == "resolver_exception=RuntimeError"
    assert "volatile repository outage detail" not in matches[0].message


def test_contract_resolver_exception_is_unknown_not_crash():
    data = clean_definition()
    data["platform_contract_refs"] = ["new-earth.contract.outage"]

    result = compile_data(data, schema=schema(), resolver=Exploding())

    assert result.outcome == "UNKNOWN"
    matches = [d for d in result.diagnostics if d.code == "PCV030"]
    assert len(matches) == 1
    assert matches[0].classification == "UNKNOWN"
    assert matches[0].evidence == "resolver_exception=ValueError"
    assert "volatile contract outage detail" not in matches[0].message


def test_resolver_exception_diagnostics_are_deterministic():
    data = clean_definition()
    data["repository_bindings"] = [
        {"repository_id": "REPO-OUTAGE", "required": True}
    ]

    one = compile_data(data, schema=schema(), resolver=Exploding())
    two = compile_data(data, schema=schema(), resolver=Exploding())

    assert [d.to_dict() for d in one.diagnostics] == [
        d.to_dict() for d in two.diagnostics
    ]
    assert one.registration_plan["plan_sha256"] == two.registration_plan["plan_sha256"]
