"""External reference boundary for Programme Compiler V0.1.

No Enrollment, NEOS or Guardian implementation exists here.
Sibling-lane adapters may implement this protocol later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Resolution:
    status: str
    evidence: str | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        allowed = {"RESOLVED", "CONTRADICTED", "UNKNOWN"}
        if self.status not in allowed:
            raise ValueError(f"unsupported resolution status: {self.status}")


class ReferenceResolver(Protocol):
    def resolve_repository_binding(self, binding: Any) -> Resolution:
        ...

    def resolve_platform_contract_ref(self, contract_ref: Any) -> Resolution:
        ...


class NullReferenceResolver:
    """Fail closed until accepted authoritative adapters are supplied."""

    def resolve_repository_binding(self, binding: Any) -> Resolution:
        return Resolution(
            "UNKNOWN",
            message="No accepted Enrollment/NEOS admission adapter supplied.",
        )

    def resolve_platform_contract_ref(self, contract_ref: Any) -> Resolution:
        return Resolution(
            "UNKNOWN",
            message="No accepted authoritative contract-reference adapter supplied.",
        )
