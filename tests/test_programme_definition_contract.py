from pathlib import Path
import json

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "programme-definition.schema.json"
VALID = ROOT / "examples" / "programmes" / "PROGRAMME_DEFINITION_CONTRACT_V1.example.yaml"
INVALID_ROOT = ROOT / "examples" / "programmes" / "invalid"


def _load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _validator():
    with SCHEMA.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_programme_definition_schema_is_valid_draft_2020_12():
    _validator()


def test_valid_programme_definition_fixture_passes():
    errors = list(_validator().iter_errors(_load_yaml(VALID)))
    assert errors == []


def test_invalid_fixture_missing_blockers_fails_closed():
    path = INVALID_ROOT / "MISSING_BLOCKERS.invalid.yaml"
    errors = list(_validator().iter_errors(_load_yaml(path)))
    assert errors
    assert any("blockers" in error.message for error in errors)


def test_invalid_fixture_rejects_live_operational_state():
    path = INVALID_ROOT / "OPERATIONAL_STATE_FIELD.invalid.yaml"
    errors = list(_validator().iter_errors(_load_yaml(path)))
    assert errors
    assert any("execution_eligible" in error.message for error in errors)


def test_invalid_fixture_rejects_unknown_authority():
    path = INVALID_ROOT / "UNKNOWN_AUTHORITY.invalid.yaml"
    errors = list(_validator().iter_errors(_load_yaml(path)))
    assert errors
    assert any("SUPERUSER" in error.message for error in errors)
