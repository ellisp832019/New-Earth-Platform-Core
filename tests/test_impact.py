from pathlib import Path

from new_earth_platform.impact import affected_by_contract, declared_impact


def test_declared_impact_direct_and_transitive_dependents() -> None:
    root = Path(__file__).resolve().parents[1]
    result = declared_impact(root, "new-earth-platform-core")
    assert result.direct == ["command-centre", "gaia", "neos"]
    assert result.transitive == []


def test_contract_impact_lists_declared_consumers() -> None:
    root = Path(__file__).resolve().parents[1]
    assert affected_by_contract(root, "neos-status-api") == ["command-centre"]
