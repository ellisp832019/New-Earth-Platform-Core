"""Deterministic Programme Compiler / Validator V0.1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import yaml

from .resolver import NullReferenceResolver, ReferenceResolver


DIAGNOSTIC_CLASS_ORDER = {
    "INVALID": 0,
    "UNKNOWN": 1,
    "BLOCKED": 2,
    "INFO": 3,
}

PROHIBITED_OPERATIONAL_FIELDS = {
    "execution_eligible",
    "dispatch_state",
    "approval_state",
    "validation_state",
    "completion_timestamp",
    "completed_at",
    "execution_state",
    "active",
    "executing",
}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    classification: str
    location: str
    message: str
    evidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "class": self.classification,
            "location": self.location,
            "message": self.message,
        }
        if self.evidence is not None:
            value["evidence"] = self.evidence
        return value


@dataclass(frozen=True)
class CompileResult:
    outcome: str
    source_sha256: str
    normalized_content_sha256: str
    diagnostics: tuple[Diagnostic, ...]
    registration_plan: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "source_sha256": self.source_sha256,
            "normalized_content_sha256": self.normalized_content_sha256,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "registration_plan": self.registration_plan,
        }


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _normalized_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _diagnostic_sort_key(diagnostic: Diagnostic) -> tuple[int, str, str, str]:
    return (
        DIAGNOSTIC_CLASS_ORDER.get(diagnostic.classification, 99),
        diagnostic.code,
        diagnostic.location,
        diagnostic.message,
    )


def _select_outcome(diagnostics: Iterable[Diagnostic]) -> str:
    classes = {d.classification for d in diagnostics}
    if "INVALID" in classes:
        return "INVALID"
    if "UNKNOWN" in classes:
        return "UNKNOWN"
    if "BLOCKED" in classes:
        return "BLOCKED"
    return "VALID"


def _walk_fields(value: Any, location: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            yield key, child_location
            yield from _walk_fields(child, child_location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_fields(child, f"{location}[{index}]")


def _programme(data: dict[str, Any]) -> dict[str, Any]:
    value = data.get("programme", {})
    return value if isinstance(value, dict) else {}


def _work_packages(data: dict[str, Any]) -> list[dict[str, Any]]:
    value = data.get("work_packages", [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _check_prohibited_fields(
    data: dict[str, Any],
    diagnostics: list[Diagnostic],
) -> None:
    for field, location in _walk_fields(data):
        if field in PROHIBITED_OPERATIONAL_FIELDS:
            diagnostics.append(
                Diagnostic(
                    "PCV025",
                    "INVALID",
                    location,
                    f"Operational-state field is prohibited: {field}",
                )
            )


def _check_duplicates(
    data: dict[str, Any],
    diagnostics: list[Diagnostic],
) -> None:
    seen_wp: dict[str, str] = {}
    seen_task: dict[str, str] = {}

    for wp_index, wp in enumerate(_work_packages(data)):
        wp_id = wp.get("work_package_id")
        wp_location = f"$.work_packages[{wp_index}].work_package_id"
        if isinstance(wp_id, str):
            if wp_id in seen_wp:
                diagnostics.append(
                    Diagnostic(
                        "PCV020",
                        "INVALID",
                        wp_location,
                        f"Duplicate work_package_id: {wp_id}",
                        evidence=f"first_seen={seen_wp[wp_id]}",
                    )
                )
            else:
                seen_wp[wp_id] = wp_location

        tasks = wp.get("tasks", [])
        if not isinstance(tasks, list):
            continue

        for task_index, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue
            task_id = task.get("task_id")
            task_location = (
                f"$.work_packages[{wp_index}].tasks[{task_index}].task_id"
            )
            if isinstance(task_id, str):
                if task_id in seen_task:
                    diagnostics.append(
                        Diagnostic(
                            "PCV021",
                            "INVALID",
                            task_location,
                            f"Duplicate task_id across programme: {task_id}",
                            evidence=f"first_seen={seen_task[task_id]}",
                        )
                    )
                else:
                    seen_task[task_id] = task_location


def _dependency_graph(
    data: dict[str, Any],
    diagnostics: list[Diagnostic],
) -> dict[str, list[str]]:
    work_packages = _work_packages(data)
    known_ids = {
        wp.get("work_package_id")
        for wp in work_packages
        if isinstance(wp.get("work_package_id"), str)
    }
    graph: dict[str, list[str]] = {}

    for wp_index, wp in enumerate(work_packages):
        wp_id = wp.get("work_package_id")
        if not isinstance(wp_id, str):
            continue

        graph.setdefault(wp_id, [])
        dependencies = wp.get("dependencies", [])
        if not isinstance(dependencies, list):
            continue

        for dep_index, dependency in enumerate(dependencies):
            if not isinstance(dependency, str):
                continue

            location = f"$.work_packages[{wp_index}].dependencies[{dep_index}]"

            if dependency == wp_id:
                diagnostics.append(
                    Diagnostic(
                        "PCV022",
                        "INVALID",
                        location,
                        f"Self-dependency detected for work package {wp_id}.",
                    )
                )
                continue

            if dependency not in known_ids:
                diagnostics.append(
                    Diagnostic(
                        "PCV023",
                        "INVALID",
                        location,
                        f"Local dependency target does not exist: {dependency}",
                    )
                )
                continue

            graph[wp_id].append(dependency)

    return graph


def _check_cycles(
    graph: dict[str, list[str]],
    diagnostics: list[Diagnostic],
) -> None:
    state: dict[str, int] = {}
    stack: list[str] = []
    reported: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        marker = state.get(node, 0)
        if marker == 2:
            return
        if marker == 1:
            start = stack.index(node) if node in stack else 0
            cycle = tuple(stack[start:] + [node])
            if cycle not in reported:
                reported.add(cycle)
                diagnostics.append(
                    Diagnostic(
                        "PCV024",
                        "INVALID",
                        "$.work_packages",
                        "Dependency cycle detected: " + " -> ".join(cycle),
                    )
                )
            return

        state[node] = 1
        stack.append(node)
        for dependency in sorted(graph.get(node, [])):
            visit(dependency)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        visit(node)


def _check_blockers(
    data: dict[str, Any],
    diagnostics: list[Diagnostic],
) -> None:
    for wp_index, wp in enumerate(_work_packages(data)):
        blockers = wp.get("blockers", [])
        if isinstance(blockers, list):
            for blocker_index, blocker in enumerate(blockers):
                if isinstance(blocker, str) and blocker:
                    diagnostics.append(
                        Diagnostic(
                            "PCV040",
                            "BLOCKED",
                            f"$.work_packages[{wp_index}].blockers[{blocker_index}]",
                            f"Explicit unresolved work-package blocker: {blocker}",
                        )
                    )

        tasks = wp.get("tasks", [])
        if not isinstance(tasks, list):
            continue
        for task_index, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue
            task_blockers = task.get("blockers", [])
            if not isinstance(task_blockers, list):
                continue
            for blocker_index, blocker in enumerate(task_blockers):
                if isinstance(blocker, str) and blocker:
                    diagnostics.append(
                        Diagnostic(
                            "PCV040",
                            "BLOCKED",
                            (
                                f"$.work_packages[{wp_index}].tasks[{task_index}]"
                                f".blockers[{blocker_index}]"
                            ),
                            f"Explicit unresolved task blocker: {blocker}",
                        )
                    )


def _check_downstream_gates(
    data: dict[str, Any],
    diagnostics: list[Diagnostic],
) -> None:
    for wp_index, wp in enumerate(_work_packages(data)):
        if wp.get("approval_required") is True:
            diagnostics.append(
                Diagnostic(
                    "PCV060",
                    "INFO",
                    f"$.work_packages[{wp_index}].approval_required",
                    "Downstream human approval gate required.",
                )
            )

        authority = wp.get("authority_required")
        if isinstance(authority, str):
            diagnostics.append(
                Diagnostic(
                    "PCV061",
                    "INFO",
                    f"$.work_packages[{wp_index}].authority_required",
                    f"Downstream authority requirement: {authority}",
                )
            )


def _check_external_references(
    data: dict[str, Any],
    resolver: ReferenceResolver,
    diagnostics: list[Diagnostic],
) -> None:
    # Contract V1 defines both collections at the document root.
    repository_bindings = data.get("repository_bindings", [])
    if isinstance(repository_bindings, list):
        for index, binding in enumerate(repository_bindings):
            location = f"$.repository_bindings[{index}]"
            try:
                resolution = resolver.resolve_repository_binding(binding)
            except Exception as exc:
                diagnostics.append(
                    Diagnostic(
                        "PCV070",
                        "UNKNOWN",
                        location,
                        "Authoritative repository-binding resolver failed closed.",
                        evidence=f"resolver_exception={exc.__class__.__name__}",
                    )
                )
                continue
            if resolution.status == "UNKNOWN":
                diagnostics.append(
                    Diagnostic(
                        "PCV070",
                        "UNKNOWN",
                        location,
                        resolution.message or "Repository binding cannot be established.",
                        resolution.evidence,
                    )
                )
            elif resolution.status == "CONTRADICTED":
                diagnostics.append(
                    Diagnostic(
                        "PCV031",
                        "INVALID",
                        location,
                        resolution.message or "Repository binding is contradicted.",
                        resolution.evidence,
                    )
                )

    contract_refs = data.get("platform_contract_refs", [])
    if isinstance(contract_refs, list):
        for index, contract_ref in enumerate(contract_refs):
            location = f"$.platform_contract_refs[{index}]"
            try:
                resolution = resolver.resolve_platform_contract_ref(contract_ref)
            except Exception as exc:
                diagnostics.append(
                    Diagnostic(
                        "PCV030",
                        "UNKNOWN",
                        location,
                        "Authoritative contract-reference resolver failed closed.",
                        evidence=f"resolver_exception={exc.__class__.__name__}",
                    )
                )
                continue
            if resolution.status == "UNKNOWN":
                diagnostics.append(
                    Diagnostic(
                        "PCV030",
                        "UNKNOWN",
                        location,
                        resolution.message or "Platform contract reference cannot be established.",
                        resolution.evidence,
                    )
                )
            elif resolution.status == "CONTRADICTED":
                diagnostics.append(
                    Diagnostic(
                        "PCV031",
                        "INVALID",
                        location,
                        resolution.message or "Platform contract reference is contradicted.",
                        resolution.evidence,
                    )
                )


def _registration_plan(
    data: dict[str, Any],
    outcome: str,
    diagnostics: list[Diagnostic],
    source_sha256: str,
    normalized_hash: str,
) -> dict[str, Any]:
    programme = _programme(data)
    work_packages = _work_packages(data)

    proposed_wps: list[dict[str, Any]] = []
    dependency_rows: list[dict[str, str]] = []
    task_count = 0

    for wp in work_packages:
        tasks = wp.get("tasks", [])
        if not isinstance(tasks, list):
            tasks = []
        task_count += sum(1 for task in tasks if isinstance(task, dict))

        dependencies = wp.get("dependencies", [])
        if not isinstance(dependencies, list):
            dependencies = []

        wp_id = wp.get("work_package_id")
        for dependency in dependencies:
            if isinstance(wp_id, str) and isinstance(dependency, str):
                dependency_rows.append(
                    {
                        "work_package_id": wp_id,
                        "depends_on": dependency,
                    }
                )

        proposed_wps.append(
            {
                "work_package_id": wp_id,
                "title": wp.get("title"),
                "objective": wp.get("objective"),
                "authority_required": wp.get("authority_required"),
                "approval_required": wp.get("approval_required"),
                "evidence_required": wp.get("evidence_required"),
                "task_ids": [
                    task.get("task_id")
                    for task in tasks
                    if isinstance(task, dict)
                ],
            }
        )

    plan: dict[str, Any] = {
        "schema": "new-earth.programme-registration-plan.v0.1-draft",
        "status": "NON_CANONICAL_COMPILER_OUTPUT",
        "compiler": {
            "name": "new-earth-programme-compiler",
            "version": "0.1.0",
        },
        "source": {
            "contract": data.get("schema"),
            "contract_version": data.get("version"),
            "source_sha256": source_sha256,
            "normalized_content_sha256": normalized_hash,
        },
        "result": {
            "outcome": outcome,
            "diagnostics": [d.to_dict() for d in diagnostics],
        },
        "programme": {
            "programme_id": programme.get("programme_id"),
            "lane_id": programme.get("lane_id"),
            "name": programme.get("name"),
            "objective": programme.get("objective"),
        },
        "proposed_work": {
            "work_packages": proposed_wps,
            "task_count": task_count,
            "dependencies": dependency_rows,
        },
        "references": {
            "repository_bindings": data.get("repository_bindings", []),
            "platform_contract_refs": data.get("platform_contract_refs", []),
        },
        "downstream_gates": {
            "peter_approval_required": True,
            "enrollment_admission_required": True,
            "programme_control_binding_required": True,
        },
        "authority_statement": {
            "creates_operational_state": False,
            "admits_repositories": False,
            "activates_work": False,
            "dispatches_tasks": False,
        },
    }

    # The source byte hash remains in the emitted plan for provenance, but is
    # deliberately excluded from plan identity. Semantically equivalent YAML
    # and JSON must produce the same deterministic plan hash.
    plan_hash_payload = json.loads(json.dumps(plan))
    source_for_hash = plan_hash_payload.get("source")
    if isinstance(source_for_hash, dict):
        source_for_hash.pop("source_sha256", None)

    plan["plan_sha256"] = _sha256(_normalized_bytes(plan_hash_payload))
    return plan


def compile_data(
    data: Any,
    *,
    schema: dict[str, Any],
    source_bytes: bytes | None = None,
    resolver: ReferenceResolver | None = None,
) -> CompileResult:
    if source_bytes is None:
        source_bytes = _normalized_bytes(data)

    source_sha256 = _sha256(source_bytes)
    normalized_hash = _sha256(_normalized_bytes(data))
    diagnostics: list[Diagnostic] = []

    validator = jsonschema.Draft202012Validator(schema)
    schema_errors = sorted(
        validator.iter_errors(data),
        key=lambda error: (list(error.absolute_path), error.message),
    )

    for error in schema_errors:
        path = "$"
        for part in error.absolute_path:
            if isinstance(part, int):
                path += f"[{part}]"
            else:
                path += f".{part}"
        diagnostics.append(
            Diagnostic(
                "PCV010",
                "INVALID",
                path,
                error.message,
            )
        )

    if isinstance(data, dict):
        _check_prohibited_fields(data, diagnostics)

        # Intrinsic semantics run only when the canonical structure is usable.
        if not schema_errors:
            _check_duplicates(data, diagnostics)
            graph = _dependency_graph(data, diagnostics)
            _check_cycles(graph, diagnostics)
            _check_blockers(data, diagnostics)
            _check_downstream_gates(data, diagnostics)
            _check_external_references(
                data,
                resolver or NullReferenceResolver(),
                diagnostics,
            )

    diagnostics = sorted(diagnostics, key=_diagnostic_sort_key)
    outcome = _select_outcome(diagnostics)
    plan = _registration_plan(
        data if isinstance(data, dict) else {},
        outcome,
        diagnostics,
        source_sha256,
        normalized_hash,
    )

    return CompileResult(
        outcome=outcome,
        source_sha256=source_sha256,
        normalized_content_sha256=normalized_hash,
        diagnostics=tuple(diagnostics),
        registration_plan=plan,
    )


def compile_file(
    input_path: str | Path,
    *,
    schema_path: str | Path,
    resolver: ReferenceResolver | None = None,
) -> CompileResult:
    input_path = Path(input_path)
    schema_path = Path(schema_path)

    source_bytes = input_path.read_bytes()

    try:
        text = source_bytes.decode("utf-8")
        if input_path.suffix.lower() == ".json":
            data = json.loads(text)
        else:
            data = yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError, UnicodeDecodeError) as exc:
        diagnostic = Diagnostic(
            "PCV001",
            "INVALID",
            "$",
            f"Input parse failed: {exc.__class__.__name__}",
        )
        source_sha256 = _sha256(source_bytes)
        normalized_hash = _sha256(_normalized_bytes({}))
        diagnostics = [diagnostic]
        plan = _registration_plan(
            {},
            "INVALID",
            diagnostics,
            source_sha256,
            normalized_hash,
        )
        return CompileResult(
            outcome="INVALID",
            source_sha256=source_sha256,
            normalized_content_sha256=normalized_hash,
            diagnostics=(diagnostic,),
            registration_plan=plan,
        )

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return compile_data(
        data,
        schema=schema,
        source_bytes=source_bytes,
        resolver=resolver,
    )

