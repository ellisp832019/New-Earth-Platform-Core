from __future__ import annotations

from pathlib import Path

from .models import Dependency, Project, load_yaml


def load_projects(path: Path) -> list[Project]:
    return [Project.from_dict(p) for p in load_yaml(path).get("projects", [])]


def load_dependencies(path: Path) -> list[Dependency]:
    return [Dependency.from_dict(d) for d in load_yaml(path).get("dependencies", [])]


def mermaid(projects: list[Project], dependencies: list[Dependency]) -> str:
    lines = ["flowchart LR"]
    for project in projects:
        safe = project.id.replace("-", "_")
        label = project.name.replace('"', "'")
        lines.append(f'  {safe}["{label}"]')
    for dep in dependencies:
        source = dep.source.replace("-", "_")
        target = dep.target.replace("-", "_")
        label = f"{dep.kind}: {dep.contract}"
        lines.append(f'  {source} -->|"{label}"| {target}')
    return "\n".join(lines) + "\n"


def adjacency(dependencies: list[Dependency]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for dependency in sorted(dependencies, key=lambda item: (item.source, item.target, item.kind)):
        graph.setdefault(dependency.source, []).append(dependency.target)
        graph.setdefault(dependency.target, [])
    return graph


def detect_cycles(dependencies: list[Dependency]) -> list[list[str]]:
    graph = adjacency(dependencies)
    cycles: list[list[str]] = []
    stack: list[str] = []
    visited: set[str] = set()
    active: set[str] = set()
    seen_cycles: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        visited.add(node)
        active.add(node)
        stack.append(node)
        for next_node in graph.get(node, []):
            if next_node not in visited:
                visit(next_node)
            elif next_node in active:
                index = stack.index(next_node)
                cycle = stack[index:] + [next_node]
                normalized = tuple(sorted(cycle[:-1]))
                if normalized not in seen_cycles:
                    cycles.append(cycle)
                    seen_cycles.add(normalized)
        stack.pop()
        active.remove(node)

    for node in sorted(graph):
        if node not in visited:
            visit(node)
    return cycles


def graph_diagnostics(projects: list[Project], dependencies: list[Dependency]) -> list[str]:
    project_ids = {project.id for project in projects}
    diagnostics: list[str] = []
    for dependency in dependencies:
        if dependency.source == dependency.target:
            diagnostics.append(f"INVALID self-cycle: {dependency.source}")
        if dependency.source not in project_ids:
            diagnostics.append(f"UNRESOLVED source node: {dependency.source}")
        if dependency.target not in project_ids:
            diagnostics.append(f"UNRESOLVED target node: {dependency.target}")
    for cycle in detect_cycles(dependencies):
        diagnostics.append(f"WARNING suspicious cycle: {' -> '.join(cycle)}")
    return diagnostics
