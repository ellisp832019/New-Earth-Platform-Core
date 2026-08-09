from pathlib import Path

from new_earth_platform.service import graph_text


def test_graph_contains_core_systems() -> None:
    root = Path(__file__).resolve().parents[1]
    text = graph_text(root)
    assert "NEOS" in text
    assert "Gaia" in text
    assert "New Earth Command Centre" in text
    assert "MicroGrow" in text
