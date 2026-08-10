import shutil
from pathlib import Path
from typing import cast

import yaml

from new_earth_platform.validation import validate_governance


def _copy_repo_data(root: Path, target: Path) -> None:
    for name in ["registry", "schemas", "compatibility", "examples", "NEW_EARTH_PROJECT.yaml"]:
        source = root / name
        destination = target / name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def _system(data: dict[str, object], system_id: str) -> dict[str, object]:
    for record in cast(list[dict[str, object]], data["systems"]):
        if record["id"] == system_id:
            return record
    raise AssertionError(system_id)


def _planned(data: dict[str, object], system_id: str) -> dict[str, object]:
    for record in cast(list[dict[str, object]], data["planned_extractions"]):
        if record["id"] == system_id:
            return record
    raise AssertionError(system_id)


def test_governance_registry_validates() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_governance(root) == []


def test_invalid_architecture_role_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "registry/governance.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _system(data, "new-earth-platform-core")["architecture_role"] = "BROKEN"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert any("Invalid architecture role" in error for error in validate_governance(tmp_path))


def test_missing_owner_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "registry/governance.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _system(data, "neos")["ownership"]["system_owner"] = ""
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert any("Missing owner" in error for error in validate_governance(tmp_path))


def test_contradictory_lifecycle_state_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "registry/governance.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _system(data, "new-earth-platform-core")["lifecycle"] = "planned"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert any("Contradictory lifecycle" in error for error in validate_governance(tmp_path))


def test_planned_extractions_are_represented_separately(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "registry/governance.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _planned(data, "microgrow-hub")["repository"]["canonical_repo"] = "MicroGrow-Hub"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert any("Planned extraction must not declare canonical_repo" in error for error in validate_governance(tmp_path))


def test_legacy_system_requires_successor(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "registry/governance.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _system(data, "mark-xl")["superseded_by"] = []
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert any("Superseded system should declare a successor" in error for error in validate_governance(tmp_path))


def test_reference_vendor_classification_is_rejected_for_internal_owner(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "registry/governance.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _system(data, "esp32-3248s035")["ownership"]["system_owner"] = "New Earth Advanced Technologies Ltd"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert any("Reference or vendor record cannot use the internal owner" in error for error in validate_governance(tmp_path))


def test_relationship_targets_must_resolve(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "registry/governance.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _system(data, "new-earth-platform-core")["relationships"]["gaia"]["target"] = "missing-system"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert any("Unresolved relationship target" in error for error in validate_governance(tmp_path))


def test_governance_cli_behaviour() -> None:
    from typer.testing import CliRunner

    from new_earth_platform.cli import app

    result = CliRunner().invoke(app, ["governance", "--json"])
    assert result.exit_code == 0
    assert "New Earth Platform Core" in result.output

    planned = CliRunner().invoke(app, ["planned-extractions", "--json"])
    assert planned.exit_code == 0
    assert "MicroGrow-Hub" in planned.output
