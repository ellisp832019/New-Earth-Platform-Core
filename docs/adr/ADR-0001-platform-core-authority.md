# ADR-0001 — Platform Core is the authoritative ecosystem registry

Status: Accepted

## Decision

Create a dedicated Platform Core repository that owns machine-readable project, dependency, compatibility, interface and standard metadata.

## Why

Keeping these concerns inside NEOS or Command Centre would couple platform truth to one consumer and make other systems dependent on implementation details.

## Consequences

- all consumers share one source of truth;
- schema changes require governance;
- registry changes become reviewable PRs;
- tooling can remain deterministic and local-first.
