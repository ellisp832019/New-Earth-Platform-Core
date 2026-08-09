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
