from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a YAML object at its root")
    return data


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    family: str
    type: str
    repository: str
    status: str
    contract: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Project:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            family=str(data["family"]),
            type=str(data["type"]),
            repository=str(data["repository"]),
            status=str(data["status"]),
            contract=str(data["contract"]),
        )


@dataclass(frozen=True)
class Dependency:
    source: str
    target: str
    kind: str
    contract: str
    required: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Dependency:
        return cls(
            source=str(data["source"]),
            target=str(data["target"]),
            kind=str(data["kind"]),
            contract=str(data["contract"]),
            required=bool(data["required"]),
        )


@dataclass(frozen=True)
class Service:
    id: str
    owner: str
    kind: str
    interface: str
    version: str | None
    status: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Service:
        return cls(
            id=str(data["id"]),
            owner=str(data["owner"]),
            kind=str(data["kind"]),
            interface=str(data["interface"]),
            version=str(data["version"]) if "version" in data else None,
            status=str(data["status"]) if "status" in data else None,
        )


@dataclass(frozen=True)
class Interface:
    id: str
    owner: str
    stability: str
    schema: str | None
    type: str | None
    endpoint: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Interface:
        return cls(
            id=str(data["id"]),
            owner=str(data["owner"]),
            stability=str(data["stability"]),
            schema=str(data["schema"]) if "schema" in data else None,
            type=str(data["type"]) if "type" in data else None,
            endpoint=str(data["endpoint"]) if "endpoint" in data else None,
        )
