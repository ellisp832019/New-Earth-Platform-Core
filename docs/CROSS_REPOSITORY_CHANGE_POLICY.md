# Cross-Repository Change Policy

Platform Core v0.1 identifies declared architectural impact. It must not directly edit multiple repositories.

## Intended Future Workflow

```text
Developer changes shared interface
        |
        v
Platform Core identifies declared impact
        |
        v
NEOS inspects observed impact
        |
        v
Affected repositories determined
        |
        v
Feature branches created independently
        |
        v
CI runs per repository
        |
        v
Integration validation
        |
        v
Pull requests
        |
        v
Coordinated release
```

## Rules

- Platform Core changes happen through Platform Core PRs.
- External repository changes happen on their own branches and PRs.
- Breaking schema or interface changes require declared impact analysis before implementation.
- NEOS is responsible for observed repository impact.
- Humans approve coordinated release plans.
