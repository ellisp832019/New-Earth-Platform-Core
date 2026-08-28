# CAP-01A Module and Capability Contract

CAP-01A is the minimum declarative foundation for representing ownership and authority without migrating the ecosystem into a shared registry. It defines a contract, not a runtime service.

## Relationship

```text
SYSTEM
  |
MODULE
  |
CAPABILITY
  |-- OWNER
  |-- CONSUMERS
  |-- AUTHORITY
  |-- PROVENANCE
  |-- CLASSIFICATION
  |-- STATUS
  `-- EVIDENCE
```

The contract is defined by `schemas/cap-01a-architecture.schema.json` and represented by the small fixture at `examples/cap-01a/minimal-architecture.yaml`. Every object carries at least one evidence reference. References are paths or identifiers; large evidence blobs do not belong in the contract.

## Ownership and Authority

`owner` identifies the system or area responsible for the capability. `consumers` identifies readers or users of that capability. A consumer does not become the owner, and an adapter/view does not become the authority. Platform Core declares architecture; NEOS observes engineering truth; GAIA interprets; Command Centre operates; Dashboard presents human-facing views.

## Vocabularies

Capability classifications are exactly:

- `LOCAL_ONLY`
- `LOCAL_NOW_POTENTIAL_SHARED_LATER`
- `SHARED_CANDIDATE`
- `SHARED_CANONICAL`
- `CONSUMED_EXTERNAL`
- `ADAPTER_VIEW_ONLY`
- `UNCLEAR_REVIEW_REQUIRED`

Provenance is preserved as: `Declared`, `Observed`, `Local`, `Interpreted`, `Operational`, `Protected`, or `Indexed`.

Lifecycle status follows the existing Platform Core vocabulary: `planned`, `declared`, `active`, or `deprecated`.

## Promotion Rule

A capability may become `SHARED_CANONICAL` only when all conditions are evidenced:

1. At least two real consumers exist.
2. The consumers have the same semantics.
3. A clear owner exists.
4. Sharing lowers total complexity.

`SHARED_CANDIDATE` does not auto-promote. CAP-01A does not automate this decision.

## Explicitly Not Promoted

Project identity, task identity, capture envelope, device identity, audit events, and command/action IDs remain local or candidate/review items. CAP-01A does not create canonical schemas for them.

## Boundaries

CAP-01A adds no database, network, MCP, process, watcher, event bus, runtime orchestration, shared command registry, or LANE-01 workflow model. LANE-01 remains deferred until module and capability ownership are stable.

## Next Step

CAP-01B should validate this contract against the complete Dashboard Wave 7 module and capability evidence before any broader adoption or migration.
