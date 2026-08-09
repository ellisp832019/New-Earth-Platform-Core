from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .graph import load_dependencies
from .models import Dependency


@dataclass(frozen=True)
class ImpactResult:
    target: str
    direct: list[str]
    transitive: list[str]


def direct_dependents(dependencies: list[Dependency], target: str) -> list[str]:
    return sorted({dependency.source for dependency in dependencies if dependency.target == target})


def transitive_dependents(dependencies: list[Dependency], target: str) -> list[str]:
    direct = direct_dependents(dependencies, target)
    found: set[str] = set(direct)
    frontier = list(direct)
    while frontier:
        current = frontier.pop(0)
        for dependent in direct_dependents(dependencies, current):
            if dependent not in found and dependent != target:
                found.add(dependent)
                frontier.append(dependent)
    return sorted(found - set(direct))


def declared_impact(root: Path, target: str) -> ImpactResult:
    dependencies = load_dependencies(root / "registry/dependencies.yaml")
    return ImpactResult(
        target=target,
        direct=direct_dependents(dependencies, target),
        transitive=transitive_dependents(dependencies, target),
    )


def affected_by_contract(root: Path, contract: str) -> list[str]:
    dependencies = load_dependencies(root / "registry/dependencies.yaml")
    return sorted({dependency.source for dependency in dependencies if dependency.contract == contract})
