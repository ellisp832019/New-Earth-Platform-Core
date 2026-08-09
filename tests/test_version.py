import tomllib
from pathlib import Path

import yaml


def test_version_metadata_does_not_drift() -> None:
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    contract = yaml.safe_load((root / "NEW_EARTH_PROJECT.yaml").read_text(encoding="utf-8"))
    releases = yaml.safe_load((root / "registry/releases.yaml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == version
    assert str(contract["repository"]["version"]) == version
    assert str(releases["platform"]["current"]) == version
