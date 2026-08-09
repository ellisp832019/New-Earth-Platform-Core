from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .models import load_yaml


@dataclass(frozen=True)
class CompatibilityRule:
    consumer: str
    provider: str
    contract: str
    requirement: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompatibilityRule:
        return cls(
            consumer=str(data["consumer"]),
            provider=str(data["provider"]),
            contract=str(data["contract"]),
            requirement=str(data["requirement"]),
        )

    def specifier(self) -> SpecifierSet:
        return SpecifierSet(self.requirement)

    def accepts(self, version: str) -> bool:
        return Version(version) in self.specifier()


def load_rules(root: Path) -> list[CompatibilityRule]:
    data = load_yaml(root / "compatibility/matrix.yaml")
    return [CompatibilityRule.from_dict(rule) for rule in data.get("rules", [])]


def find_rule(
    root: Path,
    consumer: str,
    provider: str,
    contract: str | None = None,
) -> CompatibilityRule | None:
    for rule in load_rules(root):
        if rule.consumer == consumer and rule.provider == provider and (contract is None or rule.contract == contract):
            return rule
    return None


def is_compatible(
    root: Path,
    consumer: str,
    provider: str,
    provider_version: str,
    contract: str | None = None,
) -> bool | None:
    rule = find_rule(root, consumer, provider, contract)
    if rule is None:
        return None
    return rule.accepts(provider_version)
