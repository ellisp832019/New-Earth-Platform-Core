# User Guide

Platform Core is a local-first declared-state repository. It describes the New Earth ecosystem; it does not inspect external source code or change other repositories.

## Installation

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

## Validation

```powershell
new-earth-platform validate
new-earth-platform doctor
pytest
ruff check src tests
mypy src
```

## CLI Commands

```powershell
new-earth-platform version
new-earth-platform validate
new-earth-platform validate-contract NEW_EARTH_PROJECT.yaml
new-earth-platform governance
new-earth-platform governance new-earth-platform-core
new-earth-platform planned-extractions
new-earth-platform projects
new-earth-platform projects --json
new-earth-platform project microgrow
new-earth-platform dependencies
new-earth-platform interfaces
new-earth-platform services
new-earth-platform compatibility
new-earth-platform graph --format mermaid
new-earth-platform graph --format mermaid --output artifacts/generated/platform.mmd
new-earth-platform impact microgrow
new-earth-platform doctor --json
```

## Adding A Project

1. Add or update a `NEW_EARTH_PROJECT.yaml` contract using `examples/NEW_EARTH_PROJECT.template.yaml`.
2. Register the project in `registry/projects.yaml`.
3. Ensure the project ID is lowercase kebab-case and unique.
4. Run `new-earth-platform validate-contract <path>`.
5. Run `new-earth-platform validate`.

## Adding Dependencies

Add declared edges to `registry/dependencies.yaml`. Supported relationship kinds are `consumes`, `provides`, `controls`, `observes`, `depends_on`, `publishes`, `subscribes`, and `compatible_with`.

Each edge must use known project IDs, must not be a self-dependency, must have a boolean `required` flag, may include a relationship `status` such as active, planned, optional, future, not_required, or deferred, and must reference a declared interface, service, or contract.

## Adding Interfaces And Services

Add interfaces to `registry/interfaces.yaml` and services to `registry/services.yaml`. Owners must be registered projects. Schema paths must point to tracked schema files when present.

## Governance Registry

The governance registry lives in `registry/governance.yaml`.

It records:

- canonical systems;
- planned extractions;
- lifecycle and canonical-state distinctions;
- ownership declarations;
- relationships to Platform Core, NEOS, GAIA, Command Centre, and Dashboard;
- legacy, prototype, and reference material.

The Local AI Runtime is declared there as a canonical platform service with its public runtime interfaces, consumers, and compatibility expectations. Inspect it with:

```powershell
new-earth-platform governance new-earth-local-ai-runtime
new-earth-platform interfaces
new-earth-platform services
new-earth-platform compatibility
```

For the broader governance view, inspect:

```powershell
new-earth-platform governance
new-earth-platform governance gaia
new-earth-platform planned-extractions
```

## Compatibility Rules

Add rules to `compatibility/matrix.yaml`. Requirements use Python packaging specifier syntax, including:

```text
>=1.0
>=1.0,<2.0
~=1.4
```

Platform Core validates syntax and can answer declared compatibility questions. It does not invent provider versions for external projects.

## Impact Analysis

```powershell
new-earth-platform impact microgrow
```

Impact output is declared architecture impact only. NEOS will later compare this declared state against observed repository reality.

## Interpreting Errors

Validation failures mean the authoritative platform data is incomplete, ambiguous, or malformed. Fix the registry, schema, or contract in Platform Core through a reviewed pull request. Do not silently rewrite external repositories to satisfy the registry.

## Branch And PR Workflow

Work on feature branches. Keep `main` protected. Run validation before opening a PR. Schema changes, breaking interface changes, and cross-repository changes require explicit architecture review and impact analysis.
