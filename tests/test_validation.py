import shutil
from pathlib import Path

import yaml

from new_earth_platform.service import validate_repository
from new_earth_platform.validation import validate_registry


def test_repository_validates() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_repository(root) == []


def _copy_repo_data(root: Path, target: Path) -> None:
    for name in ["registry", "schemas", "compatibility", "examples", "NEW_EARTH_PROJECT.yaml"]:
        source = root / name
        destination = target / name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def test_duplicate_project_ids_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "registry/projects.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["projects"].append(dict(data["projects"][0]))
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert "Duplicate project id: new-earth-platform-core" in validate_registry(tmp_path)


def test_unknown_dependency_target_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "registry/dependencies.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["dependencies"][0]["target"] = "missing-project"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert "Unknown dependency target: missing-project" in validate_registry(tmp_path)


def test_self_dependency_is_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    path = tmp_path / "registry/dependencies.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["dependencies"][0]["target"] = data["dependencies"][0]["source"]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert "Self dependency is not allowed: neos" in validate_registry(tmp_path)


def test_duplicate_services_and_interfaces_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    _copy_repo_data(root, tmp_path)
    services_path = tmp_path / "registry/services.yaml"
    services = yaml.safe_load(services_path.read_text(encoding="utf-8"))
    services["services"].append(dict(services["services"][0]))
    services_path.write_text(yaml.safe_dump(services, sort_keys=False), encoding="utf-8")
    interfaces_path = tmp_path / "registry/interfaces.yaml"
    interfaces = yaml.safe_load(interfaces_path.read_text(encoding="utf-8"))
    interfaces["interfaces"].append(dict(interfaces["interfaces"][0]))
    interfaces_path.write_text(yaml.safe_dump(interfaces, sort_keys=False), encoding="utf-8")
    errors = validate_registry(tmp_path)
    assert "Duplicate service id: platform-registry" in errors
    assert "Duplicate interface id: platform-registry-v1" in errors
