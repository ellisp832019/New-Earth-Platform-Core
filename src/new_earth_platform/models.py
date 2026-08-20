from __future__ import annotations

from dataclasses import dataclass, field
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
    status: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Dependency:
        return cls(
            source=str(data["source"]),
            target=str(data["target"]),
            kind=str(data["kind"]),
            contract=str(data["contract"]),
            required=bool(data["required"]),
            status=str(data["status"]) if "status" in data else None,
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
    method: str | None = None
    path: str | None = None
    protocol: str | None = None
    version: str | None = None
    consumers: list[str] = field(default_factory=list)
    security: str | None = None
    lifecycle: str | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Interface:
        return cls(
            id=str(data["id"]),
            owner=str(data["owner"]),
            stability=str(data["stability"]),
            schema=str(data["schema"]) if "schema" in data else None,
            type=str(data["type"]) if "type" in data else None,
            endpoint=str(data["endpoint"]) if "endpoint" in data else None,
            method=str(data["method"]) if "method" in data else None,
            path=str(data["path"]) if "path" in data else None,
            protocol=str(data["protocol"]) if "protocol" in data else None,
            version=str(data["version"]) if "version" in data else None,
            consumers=[str(item) for item in data.get("consumers", [])],
            security=str(data["security"]) if "security" in data else None,
            lifecycle=str(data["lifecycle"]) if "lifecycle" in data else None,
            notes=str(data["notes"]) if "notes" in data else None,
        )


@dataclass(frozen=True)
class MCPClientIdentity:
    client_id: str
    client_name: str
    client_version: str
    owner_system_id: str
    process_identity: dict[str, Any]
    machine_scope: dict[str, Any]
    declared_capabilities: list[str]
    requested_scope: list[str]
    enabled: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPClientIdentity:
        return cls(
            client_id=str(data["client_id"]),
            client_name=str(data["client_name"]),
            client_version=str(data["client_version"]),
            owner_system_id=str(data["owner_system_id"]),
            process_identity=dict(data["process_identity"]),
            machine_scope=dict(data["machine_scope"]),
            declared_capabilities=[str(item) for item in data["declared_capabilities"]],
            requested_scope=[str(item) for item in data["requested_scope"]],
            enabled=bool(data["enabled"]),
        )


@dataclass(frozen=True)
class MCPServerIdentity:
    server_id: str
    server_name: str
    server_version: str
    owner_system_id: str
    bind_scope: str
    transport: str
    capability_version: str
    schema_version: str
    declared_tools: list[str]
    declared_resources: list[str]
    enabled: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPServerIdentity:
        return cls(
            server_id=str(data["server_id"]),
            server_name=str(data["server_name"]),
            server_version=str(data["server_version"]),
            owner_system_id=str(data["owner_system_id"]),
            bind_scope=str(data["bind_scope"]),
            transport=str(data["transport"]),
            capability_version=str(data["capability_version"]),
            schema_version=str(data["schema_version"]),
            declared_tools=[str(item) for item in data["declared_tools"]],
            declared_resources=[str(item) for item in data["declared_resources"]],
            enabled=bool(data["enabled"]),
        )
