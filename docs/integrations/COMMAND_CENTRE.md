# Command Centre Integration Boundary

Command Centre should consume Platform Core as a read-only declared-state model. It is the operator cockpit, not the registry authority.

## Platform Core Data For Future Views

- registered projects
- project identity, owner, lifecycle, maturity, and release channel
- declared dependency graph
- declared interfaces and services
- compatibility rules and policies
- release registry status
- standards and design-system metadata

## Later NEOS Data

Command Centre should use NEOS for observed repository health, build health, test health, compliance, release readiness, documentation status, and drift.

## Boundary

Command Centre can present warnings and request governed actions. It must not directly rewrite Platform Core registries without an explicit reviewed workflow.
