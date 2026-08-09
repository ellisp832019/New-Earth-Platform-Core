from pathlib import Path

from new_earth_platform.service import validate_repository


def test_repository_validates() -> None:
    root = Path(__file__).resolve().parents[1]
    assert validate_repository(root) == []
