# User Guide

## Validate the whole Platform Core repository

```powershell
new-earth-platform validate
```

## Show registered projects

```powershell
new-earth-platform projects
```

## Generate a Mermaid dependency graph

```powershell
new-earth-platform graph --format mermaid
```

## Write the graph to a file

```powershell
new-earth-platform graph --format mermaid --output artifacts/generated/platform.mmd
```

## Validate a project contract

```powershell
new-earth-platform validate-contract NEW_EARTH_PROJECT.yaml
```

## How to onboard a new repository

1. Copy `examples/NEW_EARTH_PROJECT.template.yaml` into the repository root as `NEW_EARTH_PROJECT.yaml`.
2. Replace all placeholders.
3. Add the project to `registry/projects.yaml`.
4. Add dependency edges to `registry/dependencies.yaml`.
5. Add compatibility rules if the repository consumes versioned shared contracts.
6. Run `new-earth-platform validate`.
7. Open a PR in Platform Core.
8. Only after the registry PR is merged, integrate NEOS/Command Centre/Gaia as needed.

## Golden rule

The registry should describe reality.  
If code and registry disagree, investigate rather than automatically rewriting one to match the other.
