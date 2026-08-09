# ADR-0003: Use Local YAML Registries For v0.1

## Status

Accepted

## Decision

Platform Core v0.1 keeps authoritative registries in versioned YAML files.

## Consequences

The platform remains human-readable and easy to review in pull requests. Validation code provides consistency checks for duplicate IDs, unknown references, malformed requirements, missing contracts, and ambiguous dependency edges. A database or remote service can be considered later only when local deterministic files become insufficient.
