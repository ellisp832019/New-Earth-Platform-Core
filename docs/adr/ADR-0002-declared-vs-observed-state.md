# ADR-0002: Separate Declared And Observed State

## Status

Accepted

## Decision

Platform Core owns declared ecosystem state: projects, contracts, registries, dependencies, interfaces, services, compatibility rules, standards, and release metadata.

NEOS owns observed repository state and derived engineering intelligence.

## Consequences

Platform Core remains local-first, deterministic, inspectable, and human-governed. It can calculate declared impact, but it must not claim build, test, compliance, or source-code facts that require NEOS inspection.
