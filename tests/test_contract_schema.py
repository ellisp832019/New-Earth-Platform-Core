from pathlib import Path

from new_earth_platform.validation import validate_yaml_against_schema


def test_example_contracts_are_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = root / "schemas/project-contract.schema.json"
    for path in sorted((root / "examples/contracts").glob("*.yaml")):
        assert validate_yaml_against_schema(path, schema) == [], path
