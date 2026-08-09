from pathlib import Path

from new_earth_platform.graph import detect_cycles, graph_diagnostics
from new_earth_platform.models import Dependency, Project
from new_earth_platform.service import graph_text


def test_graph_contains_core_systems() -> None:
    root = Path(__file__).resolve().parents[1]
    text = graph_text(root)
    assert "NEOS" in text
    assert "Gaia" in text
    assert "New Earth Command Centre" in text
    assert "MicroGrow" in text


def test_cycle_detection_reports_suspicious_cycle() -> None:
    dependencies = [
        Dependency("a", "b", "depends_on", "test-contract", True),
        Dependency("b", "a", "depends_on", "test-contract", True),
    ]
    assert detect_cycles(dependencies) == [["a", "b", "a"]]


def test_graph_diagnostics_distinguish_self_cycle_and_unresolved_node() -> None:
    projects = [Project("a", "A", "core", "app", "Repo", "active", "contract.yaml")]
    dependencies = [Dependency("a", "a", "depends_on", "test-contract", True)]
    diagnostics = graph_diagnostics(projects, dependencies)
    assert "INVALID self-cycle: a" in diagnostics
