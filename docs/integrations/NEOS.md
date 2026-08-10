# NEOS Integration Boundary

Platform Core exposes declared state. NEOS observes engineering reality and derives engineering intelligence.

## Platform Core Read Model

NEOS may consume these read-only inputs:

- `NEW_EARTH_PROJECT.yaml`
- `registry/projects.yaml`
- `registry/governance.yaml`
- `registry/dependencies.yaml`
- `registry/interfaces.yaml`
- `registry/services.yaml`
- `registry/releases.yaml`
- `compatibility/matrix.yaml`
- `compatibility/policies.yaml`
- `standards/**`
- project contracts referenced by `registry/projects.yaml`

## Responsibility Split

Declared state is owned by Platform Core. Observed state is owned by NEOS. Derived engineering intelligence is owned by NEOS.

NEOS should inspect repositories, git state, builds, tests, docs, source code, security posture, design-system drift, and compliance. It should compare observed reality against Platform Core declarations.

## Future Sequence

1. Platform Core validates declared projects, dependencies, interfaces, services, compatibility, and standards.
2. NEOS reads the validated Platform Core model.
3. NEOS discovers repositories and records observed SHA, branch, build, test, documentation, and contract state.
4. NEOS reports drift and release readiness without mutating Platform Core.
5. Governed humans decide whether Platform Core declarations or repository implementations must change.

NEOS must not silently mutate authoritative registries.
