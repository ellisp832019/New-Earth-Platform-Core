from pathlib import Path

import yaml

from new_earth_platform.validation import validate_cap01a_contract


def _contract_copy(tmp_path: Path) -> tuple[Path, dict]:
    root = Path(__file__).resolve().parents[1]
    source = root / "examples/cap-01a/minimal-architecture.yaml"
    path = tmp_path / "architecture.yaml"
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path, data


def test_minimal_cap01a_contract_is_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_cap01a_contract(root) == []


def test_cap01a_rejects_missing_owner(tmp_path: Path) -> None:
    path, data = _contract_copy(tmp_path)
    del data["capabilities"][0]["owner"]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    root = Path(__file__).resolve().parents[1]
    errors = validate_cap01a_contract(root, path)

    assert any("owner" in error for error in errors)


def test_cap01a_rejects_invalid_classification_and_provenance(tmp_path: Path) -> None:
    path, data = _contract_copy(tmp_path)
    capability = data["capabilities"][0]
    capability["classification"] = "NOT_A_CLASSIFICATION"
    capability["provenance"] = "NotAProvenance"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    root = Path(__file__).resolve().parents[1]
    errors = validate_cap01a_contract(root, path)

    assert any("classification" in error for error in errors)
    assert any("provenance" in error for error in errors)


def test_cap01a_rejects_unknown_relationship_reference(tmp_path: Path) -> None:
    path, data = _contract_copy(tmp_path)
    data["capabilities"][0]["module_id"] = "missing-module"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    root = Path(__file__).resolve().parents[1]
    errors = validate_cap01a_contract(root, path)

    assert any("Unknown CAP-01A capability module" in error for error in errors)
