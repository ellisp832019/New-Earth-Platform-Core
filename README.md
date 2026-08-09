# New Earth Platform Core — Omega Foundation

**Version:** 0.1.0  
**Status:** Foundation / architecture-control layer  
**Purpose:** Provide the machine-readable source of truth that connects New Earth repositories, NEOS, Gaia, Command Centre, design standards, shared contracts, dependency intelligence, and platform-wide build/release orchestration.

## What this repository is

New Earth Platform Core is the **platform registry and contract layer** for the New Earth engineering ecosystem.

It is intentionally not another end-user application. It defines:

- which projects exist;
- how projects identify themselves;
- what each repository provides and consumes;
- cross-repository dependencies;
- version compatibility rules;
- platform standards;
- design-system requirements;
- release channels and maturity states;
- integration contracts for NEOS, Gaia, and Command Centre;
- platform validation and graph-generation tooling.

## Initial architecture

```text
                    New Earth Platform Core
          ┌─────────────────────────────────────┐
          │ Registry                            │
          │ Project contracts                   │
          │ Dependency graph                    │
          │ Compatibility rules                 │
          │ Standards                           │
          │ Shared schemas                      │
          │ Design-system metadata              │
          │ Release metadata                    │
          └──────────────┬──────────────────────┘
                         │
          ┌──────────────┼──────────────────┐
          │              │                  │
        NEOS           Gaia          Command Centre
   analyse/validate   understand      observe/control
          │              │                  │
          └──────────────┼──────────────────┘
                         │
          MicroGrow / BioCalm / Living / Life OS /
          Embedded Engineering Lab / future projects
```

## Quick start

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e .[dev]
new-earth-platform validate
new-earth-platform graph --format mermaid
pytest
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e '.[dev]'
new-earth-platform validate
new-earth-platform graph --format mermaid
pytest
```

## Repository lifecycle

Recommended first working branch:

```text
feature/platform-core-v0.1-foundation
```

Workflow:

1. `main` remains protected and releasable.
2. Create feature branch.
3. Implement and validate locally.
4. Push branch.
5. Open pull request.
6. Require CI to pass.
7. Review generated registry/graph changes.
8. Merge to `main`.
9. Switch back to `main`.
10. Pull/sync before starting the next platform integration branch.

See `docs/WORKFLOW.md`.

## Omega scope

This starter includes a real working Python package, JSON schemas, example project contracts, YAML registries, dependency/compatibility validation, Mermaid graph generation, GitHub Actions CI, security/engineering/design standards, architecture decision records, integration documents, tests, and expansion hooks.

## Non-goals for v0.1

- no autonomous modification of external repositories;
- no automatic merging or releasing;
- no cloud requirement;
- no replacement for NEOS;
- no replacement for Command Centre;
- no hidden dependency resolution.

The platform must remain inspectable, deterministic, local-first, and human-governed.
