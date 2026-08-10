from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .models import load_yaml


@dataclass(frozen=True)
class RepositoryIdentity:
    canonical_repo: str | None
    current_location: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepositoryIdentity:
        return cls(
            canonical_repo=str(data["canonical_repo"]) if data.get("canonical_repo") is not None else None,
            current_location=str(data["current_location"]) if data.get("current_location") is not None else None,
        )


@dataclass(frozen=True)
class Ownership:
    system_owner: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ownership:
        return cls(system_owner=str(data["system_owner"]))


@dataclass(frozen=True)
class Relationship:
    kind: str
    target: str | None
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Relationship:
        return cls(
            kind=str(data["kind"]),
            target=str(data["target"]) if data.get("target") is not None else None,
            notes=str(data["notes"]) if data.get("notes") is not None else None,
        )


@dataclass(frozen=True)
class GovernanceRecord:
    id: str
    canonical_name: str
    record_type: str
    architecture_role: str
    canonical_status: str
    lifecycle: str
    maturity: str
    ownership: Ownership
    repository: RepositoryIdentity
    contains_extractable_systems: bool
    release_independence: bool
    dependency_class: str
    relationships: dict[str, Relationship]
    recommended_action: str
    architecture_notes: list[str]
    supersedes: list[str]
    superseded_by: list[str]
    overlaps_with: list[str]
    source_system: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GovernanceRecord:
        relationships = {
            key: Relationship.from_dict(value)
            for key, value in (data.get("relationships") or {}).items()
        }
        return cls(
            id=str(data["id"]),
            canonical_name=str(data["canonical_name"]),
            record_type=str(data["record_type"]),
            architecture_role=str(data["architecture_role"]),
            canonical_status=str(data["canonical_status"]),
            lifecycle=str(data["lifecycle"]),
            maturity=str(data["maturity"]),
            ownership=Ownership.from_dict(data["ownership"]),
            repository=RepositoryIdentity.from_dict(data["repository"]),
            contains_extractable_systems=bool(data["contains_extractable_systems"]),
            release_independence=bool(data["release_independence"]),
            dependency_class=str(data["dependency_class"]),
            relationships=relationships,
            recommended_action=str(data["recommended_action"]),
            architecture_notes=[str(item) for item in data.get("architecture_notes", [])],
            supersedes=[str(item) for item in data.get("supersedes", [])],
            superseded_by=[str(item) for item in data.get("superseded_by", [])],
            overlaps_with=[str(item) for item in data.get("overlaps_with", [])],
            source_system=str(data["source_system"]) if data.get("source_system") is not None else None,
        )

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovernanceCatalog:
    governance_version: str
    ownership_model: dict[str, Any]
    systems: list[GovernanceRecord]
    planned_extractions: list[GovernanceRecord]


def load_governance(path: Path) -> GovernanceCatalog:
    data = load_yaml(path)
    systems = [GovernanceRecord.from_dict(item) for item in data.get("systems", [])]
    planned_extractions = [GovernanceRecord.from_dict(item) for item in data.get("planned_extractions", [])]
    return GovernanceCatalog(
        governance_version=str(data["governance_version"]),
        ownership_model=dict(data.get("ownership_model", {})),
        systems=systems,
        planned_extractions=planned_extractions,
    )


def governance_records(path: Path) -> list[GovernanceRecord]:
    catalog = load_governance(path)
    return catalog.systems + catalog.planned_extractions


def governance_index(path: Path) -> dict[str, GovernanceRecord]:
    return {record.id: record for record in governance_records(path)}
